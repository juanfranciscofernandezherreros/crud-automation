import contextlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from crud_generator.generator import generate_project


MAVEN = shutil.which("mvn.cmd") or shutil.which("mvn")


@contextlib.contextmanager
def working_directory(path):
    previous_directory = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous_directory)


@unittest.skipUnless(MAVEN, "Maven no está instalado")
class GeneratedProjectAcceptanceTest(unittest.TestCase):
    PROJECTS = {
        "Pedido": (
            "layered",
            "id:int, numero:string:not_blank:max=40:unique:index, creado_en:datetime, "
            "actualizado_en:datetime",
        ),
        "Producto": (
            "hexagonal",
            "id:int, nombre:string:not_blank:max=120, "
            "precio:decimal:required:positive, activo:boolean:required",
        ),
        "Cliente": (
            "clean",
            "id:int, nombre:string:not_blank:min=2:max=80, "
            "nacimiento:date:required, saldo:decimal:positive",
        ),
    }

    def test_generated_projects_compile_and_pass_their_tests(self):
        workspace = Path.cwd()
        with tempfile.TemporaryDirectory(
            prefix=".generated-tests-", dir=workspace
        ) as temporary_directory:
            root = Path(temporary_directory)
            with working_directory(root):
                for entity_name, (architecture, attributes) in self.PROJECTS.items():
                    with self.subTest(entity=entity_name):
                        project_directory = root / generate_project(
                            entity_name, attributes, architecture
                        )
                        self._run_maven_tests(project_directory, workspace)

    def _run_maven_tests(self, project_directory, workspace):
        command = [MAVEN]
        local_repository = os.environ.get(
            "CRUD_GENERATOR_MAVEN_REPO", str(workspace / ".m2" / "repository")
        )
        command.append(f"-Dmaven.repo.local={local_repository}")
        command.extend(["verify", "--quiet"])

        result = subprocess.run(
            command,
            cwd=project_directory,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        if result.returncode != 0:
            self.fail(
                f"Maven falló en {project_directory.name}.\n"
                f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )


if __name__ == "__main__":
    unittest.main()
