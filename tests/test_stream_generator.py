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

PASSTHROUGH_DEFINITION = {
    "project": "crypto-relay",
    "package": "com.example.crypto",
    "input": {
        "topic": "crypto-prices-in",
        "event": "CryptoPrice",
        "fields": [
            {"name": "symbol", "type": "string"},
            {"name": "price_usd", "type": "double"},
            {"name": "volume", "type": "double"},
        ],
    },
    "output": {"topic": "crypto-prices-out", "event": "CryptoPriceRelayed"},
}

# Sin filtro configurado: es el caso que revienta con NullPointerException si
# la topologia no descarta tombstones por su cuenta (ver stream_templates._filter_line).
AGGREGATION_WITHOUT_FILTER_DEFINITION = {
    "project": "agg-no-filter",
    "package": "com.example.aggnofilter",
    "input": {
        "topic": "in-topic",
        "event": "Reading",
        "fields": [
            {"name": "sensor_id", "type": "string"},
            {"name": "value", "type": "double"},
        ],
    },
    "output": {"topic": "out-topic", "event": "ReadingWithTotal"},
    "processing": {
        "group_by_field": "sensor_id",
        "aggregate_field": "value",
        # Deliberadamente distinto de "total_amount": get_topology_test tenia
        # el getter hardcodeado a getTotalAmount() sin mirar este valor.
        "aggregate_as": "total_value",
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


class GenerateStreamProjectPassthroughTest(unittest.TestCase):
    def test_output_model_mirrors_the_input_fields_exactly(self):
        with tempfile.TemporaryDirectory() as tmp:
            definition_path = os.path.join(tmp, "definition.json")
            _write_definition(definition_path, PASSTHROUGH_DEFINITION)
            with working_directory(tmp):
                base_dir = generate_stream_project(definition_path)
                java_base = Path(base_dir, "src/main/java/com/example/crypto")
                model = (java_base / "model/CryptoPriceRelayed.java").read_text(encoding="utf-8")

                self.assertIn("private String symbol;", model)
                self.assertIn("private Double priceUsd;", model)
                self.assertIn("private Double volume;", model)
                # A diferencia del modo con agregacion, no se añade ningun campo extra.
                self.assertNotIn("total", model.lower())

    def test_topology_has_no_state_store_or_join(self):
        with tempfile.TemporaryDirectory() as tmp:
            definition_path = os.path.join(tmp, "definition.json")
            _write_definition(definition_path, PASSTHROUGH_DEFINITION)
            with working_directory(tmp):
                base_dir = generate_stream_project(definition_path)
                topology = Path(
                    base_dir, "src/main/java/com/example/crypto/topology/CryptoRelayTopology.java"
                ).read_text(encoding="utf-8")

                self.assertIn(".mapValues(", topology)
                self.assertIn(".filter((k, v) -> v != null)", topology)
                self.assertNotIn("Materialized", topology)
                self.assertNotIn(".join(", topology)
                self.assertNotIn("KGroupedStream", topology)

    def test_topology_test_relays_and_ignores_tombstones(self):
        with tempfile.TemporaryDirectory() as tmp:
            definition_path = os.path.join(tmp, "definition.json")
            _write_definition(definition_path, PASSTHROUGH_DEFINITION)
            with working_directory(tmp):
                base_dir = generate_stream_project(definition_path)
                test_file = Path(
                    base_dir,
                    "src/test/java/com/example/crypto/topology/CryptoRelayTopologyTest.java",
                ).read_text(encoding="utf-8")

                self.assertIn("relaysEventUnchanged", test_file)
                self.assertIn("tombstoneTest", test_file)
                self.assertNotIn("stateStore", test_file)


@unittest.skipUnless(MAVEN, "Maven no está instalado")
class GeneratedStreamProjectAcceptanceTest(unittest.TestCase):
    DEFINITIONS = {
        "aggregation_with_filter": DEFINITION,
        "aggregation_without_filter": AGGREGATION_WITHOUT_FILTER_DEFINITION,
        "passthrough": PASSTHROUGH_DEFINITION,
    }

    def test_generated_stream_projects_compile_and_pass_their_tests(self):
        workspace = Path.cwd()
        local_repository = os.environ.get(
            "CRUD_GENERATOR_MAVEN_REPO", str(workspace / ".m2" / "repository")
        )
        with tempfile.TemporaryDirectory(
            prefix=".generated-tests-", dir=workspace
        ) as temporary_directory:
            root = Path(temporary_directory)
            for name, definition in self.DEFINITIONS.items():
                with self.subTest(definition=name):
                    definition_path = root / f"{name}.json"
                    _write_definition(definition_path, definition)
                    with working_directory(root):
                        base_dir = root / generate_stream_project(str(definition_path))

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
