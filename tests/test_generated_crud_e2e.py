import contextlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap
import unittest

from crud_generator.generator import generate_project


MAVEN = shutil.which("mvn.cmd") or shutil.which("mvn")
DOCKER = shutil.which("docker")


@contextlib.contextmanager
def working_directory(path):
    previous_directory = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous_directory)


def docker_is_available():
    if not DOCKER:
        return False
    try:
        result = subprocess.run(
            [DOCKER, "info"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


@unittest.skipUnless(MAVEN, "Maven no está instalado")
@unittest.skipUnless(docker_is_available(), "Docker no está disponible")
class GeneratedCrudEndToEndTest(unittest.TestCase):
    """Prueba el producto generado como lo haría un consumidor real.

    A diferencia de los tests de plantillas, este test arranca Spring Boot en un
    puerto aleatorio, levanta PostgreSQL 16 con Testcontainers y hace peticiones
    HTTP reales contra el CRUD generado.
    """

    def test_generated_layered_crud_works_end_to_end(self):
        workspace = Path.cwd()
        with tempfile.TemporaryDirectory(
            prefix=".generated-e2e-", dir=workspace
        ) as temporary_directory:
            root = Path(temporary_directory)
            with working_directory(root):
                project_directory = root / generate_project(
                    "Producto",
                    (
                        "id:int, "
                        "nombre:string:not_blank:max=120, "
                        "precio:decimal:required:positive, "
                        "activo:boolean:required"
                    ),
                    "layered",
                )

                self._write_black_box_test(project_directory)
                self._assert_compose_configuration(project_directory)
                self._run_maven_e2e(project_directory, workspace)

    def _write_black_box_test(self, project_directory):
        test_path = (
            project_directory
            / "src"
            / "test"
            / "java"
            / "com"
            / "example"
            / "crud"
            / "e2e"
            / "GeneratedCrudE2ETest.java"
        )
        test_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.write_text(
            textwrap.dedent(
                r"""
                package com.example.crud.e2e;

                import io.restassured.RestAssured;
                import org.junit.jupiter.api.Test;
                import org.springframework.boot.test.context.SpringBootTest;
                import org.springframework.boot.test.web.server.LocalServerPort;
                import org.springframework.test.context.DynamicPropertyRegistry;
                import org.springframework.test.context.DynamicPropertySource;
                import org.testcontainers.containers.PostgreSQLContainer;
                import org.testcontainers.junit.jupiter.Container;
                import org.testcontainers.junit.jupiter.Testcontainers;

                import java.util.UUID;

                import static io.restassured.RestAssured.given;
                import static org.hamcrest.Matchers.equalTo;
                import static org.hamcrest.Matchers.hasItem;

                @Testcontainers
                @SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
                class GeneratedCrudE2ETest {

                    @Container
                    static final PostgreSQLContainer<?> POSTGRES =
                            new PostgreSQLContainer<>("postgres:16-alpine");

                    @LocalServerPort
                    private int port;

                    @DynamicPropertySource
                    static void properties(DynamicPropertyRegistry registry) {
                        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
                        registry.add("spring.datasource.username", POSTGRES::getUsername);
                        registry.add("spring.datasource.password", POSTGRES::getPassword);
                        registry.add("spring.flyway.url", POSTGRES::getJdbcUrl);
                        registry.add("spring.flyway.user", POSTGRES::getUsername);
                        registry.add("spring.flyway.password", POSTGRES::getPassword);
                        registry.add("app.security.user", () -> "e2e-admin");
                        registry.add("app.security.password", () -> "e2e-password");
                        registry.add("app.rate-limit.requests-per-minute", () -> "1000");
                    }

                    @Test
                    void completeCrudLifecycleOverRealHttp() {
                        RestAssured.port = port;

                        given()
                                .when()
                                .get("/api/productos")
                                .then()
                                .statusCode(401);

                        given()
                                .auth().preemptive().basic("e2e-admin", "e2e-password")
                                .header("Idempotency-Key", UUID.randomUUID().toString())
                                .contentType("application/json")
                                .body("{}")
                                .when()
                                .post("/api/productos")
                                .then()
                                .statusCode(400);

                        String createBody =
                                "{\"nombre\":\"Teclado\",\"precio\":49.99,\"activo\":true}";
                        Integer id =
                                given()
                                        .auth().preemptive().basic("e2e-admin", "e2e-password")
                                        .header("Idempotency-Key", UUID.randomUUID().toString())
                                        .contentType("application/json")
                                        .body(createBody)
                                        .when()
                                        .post("/api/productos")
                                        .then()
                                        .statusCode(201)
                                        .body("nombre", equalTo("Teclado"))
                                        .extract()
                                        .jsonPath()
                                        .getInt("id");

                        given()
                                .auth().preemptive().basic("e2e-admin", "e2e-password")
                                .when()
                                .get("/api/productos/{id}", id)
                                .then()
                                .statusCode(200)
                                .body("id", equalTo(id))
                                .body("nombre", equalTo("Teclado"));

                        String updateBody =
                                "{\"nombre\":\"Teclado Pro\",\"precio\":79.99,\"activo\":false}";
                        given()
                                .auth().preemptive().basic("e2e-admin", "e2e-password")
                                .contentType("application/json")
                                .body(updateBody)
                                .when()
                                .put("/api/productos/{id}", id)
                                .then()
                                .statusCode(200)
                                .body("nombre", equalTo("Teclado Pro"))
                                .body("activo", equalTo(false));

                        given()
                                .auth().preemptive().basic("e2e-admin", "e2e-password")
                                .contentType("application/json")
                                .body("{\"nombre\":\"Teclado Pro 2\"}")
                                .when()
                                .patch("/api/productos/{id}", id)
                                .then()
                                .statusCode(200)
                                .body("nombre", equalTo("Teclado Pro 2"));

                        given()
                                .auth().preemptive().basic("e2e-admin", "e2e-password")
                                .when()
                                .get("/api/productos")
                                .then()
                                .statusCode(200)
                                .body("content.id", hasItem(id))
                                .body("content.nombre", hasItem("Teclado Pro 2"));

                        given()
                                .auth().preemptive().basic("e2e-admin", "e2e-password")
                                .when()
                                .delete("/api/productos/{id}", id)
                                .then()
                                .statusCode(204);

                        given()
                                .auth().preemptive().basic("e2e-admin", "e2e-password")
                                .when()
                                .get("/api/productos/{id}", id)
                                .then()
                                .statusCode(404);
                    }
                }
                """
            ).lstrip(),
            encoding="utf-8",
        )

    def _assert_compose_configuration(self, project_directory):
        compose = subprocess.run(
            [DOCKER, "compose", "config"],
            cwd=project_directory,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if compose.returncode != 0:
            self.fail(
                "docker compose config falló para el proyecto generado.\n"
                f"STDOUT:\n{compose.stdout}\nSTDERR:\n{compose.stderr}"
            )

    def _run_maven_e2e(self, project_directory, workspace):
        local_repository = os.environ.get(
            "CRUD_GENERATOR_MAVEN_REPO", str(workspace / ".m2" / "repository")
        )
        command = [
            MAVEN,
            f"-Dmaven.repo.local={local_repository}",
            "verify",
            "-Pcucumber",
            "-Dtest=GeneratedCrudE2ETest,RunCucumberTest",
            "--quiet",
        ]
        result = subprocess.run(
            command,
            cwd=project_directory,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        if result.returncode != 0:
            self.fail(
                f"E2E Maven falló en {project_directory.name}.\n"
                f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )


if __name__ == "__main__":
    unittest.main()
