import os
import tempfile
import unittest

from crud_generator.gitops import (
    DEFAULT_OWNER,
    extract_db_name,
    get_gitops_workflow,
    get_k8s_manifests,
    write_gitops_manifests,
)
from crud_generator.parsing import DefinitionError


class GetK8sManifestsTest(unittest.TestCase):
    def test_returns_all_expected_files(self):
        manifests = get_k8s_manifests("crud-articulo-hexagonal", "articulo_db")

        self.assertEqual(
            {
                "namespace.yaml", "secret.yaml", "postgres-service.yaml",
                "postgres-statefulset.yaml", "app-service.yaml", "deployment.yaml",
                "kustomization.yaml",
            },
            set(manifests.keys()),
        )

    def test_namespace_and_names_use_repo_name(self):
        manifests = get_k8s_manifests("crud-articulo-hexagonal", "articulo_db")

        self.assertIn("name: crud-articulo-hexagonal", manifests["namespace.yaml"])
        self.assertIn("namespace: crud-articulo-hexagonal", manifests["kustomization.yaml"])
        self.assertIn("name: crud-articulo-hexagonal-secrets", manifests["secret.yaml"])

    def test_deployment_references_db_name_and_ghcr_image(self):
        manifests = get_k8s_manifests("crud-articulo-hexagonal", "articulo_db")

        self.assertIn(
            "jdbc:postgresql://postgres:5432/articulo_db", manifests["deployment.yaml"],
        )
        self.assertIn(
            f"image: ghcr.io/{DEFAULT_OWNER}/crud-articulo-hexagonal:latest",
            manifests["deployment.yaml"],
        )

    def test_secret_carries_the_db_name(self):
        manifests = get_k8s_manifests("crud-articulo-hexagonal", "articulo_db")

        self.assertIn("POSTGRES_DB: articulo_db", manifests["secret.yaml"])

    def test_kustomization_lists_every_other_manifest_as_a_resource(self):
        manifests = get_k8s_manifests("crud-articulo-hexagonal", "articulo_db")

        for name in manifests:
            if name == "kustomization.yaml":
                continue
            self.assertIn(f"- {name}", manifests["kustomization.yaml"])


class GetGitopsWorkflowTest(unittest.TestCase):
    def test_builds_and_pushes_to_ghcr_on_push_to_main(self):
        workflow = get_gitops_workflow()

        self.assertIn('branches: ["main"]', workflow)
        self.assertIn("ghcr.io/${{ github.repository }}", workflow)
        self.assertIn("k8s/deployment.yaml", workflow)


class ExtractDbNameTest(unittest.TestCase):
    def test_reads_postgres_db_from_docker_compose(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "docker-compose.yml"), "w", encoding="utf-8") as file:
                file.write("services:\n  db:\n    environment:\n      - POSTGRES_DB=articulo_db\n")

            self.assertEqual("articulo_db", extract_db_name(tmp))

    def test_raises_when_docker_compose_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(DefinitionError):
                extract_db_name(tmp)

    def test_raises_when_postgres_db_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "docker-compose.yml"), "w", encoding="utf-8") as file:
                file.write("services:\n  db:\n    image: postgres:16-alpine\n")

            with self.assertRaises(DefinitionError):
                extract_db_name(tmp)


class WriteGitopsManifestsTest(unittest.TestCase):
    def test_writes_k8s_manifests_and_workflow_next_to_the_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "docker-compose.yml"), "w", encoding="utf-8") as file:
                file.write("      - POSTGRES_DB=articulo_db\n")

            db_name = write_gitops_manifests(tmp, "crud-articulo-hexagonal")

            self.assertEqual("articulo_db", db_name)
            for name in [
                "namespace.yaml", "secret.yaml", "postgres-service.yaml",
                "postgres-statefulset.yaml", "app-service.yaml", "deployment.yaml",
                "kustomization.yaml",
            ]:
                self.assertTrue(os.path.isfile(os.path.join(tmp, "k8s", name)))
            self.assertTrue(
                os.path.isfile(os.path.join(tmp, ".github", "workflows", "gitops.yml"))
            )


if __name__ == "__main__":
    unittest.main()
