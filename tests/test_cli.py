import contextlib
import io
import unittest
from unittest.mock import patch

from crud_generator.cli import choose_architecture, main
from crud_generator.parsing import DefinitionError


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
            "Producto", "id:int,nombre:string", "layered",
            base_package=None, endpoints=None, overwrite=False,
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
            "Producto", "id:int,nombre:string", "hexagonal",
            base_package=None, endpoints=None, overwrite=False,
        )

    @patch("crud_generator.cli.generate_project", return_value="crud-producto")
    def test_force_flag_is_propagated_as_overwrite(self, generate_project):
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = main(["Producto", "id:int,nombre:string", "--force"])

        self.assertEqual(0, exit_code)
        generate_project.assert_called_once_with(
            "Producto", "id:int,nombre:string", "layered",
            base_package=None, endpoints=None, overwrite=True,
        )

    @patch(
        "crud_generator.cli.generate_stream_project",
        return_value="crud-sales-streams",
    )
    def test_generates_stream_project(self, generate_stream_project):
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = main(["--stream", "definition.json"])

        self.assertEqual(0, exit_code)
        generate_stream_project.assert_called_once_with(
            "definition.json", overwrite=False
        )
        self.assertIn("crud-sales-streams", stdout.getvalue())

    @patch(
        "crud_generator.cli.generate_stream_project",
        return_value="crud-sales-streams",
    )
    def test_stream_force_flag_is_propagated_as_overwrite(
        self, generate_stream_project
    ):
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = main(["--stream", "definition.json", "--force"])

        self.assertEqual(0, exit_code)
        generate_stream_project.assert_called_once_with(
            "definition.json", overwrite=True
        )

    @patch(
        "crud_generator.cli.generate_batch_project",
        return_value="spring-batch-coches",
    )
    def test_generates_batch_project(self, generate_batch_project):
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = main(["--batch"])

        self.assertEqual(0, exit_code)
        generate_batch_project.assert_called_once_with(None, overwrite=False)
        self.assertIn("spring-batch-coches", stdout.getvalue())

    @patch(
        "crud_generator.cli.generate_batch_project",
        return_value="mi-batch",
    )
    def test_batch_accepts_target_dir_and_force(self, generate_batch_project):
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = main(["--batch", "mi-batch", "--force"])

        self.assertEqual(0, exit_code)
        generate_batch_project.assert_called_once_with("mi-batch", overwrite=True)

    @patch("crud_generator.cli.push_to_github", return_value="https://github.com/user/crud-producto")
    @patch("crud_generator.cli.generate_project", return_value="crud-producto")
    def test_github_flag_publishes_generated_project(self, generate_project, push_to_github):
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = main(["Producto", "id:int,nombre:string", "--github"])

        self.assertEqual(0, exit_code)
        push_to_github.assert_called_once_with("crud-producto", repo_name=None, private=False)
        self.assertIn("https://github.com/user/crud-producto", stdout.getvalue())

    @patch("crud_generator.cli.push_to_github", return_value="https://github.com/user/mi-repo")
    @patch("crud_generator.cli.generate_batch_project", return_value="spring-batch-coches")
    def test_github_flag_accepts_repo_name_and_private(self, generate_batch_project, push_to_github):
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = main(["--batch", "--github", "mi-repo", "--private"])

        self.assertEqual(0, exit_code)
        push_to_github.assert_called_once_with(
            "spring-batch-coches", repo_name="mi-repo", private=True
        )

    @patch("crud_generator.cli.generate_project", return_value="crud-producto")
    def test_without_github_flag_does_not_publish(self, generate_project):
        with patch("crud_generator.cli.push_to_github") as push_to_github:
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = main(["Producto", "id:int,nombre:string"])

            self.assertEqual(0, exit_code)
            push_to_github.assert_not_called()

    @patch(
        "crud_generator.cli.push_to_github",
        side_effect=DefinitionError("gh no esta autenticado"),
    )
    @patch("crud_generator.cli.generate_project", return_value="crud-producto")
    def test_github_publish_failure_returns_two(self, generate_project, push_to_github):
        stderr = io.StringIO()

        with contextlib.redirect_stdout(io.StringIO()):
            with contextlib.redirect_stderr(stderr):
                exit_code = main(["Producto", "id:int,nombre:string", "--github"])

        self.assertEqual(2, exit_code)
        self.assertIn("gh no esta autenticado", stderr.getvalue())

    @patch("crud_generator.cli.verify_project")
    @patch("crud_generator.cli.generate_project", return_value="crud-producto")
    def test_verify_flag_runs_verification_and_reports_success(self, generate_project, verify_project):
        verify_project.return_value = {
            "ran": True,
            "success": True,
            "returncode": 0,
            "tests": {"run": 5, "failures": 0, "errors": 0, "skipped": 1},
        }
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = main(["Producto", "id:int,nombre:string", "--verify"])

        self.assertEqual(0, exit_code)
        verify_project.assert_called_once_with("crud-producto")
        self.assertIn("Verificación OK", stdout.getvalue())

    @patch("crud_generator.cli.push_to_github")
    @patch("crud_generator.cli.verify_project")
    @patch("crud_generator.cli.generate_project", return_value="crud-producto")
    def test_verify_failure_returns_three_and_skips_github(
        self, generate_project, verify_project, push_to_github
    ):
        verify_project.return_value = {
            "ran": True,
            "success": False,
            "returncode": 1,
            "log": "[ERROR] boom",
            "hint": None,
            "tests": None,
        }
        stderr = io.StringIO()

        with contextlib.redirect_stdout(io.StringIO()):
            with contextlib.redirect_stderr(stderr):
                exit_code = main(
                    ["Producto", "id:int,nombre:string", "--verify", "--github"]
                )

        self.assertEqual(3, exit_code)
        self.assertIn("Verificación FALLIDA", stderr.getvalue())
        push_to_github.assert_not_called()

    @patch("crud_generator.cli.generate_project", return_value="crud-producto")
    def test_without_verify_flag_does_not_run_verification(self, generate_project):
        with patch("crud_generator.cli.verify_project") as verify_project:
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = main(["Producto", "id:int,nombre:string"])

            self.assertEqual(0, exit_code)
            verify_project.assert_not_called()

    @patch("crud_generator.cli.save_conventions")
    @patch("crud_generator.cli.load_conventions", return_value={})
    @patch("crud_generator.cli.generate_project", return_value="crud-producto")
    def test_remember_flag_saves_effective_architecture(
        self, generate_project, load_conventions, save_conventions
    ):
        save_conventions.return_value = "crud-automation.conventions.json"
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = main(
                ["Producto", "id:int,nombre:string", "--architecture", "hexagonal", "--remember"]
            )

        self.assertEqual(0, exit_code)
        save_conventions.assert_called_once_with({"architecture": "hexagonal"})
        self.assertIn("Convenciones guardadas", stdout.getvalue())

    @patch("crud_generator.cli.load_conventions", return_value={})
    @patch("crud_generator.cli.generate_project", return_value="crud-producto")
    def test_without_remember_flag_does_not_save_conventions(self, generate_project, load_conventions):
        with patch("crud_generator.cli.save_conventions") as save_conventions:
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = main(["Producto", "id:int,nombre:string"])

            self.assertEqual(0, exit_code)
            save_conventions.assert_not_called()

    @patch(
        "crud_generator.cli.load_conventions",
        return_value={"architecture": "clean", "package": "com.miempresa.x", "endpoints": ["list"]},
    )
    @patch("crud_generator.cli.generate_project", return_value="crud-producto-clean")
    def test_conventions_provide_defaults_when_no_explicit_architecture(
        self, generate_project, load_conventions
    ):
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = main(["Producto", "id:int,nombre:string"])

        self.assertEqual(0, exit_code)
        generate_project.assert_called_once_with(
            "Producto", "id:int,nombre:string", "clean",
            base_package="com.miempresa.x", endpoints=["list"], overwrite=False,
        )

    @patch("crud_generator.cli.load_conventions", return_value={"architecture": "hexagonal"})
    @patch("crud_generator.cli.generate_project", return_value="crud-producto-hexagonal")
    def test_explicit_architecture_flag_wins_over_conventions(self, generate_project, load_conventions):
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = main(
                ["Producto", "id:int,nombre:string", "--architecture", "layered"]
            )

        self.assertEqual(0, exit_code)
        generate_project.assert_called_once_with(
            "Producto", "id:int,nombre:string", "layered",
            base_package=None, endpoints=None, overwrite=False,
        )

    @patch("crud_generator.cli.load_conventions", return_value={"architecture": "hexagonal"})
    @patch("crud_generator.cli.generate_project_from_json", return_value="crud-producto")
    def test_json_mode_ignores_conventions_architecture(self, generate_project_from_json, load_conventions):
        """Una convencion guardada no debe pisar el campo 'architecture' que
        un fichero JSON concreto pueda traer -- --json siempre pasa None
        como override salvo que el usuario pase --architecture explicito en
        esta misma ejecucion (ver generator.generate_project_from_json)."""
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = main(["--json", "definicion.json"])

        self.assertEqual(0, exit_code)
        generate_project_from_json.assert_called_once_with(
            "definicion.json", None, overwrite=False
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
