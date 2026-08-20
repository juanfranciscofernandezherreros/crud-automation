import unittest
from unittest.mock import patch

from crud_generator.parsing import DefinitionError
from crud_generator.wizard import run_wizard


class RunWizardTest(unittest.TestCase):
    @patch("crud_generator.wizard.sys.stdin.isatty", return_value=False)
    def test_rejects_non_interactive_terminal(self, isatty):
        with self.assertRaisesRegex(DefinitionError, "terminal interactiva"):
            run_wizard()

    @patch("crud_generator.wizard.configure_deployment", return_value={"argocd": False})
    @patch("crud_generator.wizard.install_endpoint_security")
    @patch("crud_generator.wizard.ask_endpoint_security", return_value=[])
    @patch("crud_generator.wizard.generate_project", return_value="crud-producto")
    @patch("crud_generator.wizard.sys.stdin.isatty", return_value=True)
    @patch("builtins.input")
    def test_minimal_happy_path_no_custom_endpoint(
        self,
        mock_input,
        isatty,
        generate_project,
        ask_endpoint_security,
        install_endpoint_security,
        configure_deployment,
    ):
        mock_input.side_effect = [
            "",                         # Java -> 21 por defecto
            "",                         # DB -> PostgreSQL por defecto
            "",                         # entorno -> local por defecto
            "Producto",                 # nombre de la entidad
            "id:int,nombre:string",     # campos
            "",                         # arquitectura -> default (layered)
            "",                         # endpoints -> default (todos)
            "n",                        # ¿añadir endpoint personalizado? no
            "",                         # paquete base -> default
            "n",                        # sobrescribir?
            "n",                        # verify?
            "n",                        # publicar en GitHub?
            "n",                        # remember?
        ]

        result = run_wizard()

        base_dir, verify, push_github, repo_name, private, remember, architecture, package, endpoints = result

        self.assertEqual("crud-producto", base_dir)
        self.assertFalse(verify)
        self.assertFalse(push_github)
        self.assertIsNone(repo_name)
        self.assertFalse(private)
        self.assertFalse(remember)
        self.assertEqual("layered", architecture)
        self.assertEqual("com.example.crud", package)
        self.assertIsNone(endpoints)

        ask_endpoint_security.assert_called_once_with("Producto", None, None)
        install_endpoint_security.assert_called_once_with([])
        generate_project.assert_called_once_with(
            "Producto", "id:int,nombre:string", "layered",
            base_package="com.example.crud", endpoints=None, overwrite=False,
            custom_endpoints=None,
        )
        configure_deployment.assert_called_once_with(
            "crud-producto",
            "producto",
            environment="local",
            use_argocd=False,
            namespace=None,
            gitops_repo=None,
        )

    @patch("crud_generator.wizard.configure_deployment", return_value={"argocd": False})
    @patch("crud_generator.wizard.install_endpoint_security")
    @patch("crud_generator.wizard.ask_endpoint_security", return_value=[])
    @patch("crud_generator.wizard.generate_project", return_value="crud-tarea-hexagonal")
    @patch("crud_generator.wizard.sys.stdin.isatty", return_value=True)
    @patch("builtins.input")
    def test_full_path_with_custom_endpoint_and_github(
        self,
        mock_input,
        isatty,
        generate_project,
        ask_endpoint_security,
        install_endpoint_security,
        configure_deployment,
    ):
        mock_input.side_effect = [
            "21",                           # Java 21
            "postgresql",                   # PostgreSQL
            "local",                        # entorno local
            "Tarea",                        # entidad
            "id:int,titulo:string",         # campos
            "hexagonal",                    # arquitectura
            "list,get,create",              # endpoints
            "s",                            # ¿añadir endpoint personalizado? si
            "completar",                    # nombre
            "",                             # metodo -> default POST
            "/{id}/completar",              # path
            "",                             # request fields -> ninguno (vacio)
            "completada:boolean",           # response field 1
            "",                             # response fields -> terminar
            "n",                            # ¿añadir otro endpoint? no
            "com.miempresa.tareas",         # paquete
            "s",                            # sobrescribir
            "s",                            # verify
            "s",                            # publicar en GitHub
            "mi-repo",                      # nombre del repo
            "s",                            # privado
            "s",                            # remember
        ]

        result = run_wizard()

        base_dir, verify, push_github, repo_name, private, remember, architecture, package, endpoints = result

        self.assertEqual("crud-tarea-hexagonal", base_dir)
        self.assertTrue(verify)
        self.assertTrue(push_github)
        self.assertEqual("mi-repo", repo_name)
        self.assertTrue(private)
        self.assertTrue(remember)
        self.assertEqual("hexagonal", architecture)
        self.assertEqual("com.miempresa.tareas", package)
        self.assertEqual(["list", "get", "create"], endpoints)

        generate_project.assert_called_once()
        call_kwargs = generate_project.call_args.kwargs
        custom_endpoints = call_kwargs["custom_endpoints"]
        self.assertEqual(1, len(custom_endpoints))
        self.assertEqual("completar", custom_endpoints[0]["name"])
        self.assertEqual("POST", custom_endpoints[0]["method"])
        self.assertIsNone(custom_endpoints[0]["request_fields"] or None)
        self.assertEqual(1, len(custom_endpoints[0]["response_fields"]))
        self.assertTrue(call_kwargs["overwrite"])
        ask_endpoint_security.assert_called_once_with(
            "Tarea", ["list", "get", "create"], custom_endpoints
        )
        install_endpoint_security.assert_called_once_with([])
        configure_deployment.assert_called_once_with(
            "crud-tarea-hexagonal",
            "tarea",
            environment="local",
            use_argocd=False,
            namespace=None,
            gitops_repo=None,
        )

    @patch("crud_generator.wizard.configure_deployment", return_value={"argocd": False})
    @patch("crud_generator.wizard.install_endpoint_security")
    @patch("crud_generator.wizard.ask_endpoint_security", return_value=[])
    @patch("crud_generator.wizard.sys.stdin.isatty", return_value=True)
    @patch("builtins.input")
    def test_reprompts_on_invalid_entity_name(
        self,
        mock_input,
        isatty,
        ask_endpoint_security,
        install_endpoint_security,
        configure_deployment,
    ):
        mock_input.side_effect = [
            "",                          # Java -> 21
            "",                          # DB -> PostgreSQL
            "",                          # entorno -> local
            "no-valido",                 # invalido: contiene guion
            "Producto",                  # valido
            "id:int",                    # campos
            "",                          # arquitectura
            "",                          # endpoints
            "n",                         # custom endpoint
            "",                          # paquete
            "n", "n", "n", "n",       # overwrite/verify/github/remember
        ]

        with patch("crud_generator.wizard.generate_project", return_value="crud-producto"):
            base_dir, *_ = run_wizard()

        self.assertEqual("crud-producto", base_dir)
        ask_endpoint_security.assert_called_once_with("Producto", None, None)
        install_endpoint_security.assert_called_once_with([])
        configure_deployment.assert_called_once()

    @patch("crud_generator.wizard.configure_deployment", return_value={"argocd": False})
    @patch("crud_generator.wizard.install_endpoint_security")
    @patch("crud_generator.wizard.ask_endpoint_security", return_value=[])
    @patch("crud_generator.wizard._install_java_version")
    @patch("crud_generator.wizard.install_sqlserver_test_profile")
    @patch("crud_generator.wizard.install_database_profile")
    @patch("crud_generator.wizard.generate_project", return_value="crud-factura")
    @patch("crud_generator.wizard.sys.stdin.isatty", return_value=True)
    @patch("builtins.input")
    def test_java17_sqlserver_selection_installs_expected_profiles(
        self,
        mock_input,
        isatty,
        generate_project,
        install_database_profile,
        install_sqlserver_test_profile,
        install_java_version,
        ask_endpoint_security,
        install_endpoint_security,
        configure_deployment,
    ):
        mock_input.side_effect = [
            "17",
            "sqlserver",
            "local",
            "Factura",
            "id:int,numero:string",
            "",
            "list,get",
            "n",
            "",
            "n", "n", "n", "n",
        ]

        result = run_wizard()

        self.assertEqual("crud-factura", result[0])
        install_database_profile.assert_called_once_with("sqlserver")
        install_sqlserver_test_profile.assert_called_once_with()
        install_java_version.assert_called_once_with("17")
        ask_endpoint_security.assert_called_once_with("Factura", ["list", "get"], None)
        install_endpoint_security.assert_called_once_with([])
        generate_project.assert_called_once()
        configure_deployment.assert_called_once_with(
            "crud-factura",
            "factura",
            environment="local",
            use_argocd=False,
            namespace=None,
            gitops_repo=None,
        )

    @patch("crud_generator.wizard.configure_deployment", return_value={"argocd": True})
    @patch("crud_generator.wizard.install_endpoint_security")
    @patch("crud_generator.wizard.ask_endpoint_security", return_value=[])
    @patch("crud_generator.wizard.generate_project", return_value="crud-pedido")
    @patch("crud_generator.wizard.sys.stdin.isatty", return_value=True)
    @patch("builtins.input")
    def test_dev_environment_can_enable_argocd(
        self,
        mock_input,
        isatty,
        generate_project,
        ask_endpoint_security,
        install_endpoint_security,
        configure_deployment,
    ):
        mock_input.side_effect = [
            "21",
            "postgresql",
            "dev",
            "Pedido",
            "id:int,numero:string",
            "",
            "list,get",
            "n",
            "",
            "pedidos-dev",
            "s",
            "https://github.com/acme/pedidos-gitops.git",
            "n", "n", "n", "n",
        ]

        result = run_wizard()

        self.assertEqual("crud-pedido", result[0])
        configure_deployment.assert_called_once_with(
            "crud-pedido",
            "pedido",
            environment="dev",
            use_argocd=True,
            namespace="pedidos-dev",
            gitops_repo="https://github.com/acme/pedidos-gitops.git",
        )


if __name__ == "__main__":
    unittest.main()
