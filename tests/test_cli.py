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
            "Producto", "id:int,nombre:string", "layered"
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
            "Producto", "id:int,nombre:string", "hexagonal"
        )


if __name__ == "__main__":
    unittest.main()
