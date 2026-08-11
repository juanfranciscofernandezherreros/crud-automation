import contextlib
import os
from pathlib import Path
import tempfile
import unittest

from crud_generator.documentation import get_documentation_html
from crud_generator.generator import generate_project
from crud_generator.parsing import parse_attributes


@contextlib.contextmanager
def working_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class DocumentationTest(unittest.TestCase):
    DEFINITION = (
        "id:int, isin:string:not_blank:max=12:unique, "
        "patrimonio:decimal:required:positive, activo:boolean:index"
    )

    def test_renders_entity_fields_command_and_production_features(self):
        html = get_documentation_html(
            "FondoInversion",
            "fondoinversion",
            "hexagonal",
            parse_attributes(self.DEFINITION),
            self.DEFINITION,
        )

        self.assertIn("<h1>FondoInversion</h1>", html)
        self.assertIn("Arquitectura hexagonal", html)
        self.assertIn("patrimonio", html)
        self.assertIn("BigDecimal", html)
        self.assertIn("VARCHAR(12) NOT NULL UNIQUE CHECK", html)
        self.assertIn("NOT NULL CHECK", html)
        self.assertIn("--architecture hexagonal", html)
        self.assertIn(
            "&quot;activo:boolean:index&quot; `\n  --architecture hexagonal", html
        )
        self.assertIn("Idempotency-Key", html)
        self.assertIn("Testcontainers", html)
        self.assertIn(".env.example", html)
        self.assertIn("docker compose up", html)

    def test_every_architecture_generates_its_documentation_file(self):
        with tempfile.TemporaryDirectory() as directory:
            with working_directory(directory):
                for architecture in ("layered", "hexagonal", "clean"):
                    with self.subTest(architecture=architecture):
                        project = Path(
                            generate_project(
                                "Producto", "id:int, precio:decimal", architecture
                            )
                        )
                        documentation = project / "docs" / "index.html"

                        self.assertTrue(documentation.is_file())
                        content = documentation.read_text(encoding="utf-8")
                        self.assertIn("<h1>Producto</h1>", content)
                        self.assertIn(f"--architecture {architecture}", content)


if __name__ == "__main__":
    unittest.main()
