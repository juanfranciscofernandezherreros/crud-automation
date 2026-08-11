import contextlib
import io
import unittest
from unittest.mock import patch

from crud_generator.cli import choose_architecture, main


class CliTest(unittest.TestCase):
    @patch("crud_generator.cli.sys.stdin.isatty", return_value=True)
    @patch("builtins.input", return_value="2")
    def test_interactive_architecture_selection(self, _input, _isatty):
        with contextlib.redirect_stdout(io.StringIO()):
            architecture = choose_architecture()

        self.assertEqual("hexagonal", architecture)

    def test_returns_two_and_prints_validation_error(self):
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            exit_code = main(["Producto", "nombre:string"])

        self.assertEqual(2, exit_code)
        self.assertIn("incluir un atributo 'id'", stderr.getvalue())

    @patch("crud_generator.cli.generate_project", return_value="crud-producto")
    def test_generates_valid_project(self, generate_project):
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = main(["producto", "id:int,nombre:string"])

        self.assertEqual(0, exit_code)
        generate_project.assert_called_once_with(
            "Producto", "id:int,nombre:string", "layered", overwrite=False
        )

    @patch("crud_generator.cli.generate_project", return_value="crud-producto-hexagonal")
    def test_accepts_explicit_architecture(self, generate_project):
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = main(
                [
                    "Producto",
                    "id:int,nombre:string",
                    "--architecture",
                    "hexagonal",
                ]
            )

        self.assertEqual(0, exit_code)
        generate_project.assert_called_once_with(
            "Producto", "id:int,nombre:string", "hexagonal", overwrite=False
        )

    @patch("crud_generator.cli.generate_project", return_value="crud-producto")
    def test_force_flag_is_propagated_as_overwrite(self, generate_project):
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = main(["Producto", "id:int,nombre:string", "--force"])

        self.assertEqual(0, exit_code)
        generate_project.assert_called_once_with(
            "Producto", "id:int,nombre:string", "layered", overwrite=True
        )

    def test_existing_directory_without_force_is_rejected(self):
        import os
        import tempfile

        from crud_generator.writer import write_file

        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                write_file("crud-producto/marker.txt", "manual edit")
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    exit_code = main(["Producto", "id:int,nombre:string"])
                self.assertEqual(2, exit_code)
                self.assertIn("--force", stderr.getvalue())
                self.assertTrue(
                    os.path.isfile("crud-producto/marker.txt"),
                    "no debe tocar el directorio existente sin --force",
                )
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()
