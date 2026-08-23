import tempfile
import unittest
from pathlib import Path

from crud_generator.deployment import configure_deployment, normalize_environment


class DeploymentGenerationTest(unittest.TestCase):
    def test_local_generates_profiles_without_kubernetes_or_argocd(self):
        with tempfile.TemporaryDirectory() as directory:
            result = configure_deployment(directory, "factura", environment="local")
            root = Path(directory)

            self.assertFalse(result["kubernetes"])
            self.assertFalse(result["argocd"])
            self.assertTrue((root / "src/main/resources/application-local.yml").is_file())
            self.assertTrue((root / "src/main/resources/application-dev.yml").is_file())
            self.assertTrue((root / "src/main/resources/application-pre.yml").is_file())
            self.assertTrue((root / "src/main/resources/application-pro.yml").is_file())
            self.assertFalse((root / "deploy/k8s").exists())
            self.assertFalse((root / "deploy/argocd").exists())
            self.assertIn(
                "SPRING_PROFILES_ACTIVE=local",
                (root / ".env.environment").read_text(encoding="utf-8"),
            )

    def test_dev_with_argocd_generates_kubernetes_and_application(self):
        with tempfile.TemporaryDirectory() as directory:
            result = configure_deployment(
                directory,
                "pedido",
                environment="dev",
                use_argocd=True,
                namespace="pedidos-dev",
                gitops_repo="https://github.com/acme/pedidos-gitops.git",
            )
            root = Path(directory)

            self.assertTrue(result["kubernetes"])
            self.assertTrue(result["argocd"])
            deployment = (root / "deploy/k8s/deployment.yaml").read_text(encoding="utf-8")
            application = (root / "deploy/argocd/application.yaml").read_text(encoding="utf-8")
            self.assertIn("namespace: pedidos-dev", deployment)
            self.assertIn("SPRING_PROFILES_ACTIVE", deployment)
            self.assertIn("repoURL: https://github.com/acme/pedidos-gitops.git", application)
            self.assertIn("path: deploy/k8s", application)

    def test_argocd_requires_gitops_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "repositorio GitOps"):
                configure_deployment(
                    directory,
                    "pedido",
                    environment="pre",
                    use_argocd=True,
                )

    def test_environment_aliases(self):
        self.assertEqual("pro", normalize_environment("prod"))
        self.assertEqual("pre", normalize_environment("staging"))
        with self.assertRaises(ValueError):
            normalize_environment("qa")


if __name__ == "__main__":
    unittest.main()
