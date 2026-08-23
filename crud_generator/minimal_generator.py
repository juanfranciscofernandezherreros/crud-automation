"""Generador de la arquitectura 'minimal': un esqueleto Spring Boot + Docker
sin base de datos, sin seguridad y sin observabilidad -- listo para GitOps.

Mismo formato que hello-world-argocd (github.com/juanfranciscofernandezherreros
/hello-world-argocd): un unico endpoint GET que confirma que el contenedor
arranca y responde, pensado como base para desplegar por ArgoCD, no como CRUD.
Por eso ignora 'fields'/'attrs': la entidad solo pone nombre al servicio."""

from .architectures import DEFAULT_BASE_PACKAGE
from .generator import _guard_existing_directory, _make_write_file


def get_minimal_pom_xml(entity_lower):
    artifact_id = f"crud-{entity_lower}-minimal"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.4</version>
        <relativePath/>
    </parent>
    <groupId>com.example</groupId>
    <artifactId>{artifact_id}</artifactId>
    <version>0.0.1-SNAPSHOT</version>
    <name>{artifact_id}</name>
    <description>Esqueleto minimo Spring Boot + Docker, listo para GitOps</description>

    <properties>
        <java.version>21</java.version>
    </properties>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-actuator</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>
"""


def get_minimal_application(base_package, entity_name):
    return f"""package {base_package};

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class {entity_name}Application {{

    public static void main(String[] args) {{
        SpringApplication.run({entity_name}Application.class, args);
    }}
}}
"""


def get_minimal_controller(base_package, entity_name, entity_lower):
    return f"""package {base_package};

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class {entity_name}Controller {{

    @GetMapping("/{entity_lower}")
    public {entity_name}Response hello() {{
        return new {entity_name}Response("Hello from {entity_name}");
    }}

    public record {entity_name}Response(String message) {{
    }}
}}
"""


def get_minimal_controller_test(base_package, entity_name, entity_lower):
    return f"""package {base_package};

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class {entity_name}ControllerTest {{

    @LocalServerPort
    private int port;

    @Autowired
    private TestRestTemplate restTemplate;

    @Test
    void respondeConMensaje() {{
        ResponseEntity<{entity_name}Controller.{entity_name}Response> response =
                restTemplate.getForEntity(
                        "http://localhost:" + port + "/{entity_lower}",
                        {entity_name}Controller.{entity_name}Response.class);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().message()).isEqualTo("Hello from {entity_name}");
    }}
}}
"""


def get_minimal_application_yml(entity_lower):
    return f"""server:
  port: 8080

spring:
  application:
    name: {entity_lower}

management:
  endpoints:
    web:
      exposure:
        include: health,info
  endpoint:
    health:
      probes:
        enabled: true
"""


MINIMAL_DOCKERFILE_TEMPLATE = """FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /build
COPY pom.xml .
RUN mvn -B dependency:go-offline
COPY src ./src
RUN mvn -B -DskipTests package

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /build/target/{jar_name} app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
"""

MINIMAL_DOCKERIGNORE = """target
.git
.idea
*.iml
"""


def get_minimal_readme(entity_name, entity_lower, base_dir):
    return f"""# {base_dir}

Microservicio minimo ({entity_name}), generado con la arquitectura
`minimal` de crud-automation: solo `app/` con un Spring Boot + Docker sin
base de datos, sin seguridad y sin observabilidad -- mismo formato que
[hello-world-argocd](https://github.com/juanfranciscofernandezherreros/hello-world-argocd),
pensado como base para desplegar por GitOps (ver esa guia para el resto
del flujo: clúster kind, ArgoCD, manifiestos).

## Build local

```
mvn -f app/pom.xml clean package
docker build -t {entity_lower}:local app
```

## Verificar

```
curl http://localhost:8080/{entity_lower}
```

Responde `{{"message":"Hello from {entity_name}"}}`.
"""


def generate_minimal_project(entity_name, base_package=None, overwrite=False):
    """Genera el esqueleto minimo para 'entity_name'. A diferencia del resto
    de arquitecturas no recibe 'attrs'/'fields': no hay CRUD que generar,
    solo un nombre de servicio."""
    base_package = base_package or DEFAULT_BASE_PACKAGE
    write_file = _make_write_file(base_package)

    entity_lower = entity_name.lower()
    base_dir = f"crud-{entity_lower}-minimal"
    _guard_existing_directory(base_dir, overwrite)

    app_dir = f"{base_dir}/app"
    package_path = base_package.replace(".", "/")
    java_base = f"{app_dir}/src/main/java/{package_path}"
    test_base = f"{app_dir}/src/test/java/{package_path}"

    write_file(f"{app_dir}/pom.xml", get_minimal_pom_xml(entity_lower))
    write_file(
        f"{app_dir}/Dockerfile",
        MINIMAL_DOCKERFILE_TEMPLATE.format(jar_name=f"crud-{entity_lower}-minimal-0.0.1-SNAPSHOT.jar"),
    )
    write_file(f"{app_dir}/.dockerignore", MINIMAL_DOCKERIGNORE)
    write_file(
        f"{app_dir}/src/main/resources/application.yml",
        get_minimal_application_yml(entity_lower),
    )
    write_file(
        f"{java_base}/{entity_name}Application.java",
        get_minimal_application(base_package, entity_name),
    )
    write_file(
        f"{java_base}/{entity_name}Controller.java",
        get_minimal_controller(base_package, entity_name, entity_lower),
    )
    write_file(
        f"{test_base}/{entity_name}ControllerTest.java",
        get_minimal_controller_test(base_package, entity_name, entity_lower),
    )
    write_file(f"{base_dir}/README.md", get_minimal_readme(entity_name, entity_lower, base_dir))

    return base_dir
