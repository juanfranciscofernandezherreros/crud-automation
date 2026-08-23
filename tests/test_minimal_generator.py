import contextlib
import os
import tempfile
import unittest
from pathlib import Path

from crud_generator.generator import generate_project
from crud_generator.minimal_generator import generate_minimal_project
from crud_generator.parsing import DefinitionError


@contextlib.contextmanager
def working_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class MinimalGeneratorTest(unittest.TestCase):
    def test_generates_bare_app_skeleton_ignoring_fields(self):
        with tempfile.TemporaryDirectory() as tmp, working_directory(tmp):
            base_dir = generate_minimal_project("Producto")

            self.assertEqual("crud-producto-minimal", base_dir)
            app_dir = Path(tmp) / base_dir / "app"
            self.assertTrue((app_dir / "pom.xml").exists())
            self.assertTrue((app_dir / "Dockerfile").exists())
            self.assertTrue((app_dir / ".dockerignore").exists())
            self.assertTrue((app_dir / "src/main/resources/application.yml").exists())

            java_base = app_dir / "src/main/java/com/example/crud"
            self.assertTrue((java_base / "ProductoApplication.java").exists())
            controller = (java_base / "ProductoController.java").read_text(encoding="utf-8")
            self.assertIn('@GetMapping("/producto")', controller)
            self.assertIn("Hello from Producto", controller)

            test_file = (
                app_dir / "src/test/java/com/example/crud/ProductoControllerTest.java"
            ).read_text(encoding="utf-8")
            self.assertIn("/producto", test_file)

            # No genera nada de CRUD/BD/seguridad/observabilidad.
            self.assertFalse((app_dir / "src/main/resources/db").exists())
            self.assertFalse((Path(tmp) / base_dir / "docker-compose.yml").exists())

    def test_dispatches_from_generate_project_and_ignores_attrs(self):
        with tempfile.TemporaryDirectory() as tmp, working_directory(tmp):
            base_dir = generate_project("Pedido", "esto no es un DSL valido", "minimal")

            self.assertEqual("crud-pedido-minimal", base_dir)
            self.assertTrue((Path(tmp) / base_dir / "app" / "pom.xml").exists())

    def test_refuses_to_overwrite_without_force(self):
        with tempfile.TemporaryDirectory() as tmp, working_directory(tmp):
            generate_minimal_project("Producto")
            with self.assertRaises(DefinitionError):
                generate_minimal_project("Producto")

    def test_respects_custom_base_package(self):
        with tempfile.TemporaryDirectory() as tmp, working_directory(tmp):
            base_dir = generate_minimal_project("Producto", base_package="com.acme.hello")

            java_base = Path(tmp) / base_dir / "app/src/main/java/com/acme/hello"
            self.assertTrue((java_base / "ProductoApplication.java").exists())
            content = (java_base / "ProductoApplication.java").read_text(encoding="utf-8")
            self.assertIn("package com.acme.hello;", content)


if __name__ == "__main__":
    unittest.main()
