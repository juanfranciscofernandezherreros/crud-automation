import contextlib
import importlib
import os
import pkgutil
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import crud_generator
from crud_generator.generate_service import generate_batch_project
from crud_generator.generator import generate_project, generate_project_from_json
from crud_generator.stream_generator import generate_stream_project


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = REPO_ROOT / "examples"
MAVEN = shutil.which("mvn.cmd") or shutil.which("mvn")
CRUD_EXAMPLES = (
    "categorias-arbol.json",
    "dividendos.json",
    "empleados-clean.json",
    "fondoinversion.json",
    "tareas-endpoint-personalizado.json",
    "tipos-y-validaciones.json",
    "transferencia.json",
    "ventas.json",
)
STREAM_EXAMPLES = (
    "crypto-relay.json",
    "sales-streams.json",
    "sensores-stream.json",
)


@contextlib.contextmanager
def working_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def run_maven_verify(project_dir):
    local_repository = os.environ.get(
        "CRUD_GENERATOR_MAVEN_REPO", str(REPO_ROOT / ".m2" / "repository")
    )
    return subprocess.run(
        [MAVEN, f"-Dmaven.repo.local={local_repository}", "verify", "--quiet"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )


class PublicFeatureMatrixTest(unittest.TestCase):
    """Smoke tests de todas las rutas públicas principales del producto.

    Los tests especializados siguen validando el detalle de cada módulo. Esta
    matriz evita que una funcionalidad completa deje de ser invocable aunque
    sus piezas unitarias continúen pasando por separado.
    """

    def test_public_python_api_is_importable(self):
        self.assertTrue(callable(crud_generator.generate_project))
        self.assertTrue(callable(crud_generator.parse_attributes))
        self.assertTrue(callable(crud_generator.normalize_entity_name))
        self.assertTrue(issubclass(crud_generator.DefinitionError, ValueError))

    def test_every_package_module_imports(self):
        modules = sorted(
            module.name
            for module in pkgutil.iter_modules(
                crud_generator.__path__, prefix="crud_generator."
            )
        )
        self.assertTrue(modules)
        for module_name in modules:
            with self.subTest(module=module_name):
                imported = importlib.import_module(module_name)
                self.assertIsNotNone(imported)

    def test_all_three_crud_architectures_generate_real_projects(self):
        expected = {
            "layered": "crud-producto",
            "hexagonal": "crud-producto-hexagonal",
            "clean": "crud-producto-clean",
        }
        attrs = "id:int,nombre:string:not_blank,precio:decimal:positive"

        with tempfile.TemporaryDirectory() as tmp:
            for architecture, expected_dir in expected.items():
                with self.subTest(architecture=architecture):
                    case_dir = Path(tmp) / architecture
                    case_dir.mkdir()
                    with working_directory(case_dir):
                        base_dir = generate_project("Producto", attrs, architecture)
                    project = case_dir / base_dir
                    self.assertEqual(expected_dir, base_dir)
                    self.assertTrue((project / "pom.xml").is_file())
                    self.assertTrue((project / "docs/index.html").is_file())
                    self.assertTrue((project / "src/main/resources").is_dir())
                    self.assertTrue((project / "src/test").is_dir())

    def test_minimal_mode_generates_only_the_small_skeleton(self):
        with tempfile.TemporaryDirectory() as tmp, working_directory(tmp):
            base_dir = generate_project("Smoke", "ignored", "minimal")
            project = Path(tmp) / base_dir
            app = project / "app"

            self.assertEqual("crud-smoke-minimal", base_dir)
            self.assertTrue((app / "pom.xml").is_file())
            self.assertTrue((app / "Dockerfile").is_file())
            self.assertTrue((app / "src/main/resources/application.yml").is_file())
            self.assertFalse((app / "src/main/resources/db").exists())
            self.assertFalse((project / "docker-compose.yml").exists())

    def test_every_crud_example_generates_successfully(self):
        with tempfile.TemporaryDirectory() as tmp:
            for filename in CRUD_EXAMPLES:
                with self.subTest(example=filename):
                    case_dir = Path(tmp) / filename.removesuffix(".json")
                    case_dir.mkdir()
                    with working_directory(case_dir):
                        base_dir = generate_project_from_json(str(EXAMPLES / filename))
                    project = case_dir / base_dir
                    self.assertTrue(project.is_dir(), filename)
                    self.assertTrue((project / "pom.xml").is_file(), filename)

    def test_every_stream_example_generates_successfully(self):
        with tempfile.TemporaryDirectory() as tmp:
            for filename in STREAM_EXAMPLES:
                with self.subTest(example=filename):
                    case_dir = Path(tmp) / filename.removesuffix(".json")
                    case_dir.mkdir()
                    with working_directory(case_dir):
                        base_dir = generate_stream_project(str(EXAMPLES / filename))
                    project = case_dir / base_dir
                    self.assertTrue((project / "pom.xml").is_file(), filename)
                    self.assertTrue((project / "src/main/avro").is_dir(), filename)
                    self.assertTrue((project / "src/test/java").is_dir(), filename)

    def test_batch_mode_generates_runnable_project_layout(self):
        with tempfile.TemporaryDirectory() as tmp, working_directory(tmp):
            base_dir = generate_batch_project()
            project = Path(tmp) / base_dir

            self.assertEqual("spring-batch-coches", base_dir)
            self.assertTrue((project / "pom.xml").is_file())
            self.assertTrue((project / "Dockerfile").is_file())
            self.assertTrue((project / "docker-compose.yml").is_file())
            self.assertTrue(
                (project / "src/test/java/com/example/batch/job/CochesJobConfigTest.java").is_file()
            )

    def test_python_dash_m_entrypoint_really_executes_the_local_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            current_pythonpath = env.get("PYTHONPATH")
            env["PYTHONPATH"] = (
                str(REPO_ROOT)
                if not current_pythonpath
                else str(REPO_ROOT) + os.pathsep + current_pythonpath
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "crud_generator",
                    "Smoke",
                    "--architecture",
                    "minimal",
                ],
                cwd=tmp,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("generado con éxito", result.stdout)
            self.assertTrue((Path(tmp) / "crud-smoke-minimal/app/pom.xml").is_file())

    @unittest.skipUnless(MAVEN, "Maven no está instalado")
    def test_minimal_generated_project_compiles_and_tests(self):
        with tempfile.TemporaryDirectory() as tmp, working_directory(tmp):
            base_dir = generate_project("Smoke", "", "minimal")
            result = run_maven_verify(Path(tmp) / base_dir / "app")
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    @unittest.skipUnless(MAVEN, "Maven no está instalado")
    def test_batch_generated_project_compiles_and_runs_its_tests(self):
        with tempfile.TemporaryDirectory() as tmp, working_directory(tmp):
            base_dir = generate_batch_project()
            result = run_maven_verify(Path(tmp) / base_dir)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
