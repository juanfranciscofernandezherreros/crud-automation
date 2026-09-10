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
    @patch("crud_generator.wizard._install_java_version")
    @patch("crud_generator.wizard.install_database_profile")
    @patch("crud_generator.wizard.sys.stdin.isatty", return_value=True)
    @patch("builtins.input")
    def test_crud_happy_path_uses_defaults_and_all_endpoints(
        self,
        mock_input,
        isatty,
        install_database_profile,
        install_java_version,
        generate_project,
        ask_endpoint_security,
        install_endpoint_security,
        configure_deployment,
    ):
        mock_input.side_effect = [
            "",                         # Java -> 21
            "",                         # entorno -> local
            "Producto",                 # entidad
            "",                         # arquitectura -> layered
            "",                         # DB -> PostgreSQL
            "id:int,nombre:string",     # campos
            "",                         # endpoints -> todos
            "n",                        # endpoint personalizado
            "n",                        # personalizar seguridad -> no
            "",                         # paquete base
            "n",                        # sobrescribir
            "n",                        # verify
            "n",                        # publicar GitHub
            "n",                        # guardar defaults
        ]

        result = run_wizard()

        self.assertEqual("crud-producto", result[0])
        self.assertEqual("layered", result[6])
        self.assertEqual("com.example.crud", result[7])
        self.assertEqual(
            ["list", "get", "create", "update", "patch", "delete"], result[8]
        )
        install_database_profile.assert_called_once_with("postgresql")
        install_java_version.assert_called_once_with("21")
        ask_endpoint_security.assert_called_once_with(
            "Producto",
            ["list", "get", "create", "update", "patch", "delete"],
            None,
        )
        install_endpoint_security.assert_called_once_with([])
        generate_project.assert_called_once_with(
            "Producto",
            "id:int,nombre:string",
            "layered",
            base_package="com.example.crud",
            endpoints=["list", "get", "create", "update", "patch", "delete"],
            overwrite=False,
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
    @patch("crud_generator.wizard._install_java_version")
    @patch("crud_generator.wizard.install_database_profile")
    @patch("crud_generator.wizard.sys.stdin.isatty", return_value=True)
    @patch("builtins.input")
    def test_crud_can_publish_to_github(
        self,
        mock_input,
        isatty,
        install_database_profile,
        install_java_version,
        generate_project,
        ask_endpoint_security,
        install_endpoint_security,
        configure_deployment,
    ):
        mock_input.side_effect = [
            "17",                       # Java
            "local",                    # entorno
            "Tarea",                    # entidad
            "hexagonal",                # arquitectura
            "postgresql",               # DB
            "id:int,titulo:string",     # campos
            "list,get,create",          # endpoints
            "n",                        # endpoint personalizado
            "n",                        # seguridad por defecto
            "com.miempresa.tareas",     # paquete
            "n",                        # sobrescribir
            "s",                        # verify
            "s",                        # publicar GitHub
            "mi-repo",                  # nombre repo
            "s",                        # privado
            "s",                        # guardar defaults
        ]

        result = run_wizard()

        self.assertEqual("crud-tarea-hexagonal", result[0])
        self.assertTrue(result[1])
        self.assertTrue(result[2])
        self.assertEqual("mi-repo", result[3])
        self.assertTrue(result[4])
        self.assertTrue(result[5])
        self.assertEqual("hexagonal", result[6])
        self.assertEqual("com.miempresa.tareas", result[7])
        self.assertEqual(["list", "get", "create"], result[8])

    @patch("crud_generator.wizard.configure_deployment", return_value={"argocd": False})
    @patch("crud_generator.wizard.install_endpoint_security")
    @patch("crud_generator.wizard.ask_endpoint_security")
    @patch("crud_generator.wizard.generate_project", return_value="crud-smoke-minimal")
    @patch("crud_generator.wizard._install_java_version")
    @patch("crud_generator.wizard.install_sqlserver_test_profile")
    @patch("crud_generator.wizard.install_database_profile")
    @patch("crud_generator.wizard.sys.stdin.isatty", return_value=True)
    @patch("builtins.input")
    def test_minimal_skips_database_fields_endpoints_and_security(
        self,
        mock_input,
        isatty,
        install_database_profile,
        install_sqlserver_test_profile,
        install_java_version,
        generate_project,
        ask_endpoint_security,
        install_endpoint_security,
        configure_deployment,
    ):
        mock_input.side_effect = [
            "",             # Java -> 21
            "",             # entorno -> local
            "Smoke",        # nombre
            "minimal",      # arquitectura
            "",             # paquete base
            "n",            # sobrescribir
            "n",            # verify
            "n",            # GitHub
            "n",            # guardar defaults
        ]

        result = run_wizard()

        self.assertEqual("crud-smoke-minimal", result[0])
        self.assertEqual("minimal", result[6])
        self.assertIsNone(result[8])
        install_database_profile.assert_not_called()
        install_sqlserver_test_profile.assert_not_called()
        ask_endpoint_security.assert_not_called()
        install_endpoint_security.assert_not_called()
        install_java_version.assert_called_once_with("21")
        generate_project.assert_called_once_with(
            "Smoke",
            "",
            "minimal",
            base_package="com.example.crud",
            endpoints=None,
            overwrite=False,
            custom_endpoints=None,
        )

    @patch("crud_generator.wizard.configure_deployment", return_value={"argocd": True})
    @patch("crud_generator.wizard.install_endpoint_security")
    @patch("crud_generator.wizard.ask_endpoint_security", return_value=[])
    @patch("crud_generator.wizard.generate_project", return_value="crud-pedido")
    @patch("crud_generator.wizard._install_java_version")
    @patch("crud_generator.wizard.install_database_profile")
    @patch("crud_generator.wizard.sys.stdin.isatty", return_value=True)
    @patch("builtins.input")
    def test_dev_environment_can_enable_argocd(
        self,
        mock_input,
        isatty,
        install_database_profile,
        install_java_version,
        generate_project,
        ask_endpoint_security,
        install_endpoint_security,
        configure_deployment,
    ):
        mock_input.side_effect = [
            "21",
            "dev",
            "Pedido",
            "layered",
            "postgresql",
            "id:int,numero:string",
            "list,get",
            "n",
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
