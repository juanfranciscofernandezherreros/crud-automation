import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from crud_generator.security_profiles import build_security_config


REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATOR = REPO_ROOT / "generate_crud.py"


class EndpointSecurityProfileTest(unittest.TestCase):
    def test_security_config_contains_roles_and_permissions_per_endpoint(self):
        config = build_security_config([
            {
                "name": "list",
                "method": "GET",
                "path": "/api/clientes",
                "roles": ["USER", "ADMIN"],
                "permissions": ["cliente:read"],
            },
            {
                "name": "delete",
                "method": "DELETE",
                "path": "/api/clientes/{id}",
                "roles": ["ADMIN"],
                "permissions": ["cliente:delete"],
            },
        ])

        self.assertIn("hasAnyRole('USER', 'ADMIN') and hasAuthority('cliente:read')", config)
        self.assertIn("hasAnyRole('ADMIN') and hasAuthority('cliente:delete')", config)
        self.assertIn('HttpMethod.DELETE, "/api/clientes/*"', config)
        self.assertIn('"ROLE_ADMIN"', config)
        self.assertIn('"cliente:read"', config)
        self.assertIn('.requestMatchers("/api/**").denyAll()', config)


class SQLServerGeneratedTestsTest(unittest.TestCase):
    def test_sqlserver_generation_contains_only_sqlserver_database_tests(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "Factura",
                    "id:int,numero:string:not_blank",
                    "--database",
                    "sqlserver",
                ],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)

            project = Path(temp_dir) / "crud-factura"
            test_root = project / "src" / "test" / "java"
            integration = list(test_root.rglob("SQLServerIntegrationTest.java"))
            postgres_integration = list(test_root.rglob("PostgreSQLIntegrationTest.java"))
            self.assertEqual(1, len(integration))
            self.assertEqual([], postgres_integration)

            all_test_text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in test_root.rglob("*.java")
            )
            self.assertIn("MSSQLServerContainer", all_test_text)
            self.assertNotIn("PostgreSQLContainer", all_test_text)

            pom = (project / "pom.xml").read_text(encoding="utf-8")
            self.assertIn("<artifactId>mssqlserver</artifactId>", pom)
            self.assertNotIn("<artifactId>postgresql</artifactId>", pom)

            idempotency = next(
                (project / "src" / "main" / "java").rglob("IdempotencyService.java")
            ).read_text(encoding="utf-8")
            self.assertIn("sp_getapplock", idempotency)
            self.assertNotIn("pg_advisory_xact_lock", idempotency)


if __name__ == "__main__":
    unittest.main()
