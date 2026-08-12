import contextlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from crud_generator.parsing import DefinitionError
from crud_generator.stream_generator import generate_stream_project

MAVEN = shutil.which("mvn.cmd") or shutil.which("mvn")

DEFINITION = {
    "project": "sales-streams",
    "package": "com.example.sales",
    "input": {
        "topic": "orders-topic1",
        "event": "Order",
        "fields": [
            {"name": "order_id", "type": "string"},
            {"name": "customer_id", "type": "string"},
            {"name": "amount", "type": "double"},
        ],
    },
    "output": {"topic": "total-sales-topic1", "event": "OrderWithTotal"},
    "processing": {
        "group_by_field": "customer_id",
        "aggregate_field": "amount",
        "aggregate_as": "total_amount",
        "filter_field": "amount",
        "filter_operator": ">",
        "filter_value": 10,
    },
}


@contextlib.contextmanager
def working_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _write_definition(path, definition=DEFINITION):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(definition, handle)


class GenerateStreamProjectTest(unittest.TestCase):
    def test_generates_the_expected_project_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            definition_path = os.path.join(tmp, "definition.json")
            _write_definition(definition_path)
            with working_directory(tmp):
                base_dir = generate_stream_project(definition_path)

                self.assertEqual("crud-sales-streams", base_dir)
                java_base = Path(base_dir) / "src/main/java/com/example/sales"
                self.assertTrue((Path(base_dir) / "pom.xml").is_file())
                self.assertTrue((Path(base_dir) / "Dockerfile").is_file())
                self.assertTrue((Path(base_dir) / "docker-compose.yml").is_file())
                self.assertTrue((Path(base_dir) / ".gitignore").is_file())
                self.assertTrue(
                    (Path(base_dir) / "src/main/resources/application.yml").is_file()
                )
                self.assertTrue((java_base / "SalesStreamsApplication.java").is_file())
                self.assertTrue(
                    (java_base / "config/KafkaStreamsConfig.java").is_file()
                )
                self.assertTrue((java_base / "model/Order.java").is_file())
                self.assertTrue((java_base / "model/OrderWithTotal.java").is_file())
                self.assertTrue(
                    (java_base / "topology/SalesStreamsTopology.java").is_file()
                )
                test_base = Path(base_dir) / "src/test/java/com/example/sales"
                self.assertTrue(
                    (test_base / "topology/SalesStreamsTopologyTest.java").is_file()
                )

    def test_output_event_model_includes_the_aggregate_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            definition_path = os.path.join(tmp, "definition.json")
            _write_definition(definition_path)
            with working_directory(tmp):
                base_dir = generate_stream_project(definition_path)
                model = Path(
                    base_dir, "src/main/java/com/example/sales/model/OrderWithTotal.java"
                ).read_text(encoding="utf-8")

                self.assertIn("private Double totalAmount;", model)
                self.assertIn("private String orderId;", model)

    def test_refuses_to_overwrite_an_existing_directory_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            definition_path = os.path.join(tmp, "definition.json")
            _write_definition(definition_path)
            with working_directory(tmp):
                generate_stream_project(definition_path)

                with self.assertRaises(DefinitionError) as ctx:
                    generate_stream_project(definition_path)
                self.assertIn("--force", str(ctx.exception))

    def test_force_regenerates_an_existing_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            definition_path = os.path.join(tmp, "definition.json")
            _write_definition(definition_path)
            with working_directory(tmp):
                generate_stream_project(definition_path)
                base_dir = generate_stream_project(definition_path, overwrite=True)

                self.assertEqual("crud-sales-streams", base_dir)


@unittest.skipUnless(MAVEN, "Maven no está instalado")
class GeneratedStreamProjectAcceptanceTest(unittest.TestCase):
    def test_generated_stream_project_compiles_and_passes_its_tests(self):
        workspace = Path.cwd()
        with tempfile.TemporaryDirectory(
            prefix=".generated-tests-", dir=workspace
        ) as temporary_directory:
            root = Path(temporary_directory)
            definition_path = root / "definition.json"
            _write_definition(definition_path)
            with working_directory(root):
                base_dir = root / generate_stream_project(str(definition_path))

            local_repository = os.environ.get(
                "CRUD_GENERATOR_MAVEN_REPO", str(workspace / ".m2" / "repository")
            )
            result = subprocess.run(
                [MAVEN, f"-Dmaven.repo.local={local_repository}", "verify", "--quiet"],
                cwd=base_dir,
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
            if result.returncode != 0:
                self.fail(
                    f"Maven falló en {base_dir.name}.\n"
                    f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
                )


if __name__ == "__main__":
    unittest.main()
