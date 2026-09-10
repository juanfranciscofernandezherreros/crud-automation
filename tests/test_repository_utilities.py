import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_script(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GenerateCrudCompatibilityScriptTest(unittest.TestCase):
    def test_script_delegates_to_package_main(self):
        module = load_script("generate_crud_test_module", "generate_crud.py")
        self.assertTrue(callable(module.main))
        self.assertEqual("crud_generator.__main__", module.main.__module__)


class OrchestrateCrudTest(unittest.TestCase):
    def setUp(self):
        self.module = load_script("orchestrate_crud_test_module", "orchestrate_crud.py")

    def test_skip_github_runs_only_generation(self):
        generated = "Proyecto crud-producto generado con éxito.\n"
        with patch.object(
            self.module,
            "run_step",
            return_value=(0, generated),
        ) as run_step, patch.object(
            sys,
            "argv",
            [
                "orchestrate_crud.py",
                "Producto",
                "id:int,nombre:string",
                "--architecture",
                "hexagonal",
                "--skip-github",
            ],
        ):
            code = self.module.main()

        self.assertEqual(0, code)
        run_step.assert_called_once_with(
            [
                "generate_crud.py",
                "Producto",
                "id:int,nombre:string",
                "--architecture",
                "hexagonal",
            ],
            "Paso 1/2: generate_crud.py",
        )

    def test_successful_orchestration_generates_then_publishes(self):
        with patch.object(
            self.module,
            "run_step",
            side_effect=[
                (0, "Proyecto crud-cliente-clean generado con éxito.\n"),
                (0, "Repositorio publicado en GitHub: https://github.com/u/clientes\n"),
            ],
        ) as run_step, patch.object(
            sys,
            "argv",
            [
                "orchestrate_crud.py",
                "Cliente",
                "id:int,nombre:string",
                "--architecture",
                "clean",
                "--repo-name",
                "clientes",
                "--private",
                "--force",
                "--verify",
            ],
        ):
            code = self.module.main()

        self.assertEqual(0, code)
        self.assertEqual(2, run_step.call_count)
        generation = run_step.call_args_list[0].args[0]
        publication = run_step.call_args_list[1].args[0]
        self.assertIn("--force", generation)
        self.assertIn("--verify", generation)
        self.assertEqual(
            ["createRepo.py", "crud-cliente-clean", "clientes", "--private"],
            publication,
        )

    def test_generation_failure_stops_before_publication(self):
        with patch.object(
            self.module, "run_step", return_value=(2, "")
        ) as run_step, patch.object(
            sys,
            "argv",
            ["orchestrate_crud.py", "Producto", "id:int", "--skip-github"],
        ):
            code = self.module.main()

        self.assertEqual(2, code)
        self.assertEqual(1, run_step.call_count)

    def test_missing_generated_directory_in_output_is_an_error(self):
        with patch.object(
            self.module, "run_step", return_value=(0, "salida inesperada")
        ), patch.object(
            sys,
            "argv",
            ["orchestrate_crud.py", "Producto", "id:int", "--skip-github"],
        ):
            self.assertEqual(1, self.module.main())


class CreateRepoScriptTest(unittest.TestCase):
    def setUp(self):
        self.module = load_script("create_repo_test_module", "createRepo.py")

    def test_forwards_directory_name_and_private_flag(self):
        with patch.object(
            self.module,
            "push_to_github",
            return_value="https://github.com/user/mi-repo",
        ) as push, patch.object(
            sys,
            "argv",
            ["createRepo.py", "crud-producto", "mi-repo", "--private"],
        ):
            self.module.main()

        push.assert_called_once_with(
            "crud-producto", repo_name="mi-repo", private=True
        )

    def test_definition_error_exits_with_one(self):
        error = self.module.DefinitionError("gh no autenticado")
        with patch.object(self.module, "push_to_github", side_effect=error), patch.object(
            sys, "argv", ["createRepo.py", "crud-producto"]
        ):
            with self.assertRaises(SystemExit) as ctx:
                self.module.main()
        self.assertEqual(1, ctx.exception.code)


class UpdateApplicationSetScriptTest(unittest.TestCase):
    def setUp(self):
        self.module = load_script(
            "update_applicationset_test_module", "scripts/update_applicationset.py"
        )

    def test_discover_filters_archived_non_crud_and_missing_kustomization(self):
        repos = [
            {"name": "crud-a", "archived": False, "default_branch": "main"},
            {"name": "crud-b", "archived": True, "default_branch": "main"},
            {"name": "other", "archived": False, "default_branch": "main"},
            {"name": "crud-c", "archived": False, "default_branch": "develop"},
        ]
        with patch.object(self.module, "api_get", return_value=repos), patch.object(
            self.module,
            "has_kustomization",
            side_effect=lambda repo, branch: repo == "crud-a",
        ):
            self.assertEqual([("crud-a", "main")], self.module.discover())

    def test_render_contains_repo_branch_and_expected_argocd_fields(self):
        yaml = self.module.render([("crud-pedidos", "main")])
        self.assertIn("repo: crud-pedidos", yaml)
        self.assertIn("branch: main", yaml)
        self.assertIn("path: k8s", yaml)
        self.assertIn("CreateNamespace=true", yaml)
        self.assertIn(f"https://github.com/{self.module.OWNER}/", yaml)

    def test_main_writes_rendered_applicationset(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "applicationset.yaml"
            with patch.object(
                self.module, "discover", return_value=[("crud-a", "main")]
            ), patch.object(self.module, "OUTPUT", output):
                self.module.main()
            self.assertTrue(output.is_file())
            self.assertIn("repo: crud-a", output.read_text(encoding="utf-8"))

    def test_main_fails_cleanly_when_no_repositories_are_found(self):
        with patch.object(self.module, "discover", return_value=[]):
            with self.assertRaises(SystemExit) as ctx:
                self.module.main()
        self.assertIn("No se encontraron", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
