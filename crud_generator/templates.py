"""Plantillas de los archivos del proyecto Spring Boot generado."""

from . import shared_templates
from .parsing import DEFAULT_ENDPOINTS


def get_pom_xml(entity_lower):
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
    <artifactId>crud-{entity_lower}</artifactId>
    <version>0.0.1-SNAPSHOT</version>
    <name>crud-{entity_lower}</name>

    <properties>
        <java.version>21</java.version>
        <org.mapstruct.version>1.5.5.Final</org.mapstruct.version>
        <springdoc.version>2.5.0</springdoc.version>
        <lombok.version>1.18.30</lombok.version>
        <cucumber.version>7.18.1</cucumber.version>
        <allure.version>2.27.0</allure.version>
        <!-- Version reciente explicita: la que trae por defecto Spring Boot 3.2.x
             (1.19.x) negocia mal la version de API con Docker Desktop actual y
             falla con "client version ... too old" al usar Testcontainers. -->
        <testcontainers.version>1.20.4</testcontainers.version>
    </properties>

    <dependencies>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-web</artifactId></dependency>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-data-jpa</artifactId></dependency>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-validation</artifactId></dependency>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-actuator</artifactId></dependency>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-security</artifactId></dependency>
        <dependency><groupId>io.micrometer</groupId><artifactId>micrometer-registry-prometheus</artifactId><scope>runtime</scope></dependency>
        <dependency><groupId>io.micrometer</groupId><artifactId>micrometer-tracing-bridge-otel</artifactId></dependency>
        <dependency><groupId>io.opentelemetry</groupId><artifactId>opentelemetry-exporter-otlp</artifactId></dependency>
        <!-- Envia cada linea de log a Loki (ver logback-spring.xml y docker-compose.yml) -->
        <dependency><groupId>com.github.loki4j</groupId><artifactId>loki-logback-appender</artifactId><version>1.5.2</version><scope>runtime</scope></dependency>

        <!-- Flyway con versión explícita hardcodeada para evitar errores en el POM -->
        <dependency>
            <groupId>org.flywaydb</groupId>
            <artifactId>flyway-core</artifactId>
            <version>10.8.1</version>
        </dependency>
        <dependency>
            <groupId>org.flywaydb</groupId>
            <artifactId>flyway-database-postgresql</artifactId>
            <version>10.8.1</version>
        </dependency>

        <dependency><groupId>org.postgresql</groupId><artifactId>postgresql</artifactId><scope>runtime</scope></dependency>
        <dependency><groupId>org.projectlombok</groupId><artifactId>lombok</artifactId><optional>true</optional></dependency>
        <dependency><groupId>org.mapstruct</groupId><artifactId>mapstruct</artifactId><version>${{org.mapstruct.version}}</version></dependency>
        <dependency><groupId>org.springdoc</groupId><artifactId>springdoc-openapi-starter-webmvc-ui</artifactId><version>${{springdoc.version}}</version></dependency>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-test</artifactId><scope>test</scope></dependency>
        <dependency><groupId>org.springframework.security</groupId><artifactId>spring-security-test</artifactId><scope>test</scope></dependency>
        <dependency><groupId>org.testcontainers</groupId><artifactId>junit-jupiter</artifactId><scope>test</scope></dependency>
        <dependency><groupId>org.testcontainers</groupId><artifactId>postgresql</artifactId><scope>test</scope></dependency>

        <!-- Cucumber (BDD, HTTP real contra la app en un puerto aleatorio) + Allure -->
        <dependency><groupId>io.cucumber</groupId><artifactId>cucumber-java</artifactId><version>${{cucumber.version}}</version><scope>test</scope></dependency>
        <dependency><groupId>io.cucumber</groupId><artifactId>cucumber-junit-platform-engine</artifactId><version>${{cucumber.version}}</version><scope>test</scope></dependency>
        <dependency><groupId>io.cucumber</groupId><artifactId>cucumber-spring</artifactId><version>${{cucumber.version}}</version><scope>test</scope></dependency>
        <dependency><groupId>org.junit.platform</groupId><artifactId>junit-platform-suite</artifactId><scope>test</scope></dependency>
        <dependency><groupId>io.qameta.allure</groupId><artifactId>allure-cucumber7-jvm</artifactId><version>${{allure.version}}</version><scope>test</scope></dependency>
        <dependency><groupId>io.rest-assured</groupId><artifactId>rest-assured</artifactId><scope>test</scope></dependency>
    </dependencies>

    <dependencyManagement>
        <dependencies>
            <dependency>
                <groupId>io.cucumber</groupId>
                <artifactId>cucumber-bom</artifactId>
                <version>${{cucumber.version}}</version>
                <type>pom</type>
                <scope>import</scope>
            </dependency>
            <dependency>
                <groupId>org.testcontainers</groupId>
                <artifactId>testcontainers-bom</artifactId>
                <version>${{testcontainers.version}}</version>
                <type>pom</type>
                <scope>import</scope>
            </dependency>
        </dependencies>
    </dependencyManagement>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
                <configuration>
                    <excludes>
                        <exclude>
                            <groupId>org.projectlombok</groupId>
                            <artifactId>lombok</artifactId>
                        </exclude>
                    </excludes>
                </configuration>
            </plugin>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <configuration>
                    <source>${{java.version}}</source>
                    <target>${{java.version}}</target>
                    <annotationProcessorPaths>
                        <path><groupId>org.projectlombok</groupId><artifactId>lombok</artifactId><version>${{lombok.version}}</version></path>
                        <path><groupId>org.mapstruct</groupId><artifactId>mapstruct-processor</artifactId><version>${{org.mapstruct.version}}</version></path>
                        <path><groupId>org.projectlombok</groupId><artifactId>lombok-mapstruct-binding</artifactId><version>0.2.0</version></path>
                    </annotationProcessorPaths>
                </configuration>
            </plugin>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-surefire-plugin</artifactId>
                <configuration>
                    <!-- RunCucumberTest se excluye de 'mvn test'/'mvn verify' por defecto:
                         necesita Docker funcionando de verdad para Testcontainers (no solo
                         disponible: en Windows con Docker Desktop es habitual que la
                         negociacion de API sobre el named pipe falle aunque 'docker' vaya
                         bien por CLI). Ejecutalo aparte con 'mvn test -Pcucumber', donde
                         Docker sea fiable (CI, Linux, WSL2). -->
                    <excludes>
                        <exclude>**/RunCucumberTest.java</exclude>
                    </excludes>
                    <systemPropertyVariables>
                        <allure.results.directory>${{project.build.directory}}/allure-results</allure.results.directory>
                    </systemPropertyVariables>
                </configuration>
            </plugin>
            <plugin>
                <groupId>io.qameta.allure</groupId>
                <artifactId>allure-maven</artifactId>
                <version>2.12.0</version>
                <configuration>
                    <reportVersion>${{allure.version}}</reportVersion>
                    <resultsDirectory>${{project.build.directory}}/allure-results</resultsDirectory>
                </configuration>
            </plugin>
        </plugins>
    </build>

    <profiles>
        <profile>
            <!-- 'mvn test -Pcucumber' o 'mvn verify -Pcucumber': ejecuta ademas los
                 escenarios de RunCucumberTest (ver exclude de arriba). -->
            <id>cucumber</id>
            <build>
                <plugins>
                    <plugin>
                        <groupId>org.apache.maven.plugins</groupId>
                        <artifactId>maven-surefire-plugin</artifactId>
                        <configuration>
                            <excludes combine.self="override"/>
                        </configuration>
                    </plugin>
                </plugins>
            </build>
        </profile>
    </profiles>
</project>
"""

DOCKERFILE = """FROM maven:3.9.9-eclipse-temurin-21-alpine AS builder
WORKDIR /app
COPY . .
RUN mvn clean package -DskipTests

FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY --from=builder /app/target/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
"""

def get_docker_compose(entity_lower):
    return f"""version: '3.8'
services:
  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      - SPRING_DATASOURCE_URL=jdbc:postgresql://db:5432/{entity_lower}_db
      - SPRING_DATASOURCE_USERNAME=${{POSTGRES_USER:?Set POSTGRES_USER}}
      - SPRING_DATASOURCE_PASSWORD=${{POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD}}
      - SPRING_FLYWAY_URL=jdbc:postgresql://db:5432/{entity_lower}_db
      - SPRING_FLYWAY_USER=${{POSTGRES_USER:?Set POSTGRES_USER}}
      - SPRING_FLYWAY_PASSWORD=${{POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD}}
      - APP_SECURITY_USER=${{APP_SECURITY_USER:?Set APP_SECURITY_USER}}
      - APP_SECURITY_PASSWORD=${{APP_SECURITY_PASSWORD:?Set APP_SECURITY_PASSWORD}}
      - OTEL_EXPORTER_OTLP_ENDPOINT=${{OTEL_EXPORTER_OTLP_ENDPOINT:-http://host.docker.internal:4318/v1/traces}}
      - LOKI_URL=${{LOKI_URL:-http://loki:3100}}
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB={entity_lower}_db
      - POSTGRES_USER=${{POSTGRES_USER:?Set POSTGRES_USER}}
      - POSTGRES_PASSWORD=${{POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD}}
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${{POSTGRES_USER}} -d $${{POSTGRES_DB}}"]
      interval: 5s
      timeout: 5s
      retries: 5

  prometheus:
    image: prom/prometheus:v2.54.1
    volumes:
      - ./observability/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    ports:
      - "9090:9090"
    depends_on:
      - app

  loki:
    image: grafana/loki:2.9.8
    command: ["-config.file=/etc/loki/loki-config.yml"]
    volumes:
      - ./observability/loki-config.yml:/etc/loki/loki-config.yml:ro
    ports:
      - "3100:3100"

  grafana:
    image: grafana/grafana:11.1.4
    environment:
      - GF_SECURITY_ADMIN_USER=${{APP_SECURITY_USER:?Set APP_SECURITY_USER}}
      - GF_SECURITY_ADMIN_PASSWORD=${{APP_SECURITY_PASSWORD:?Set APP_SECURITY_PASSWORD}}
      - GF_AUTH_ANONYMOUS_ENABLED=false
    volumes:
      - ./observability/grafana/provisioning:/etc/grafana/provisioning:ro
      - ./observability/grafana/dashboards:/var/lib/grafana/dashboards:ro
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
      - loki
"""


def get_prometheus_config(entity_lower):
    return f"""global:
  scrape_interval: 10s

scrape_configs:
  - job_name: "{entity_lower}-service"
    metrics_path: /actuator/prometheus
    static_configs:
      - targets: ["app:8080"]
"""


def get_loki_config():
    return """auth_enabled: false

server:
  http_listen_port: 3100

common:
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2024-01-01
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h
"""


def get_grafana_datasources():
    return """apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
"""


def get_grafana_dashboard_provider():
    return """apiVersion: 1

providers:
  - name: default
    orgId: 1
    folder: ""
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30
    options:
      path: /var/lib/grafana/dashboards
"""


def get_grafana_business_dashboard(entity_name, entity_lower):
    """Dashboard con metricas de negocio/operacion del endpoint de listado de la
    entidad: throughput, tasa de error, latencia p95 y logs recientes desde Loki."""
    uid = f"{entity_lower}-overview"
    return f"""{{
  "uid": "{uid}",
  "title": "{entity_name} - Vision general",
  "timezone": "browser",
  "schemaVersion": 39,
  "version": 1,
  "refresh": "10s",
  "time": {{"from": "now-1h", "to": "now"}},
  "panels": [
    {{
      "id": 1,
      "title": "Peticiones/seg a /api/{entity_lower}s",
      "type": "timeseries",
      "gridPos": {{"h": 8, "w": 12, "x": 0, "y": 0}},
      "datasource": {{"type": "prometheus", "uid": "Prometheus"}},
      "targets": [
        {{
          "expr": "sum(rate(http_server_requests_seconds_count{{uri=~\\"/api/{entity_lower}s.*\\"}}[1m]))",
          "legendFormat": "req/s"
        }}
      ]
    }},
    {{
      "id": 2,
      "title": "Tasa de error 5xx",
      "type": "timeseries",
      "gridPos": {{"h": 8, "w": 12, "x": 12, "y": 0}},
      "datasource": {{"type": "prometheus", "uid": "Prometheus"}},
      "targets": [
        {{
          "expr": "sum(rate(http_server_requests_seconds_count{{uri=~\\"/api/{entity_lower}s.*\\",status=~\\"5..\\"}}[1m]))",
          "legendFormat": "errores/s"
        }}
      ]
    }},
    {{
      "id": 3,
      "title": "Latencia p95",
      "type": "timeseries",
      "gridPos": {{"h": 8, "w": 12, "x": 0, "y": 8}},
      "datasource": {{"type": "prometheus", "uid": "Prometheus"}},
      "targets": [
        {{
          "expr": "histogram_quantile(0.95, sum(rate(http_server_requests_seconds_bucket{{uri=~\\"/api/{entity_lower}s.*\\"}}[5m])) by (le))",
          "legendFormat": "p95 (s)"
        }}
      ]
    }},
    {{
      "id": 4,
      "title": "Logs recientes",
      "type": "logs",
      "gridPos": {{"h": 8, "w": 12, "x": 12, "y": 8}},
      "datasource": {{"type": "loki", "uid": "Loki"}},
      "targets": [
        {{"expr": "{{{{service_name=\\"{entity_lower}-service\\"}}}}"}}
      ]
    }}
  ]
}}
"""

_ENV_DEFAULTS = """POSTGRES_USER=app_user
POSTGRES_PASSWORD=cambiar-en-produccion
APP_SECURITY_USER=admin
APP_SECURITY_PASSWORD=otra-clave-segura
"""


def get_env_example():
    return """# Copia este fichero a ".env" (mismo directorio que docker-compose.yml) y
# ajusta los valores antes de ejecutar "docker compose up". docker compose
# carga ".env" automaticamente; sin el, "docker compose up" falla porque
# las cuatro variables son obligatorias en docker-compose.yml.
""" + _ENV_DEFAULTS


def get_env_default():
    """Fichero ".env" lista para usar en desarrollo local, con las mismas
    credenciales de ejemplo que ".env.example", para que "docker compose up"
    funcione nada mas generar el proyecto sin un paso manual de copia. Nunca
    se versiona: GITIGNORE excluye ".env"."""
    return (
        "# Generado automaticamente para desarrollo local. Cambia estos valores\n"
        "# antes de desplegar en cualquier entorno compartido.\n"
    ) + _ENV_DEFAULTS


GITIGNORE = """target/
.env
"""


def get_github_actions_workflow(entity_lower):
    """CI minima: compila y ejecuta 'mvn verify' (incluye los tests de
    Testcontainers, para los que el runner de GitHub Actions ya trae Docker)
    en cada push/PR. Cachea el repositorio local de Maven entre ejecuciones."""
    return f"""name: CI

on:
  push:
    branches: ["main", "master"]
  pull_request:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configurar JDK 21
        uses: actions/setup-java@v4
        with:
          java-version: "21"
          distribution: "temurin"
          cache: maven

      - name: mvn verify (compila, unit tests y tests de Testcontainers)
        run: mvn --batch-mode --no-transfer-progress verify

      - name: Cucumber (perfil 'cucumber', necesita Docker real para Testcontainers)
        run: mvn --batch-mode --no-transfer-progress test -Pcucumber -Dtest=RunCucumberTest

      - name: Publicar resultados de test
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: crud-{entity_lower}-test-results
          path: |
            target/surefire-reports/
            target/failsafe-reports/
            target/allure-results/
          if-no-files-found: ignore
"""


def get_logback_spring_xml(entity_lower):
    """Ademas de la consola, envia cada linea a Loki con la label
    'service_name={entity_lower}-service' que usa el dashboard de Grafana
    generado en observability/grafana/dashboards/."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <include resource="org/springframework/boot/logging/logback/defaults.xml"/>
    <property name="CONSOLE_LOG_PATTERN"
              value="%d{{yyyy-MM-dd HH:mm:ss.SSS}} %-5level [%thread] traceId=%X{{traceId:-}} spanId=%X{{spanId:-}} %logger{{36}} - %msg%n"/>

    <springProperty scope="context" name="lokiUrl" source="LOKI_URL" defaultValue="http://localhost:3100"/>

    <appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
        <encoder><pattern>${{CONSOLE_LOG_PATTERN}}</pattern></encoder>
    </appender>

    <appender name="LOKI" class="com.github.loki4j.logback.Loki4jAppender">
        <http>
            <url>${{lokiUrl}}/loki/api/v1/push</url>
        </http>
        <format>
            <label>
                <pattern>service_name={entity_lower}-service</pattern>
            </label>
            <message>
                <pattern>${{CONSOLE_LOG_PATTERN}}</pattern>
            </message>
        </format>
    </appender>

    <root level="INFO">
        <appender-ref ref="CONSOLE"/>
        <appender-ref ref="LOKI"/>
    </root>
</configuration>
"""


def get_application_yml(entity_lower):
    return f"""server:
  port: 8080
spring:
  application:
    name: {entity_lower}-service
  datasource:
    url: ${{SPRING_DATASOURCE_URL:jdbc:postgresql://localhost:5432/{entity_lower}_db}}
    username: ${{SPRING_DATASOURCE_USERNAME}}
    password: ${{SPRING_DATASOURCE_PASSWORD}}
    driver-class-name: org.postgresql.Driver
  jpa:
    hibernate:
      ddl-auto: validate
    show-sql: ${{JPA_SHOW_SQL:false}}
    properties:
      hibernate:
        format_sql: true
        dialect: org.hibernate.dialect.PostgreSQLDialect
  flyway:
    enabled: true
    baseline-on-migrate: true
  data:
    web:
      pageable:
        default-page-size: 20
        max-page-size: 100
management:
  endpoints:
    web:
      exposure:
        include: health, info, prometheus
  endpoint:
    health:
      show-details: when_authorized
  tracing:
    sampling:
      probability: ${{TRACING_SAMPLING_PROBABILITY:0.1}}
  otlp:
    tracing:
      endpoint: ${{OTEL_EXPORTER_OTLP_ENDPOINT:http://localhost:4318/v1/traces}}
app:
  security:
    user: ${{APP_SECURITY_USER}}
    password: ${{APP_SECURITY_PASSWORD}}
  rate-limit:
    requests-per-minute: ${{RATE_LIMIT_PER_MINUTE:120}}
logging:
  pattern:
    level: "%5p [traceId=%X{{traceId:-}},spanId=%X{{spanId:-}}]"
springdoc:
  api-docs:
    path: /v3/api-docs
  swagger-ui:
    path: /swagger-ui.html
"""

def get_sql_migration(entity_lower, sql_fields, sql_indexes=""):
    indexes = f"\n{sql_indexes}\n" if sql_indexes else ""
    return f"""CREATE TABLE {entity_lower}s (
{sql_fields}
);
{indexes}
CREATE TABLE IF NOT EXISTS idempotency_keys (
    idempotency_key VARCHAR(128) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id INT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (idempotency_key, resource_type)
);
"""

def get_entity(
    entity_name,
    entity_lower,
    entity_fields,
    unique_constraints_annotation="",
    dynamic_insert=False,
    include_all_args_builder=True,
    has_inverse_relations=False,
):
    return shared_templates.render_jpa_entity_class(
        "com.example.crud.entity",
        entity_name,
        entity_lower,
        entity_fields,
        unique_constraints_annotation,
        dynamic_insert,
        include_all_args_builder,
        "",
        has_inverse_relations,
    )

def get_enum_class(enum_class, values, package="com.example.crud.entity"):
    constants = ", ".join(values)
    return f"""package {package};

public enum {enum_class} {{
    {constants}
}}
"""


def get_dto(class_name, dto_fields, enum_import_lines=""):
    return shared_templates.render_dto_class(
        "com.example.crud.dto", class_name, dto_fields, enum_import_lines
    )

def get_mapper(entity_name, reference_attrs=None):
    """reference_attrs: atributos 'reference' de la entidad. MapStruct no puede
    convertir el Integer '{campo}Id' del DTO en la entidad relacionada (eso exige
    una consulta a su repositorio), asi que esos campos se ignoran aqui y los
    resuelve {entity_name}ServiceImpl (ver get_service_impl)."""
    reference_attrs = reference_attrs or []
    ignore_lines = "\n".join(
        f'    @Mapping(target = "{attr["camel_name"]}", ignore = true)'
        for attr in reference_attrs
    )
    ignore_block = f"{ignore_lines}\n" if ignore_lines else ""

    suffix = shared_templates.capitalize_first

    response_lines = "\n".join(
        f'    @Mapping(target = "{attr["camel_name"]}Id", '
        f'expression = "java(entity.get{suffix(attr["camel_name"])}() != null ? '
        f'entity.get{suffix(attr["camel_name"])}().getId() : null)")'
        for attr in reference_attrs
    )
    response_block = f"{response_lines}\n" if response_lines else ""
    mapping_import = "\nimport org.mapstruct.Mapping;" if reference_attrs else ""
    return f"""package com.example.crud.mapper;

import com.example.crud.dto.*;
import com.example.crud.entity.{entity_name};
import org.mapstruct.BeanMapping;
import org.mapstruct.Mapper;{mapping_import}
import org.mapstruct.MappingTarget;
import org.mapstruct.NullValuePropertyMappingStrategy;

@Mapper(componentModel = "spring")
public interface {entity_name}Mapper {{
{ignore_block}    {entity_name} toEntity({entity_name}CreateDTO dto);
{ignore_block}    {entity_name} toEntity({entity_name}UpdateDTO dto);
{response_block}    {entity_name}ResponseDTO toDto({entity_name} entity);

{ignore_block}    @BeanMapping(nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
    void updateEntityFromPatchDto({entity_name}PatchDTO dto, @MappingTarget {entity_name} entity);

{ignore_block}    void updateEntityFromUpdateDto({entity_name}UpdateDTO dto, @MappingTarget {entity_name} entity);
}}
"""

def get_repository(entity_name):
    return f"""package com.example.crud.repository;

import com.example.crud.entity.{entity_name};
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.stereotype.Repository;

@Repository
public interface {entity_name}Repository
        extends JpaRepository<{entity_name}, Integer>, JpaSpecificationExecutor<{entity_name}> {{
}}
"""

def get_specification(entity_name, filter_cases):
    return f"""package com.example.crud.specification;

import com.example.crud.entity.{entity_name};
import org.springframework.data.jpa.domain.Specification;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.Map;

public final class {entity_name}Specifications {{

    private {entity_name}Specifications() {{
    }}

    public static Specification<{entity_name}> fromFilters(Map<String, String> filters) {{
        Specification<{entity_name}> spec = Specification.where(null);
        for (Map.Entry<String, String> entry : filters.entrySet()) {{
            String value = entry.getValue();
            if (value == null || value.isBlank()) {{
                continue;
            }}
            switch (entry.getKey()) {{
{filter_cases}
                default -> {{ }}
            }}
        }}
        return spec;
    }}
}}
"""

def get_service(entity_name):
    return f"""package com.example.crud.service;

import com.example.crud.dto.*;
import com.example.crud.entity.{entity_name};
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.domain.Specification;

public interface {entity_name}Service {{
    {entity_name}ResponseDTO create({entity_name}CreateDTO createDTO);
    Page<{entity_name}ResponseDTO> findAll(Pageable pageable, Specification<{entity_name}> spec);
    {entity_name}ResponseDTO findById(Integer id);
    {entity_name}ResponseDTO update(Integer id, {entity_name}UpdateDTO updateDTO);
    {entity_name}ResponseDTO patch(Integer id, {entity_name}PatchDTO patchDTO);
    void delete(Integer id);
}}
"""

def get_service_impl(entity_name, reference_attrs=None):
    """reference_attrs: atributos 'reference' de la entidad (@ManyToOne). El
    mapper los ignora (ver get_mapper), asi que aqui se resuelven a mano contra
    el repositorio de la entidad referenciada antes de guardar."""
    reference_attrs = reference_attrs or []
    suffix = shared_templates.capitalize_first

    reference_imports_block = shared_templates.render_reference_imports_block(
        reference_attrs, "com.example.crud.entity", "com.example.crud.repository"
    )
    reference_fields_block = shared_templates.render_reference_fields_block(reference_attrs)

    create_resolutions = shared_templates.render_reference_resolution_calls(
        reference_attrs, "entity", "createDTO"
    )
    create_resolutions_block = f"\n{create_resolutions}" if create_resolutions else ""

    update_resolutions = shared_templates.render_reference_resolution_calls(
        reference_attrs, "entity", "updateDTO"
    )
    update_resolutions_block = f"\n{update_resolutions}" if update_resolutions else ""

    patch_resolutions = "\n".join(
        f"        if (patchDTO.get{suffix(attr['camel_name'])}Id() != null) {{\n"
        f"            entity.set{suffix(attr['camel_name'])}(resolve{suffix(attr['camel_name'])}(patchDTO.get{suffix(attr['camel_name'])}Id()));\n"
        "        }"
        for attr in reference_attrs
    )
    patch_resolutions_block = f"\n{patch_resolutions}" if patch_resolutions else ""

    resolvers_block = shared_templates.render_reference_resolvers_block(reference_attrs)

    return f"""package com.example.crud.service.impl;

import com.example.crud.dto.*;
import com.example.crud.entity.{entity_name};
import com.example.crud.exception.ResourceNotFoundException;
import com.example.crud.mapper.{entity_name}Mapper;
import com.example.crud.repository.{entity_name}Repository;
{reference_imports_block}import com.example.crud.service.{entity_name}Service;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class {entity_name}ServiceImpl implements {entity_name}Service {{

    private final {entity_name}Repository repository;
    private final {entity_name}Mapper mapper;{reference_fields_block}

    @Override
    @Transactional
    public {entity_name}ResponseDTO create({entity_name}CreateDTO createDTO) {{
        {entity_name} entity = mapper.toEntity(createDTO);{create_resolutions_block}
        return mapper.toDto(repository.save(entity));
    }}

    @Override
    @Transactional(readOnly = true)
    public Page<{entity_name}ResponseDTO> findAll(Pageable pageable, Specification<{entity_name}> spec) {{
        return repository.findAll(spec, pageable).map(mapper::toDto);
    }}

    @Override
    @Transactional(readOnly = true)
    public {entity_name}ResponseDTO findById(Integer id) {{
        return mapper.toDto(getEntity(id));
    }}

    @Override
    @Transactional
    public {entity_name}ResponseDTO update(Integer id, {entity_name}UpdateDTO updateDTO) {{
        {entity_name} entity = getEntity(id);
        mapper.updateEntityFromUpdateDto(updateDTO, entity);{update_resolutions_block}
        return mapper.toDto(repository.save(entity));
    }}

    @Override
    @Transactional
    public {entity_name}ResponseDTO patch(Integer id, {entity_name}PatchDTO patchDTO) {{
        {entity_name} entity = getEntity(id);
        mapper.updateEntityFromPatchDto(patchDTO, entity);{patch_resolutions_block}
        return mapper.toDto(repository.save(entity));
    }}

    @Override
    @Transactional
    public void delete(Integer id) {{
        repository.delete(getEntity(id));
    }}

    private {entity_name} getEntity(Integer id) {{
        return repository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("{entity_name} no encontrado con ID: " + id));
    }}{resolvers_block}
}}
"""

def get_controller(entity_name, entity_lower, endpoints=None):
    endpoints = set(endpoints) if endpoints else set(DEFAULT_ENDPOINTS)

    methods = []
    if "create" in endpoints:
        methods.append(f"""
    @PostMapping
    @Operation(summary = "Crear {entity_lower}")
    public ResponseEntity<{entity_name}ResponseDTO> create(
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @Valid @RequestBody {entity_name}CreateDTO dto) {{
        {entity_name}ResponseDTO created = idempotencyService.execute(
                idempotencyKey,
                "{entity_name}",
                () -> service.create(dto),
                service::findById,
                value -> value.getId());
        URI location = ServletUriComponentsBuilder.fromCurrentRequest().path("/{{id}}").buildAndExpand(created.getId()).toUri();
        return ResponseEntity.created(location).body(created);
    }}""")
    if "list" in endpoints:
        methods.append(f"""
    @GetMapping
    @Operation(summary = "Listar {entity_lower}s",
            description = "Admite filtros por igualdad usando cualquier campo de la entidad como query param")
    public ResponseEntity<Page<{entity_name}ResponseDTO>> findAll(
            Pageable pageable, @RequestParam Map<String, String> filters) {{
        return ResponseEntity.ok(service.findAll(pageable, {entity_name}Specifications.fromFilters(filters)));
    }}""")
    if "get" in endpoints:
        methods.append(f"""
    @GetMapping("/{{id}}")
    @Operation(summary = "Obtener por ID")
    public ResponseEntity<{entity_name}ResponseDTO> findById(@PathVariable Integer id) {{
        return ResponseEntity.ok(service.findById(id));
    }}""")
    if "update" in endpoints:
        methods.append(f"""
    @PutMapping("/{{id}}")
    @Operation(summary = "Actualización completa")
    public ResponseEntity<{entity_name}ResponseDTO> update(@PathVariable Integer id, @Valid @RequestBody {entity_name}UpdateDTO dto) {{
        return ResponseEntity.ok(service.update(id, dto));
    }}""")
    if "patch" in endpoints:
        methods.append(f"""
    @PatchMapping("/{{id}}")
    @Operation(summary = "Actualización parcial")
    public ResponseEntity<{entity_name}ResponseDTO> patch(@PathVariable Integer id, @Valid @RequestBody {entity_name}PatchDTO dto) {{
        return ResponseEntity.ok(service.patch(id, dto));
    }}""")
    if "delete" in endpoints:
        methods.append(f"""
    @DeleteMapping("/{{id}}")
    @Operation(summary = "Eliminar {entity_lower}")
    public ResponseEntity<Void> delete(@PathVariable Integer id) {{
        service.delete(id);
        return ResponseEntity.noContent().build();
    }}""")

    needs_idempotency = "create" in endpoints
    needs_valid = bool(endpoints & {"create", "update", "patch"})
    needs_page = "list" in endpoints
    needs_uri = "create" in endpoints
    needs_map = "list" in endpoints
    needs_specification = "list" in endpoints

    imports = ["import com.example.crud.dto.*;"]
    if needs_idempotency:
        imports.append("import com.example.crud.configuration.IdempotencyService;")
    imports.append(f"import com.example.crud.service.{entity_name}Service;")
    if needs_specification:
        imports.append(f"import com.example.crud.specification.{entity_name}Specifications;")
    imports.append("import io.swagger.v3.oas.annotations.Operation;")
    imports.append("import io.swagger.v3.oas.annotations.tags.Tag;")
    if needs_valid:
        imports.append("import jakarta.validation.Valid;")
    imports.append("import lombok.RequiredArgsConstructor;")
    if needs_page:
        imports.append("import org.springframework.data.domain.Page;")
        imports.append("import org.springframework.data.domain.Pageable;")
    imports.append("import org.springframework.http.ResponseEntity;")
    imports.append("import org.springframework.web.bind.annotation.*;")
    if needs_uri:
        imports.append("import org.springframework.web.servlet.support.ServletUriComponentsBuilder;")
        imports.append("import java.net.URI;")
    if needs_map:
        imports.append("import java.util.Map;")

    fields = [f"    private final {entity_name}Service service;"]
    if needs_idempotency:
        fields.append("    private final IdempotencyService idempotencyService;")

    imports_block = "\n".join(imports)
    fields_block = "\n".join(fields)
    methods_block = "\n".join(methods)

    return f"""package com.example.crud.controller;

{imports_block}

@RestController
@RequestMapping("/api/{entity_lower}s")
@RequiredArgsConstructor
@Tag(name = "{entity_name}", description = "API CRUD para {entity_name}")
public class {entity_name}Controller {{

{fields_block}
{methods_block}
}}
"""

APP_MAIN = """package com.example.crud;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class CrudApplication {
    public static void main(String[] args) {
        SpringApplication.run(CrudApplication.class, args);
    }
}
"""

AUDITING_CONFIG = """package com.example.crud.configuration;

import org.springframework.context.annotation.Configuration;
import org.springframework.data.jpa.repository.config.EnableJpaAuditing;

@Configuration
@EnableJpaAuditing
public class JpaAuditingConfiguration {
}
"""

SECURITY_CONFIG = """package com.example.crud.configuration;

import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.security.config.http.SessionCreationPolicy;

@Configuration
@RequiredArgsConstructor
public class SecurityConfiguration {
    private final RateLimitFilter rateLimitFilter;

    @Bean
    SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        return http
                .csrf(csrf -> csrf.disable())
                .sessionManagement(session -> session
                        .sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers("/actuator/health", "/v3/api-docs/**", "/swagger-ui/**").permitAll()
                        .requestMatchers("/actuator/**").hasRole("ADMIN")
                        .requestMatchers(org.springframework.http.HttpMethod.GET, "/api/**").hasAnyRole("USER", "ADMIN")
                        .requestMatchers("/api/**").hasRole("ADMIN")
                        .anyRequest().authenticated())
                .httpBasic(Customizer.withDefaults())
                .addFilterBefore(rateLimitFilter, UsernamePasswordAuthenticationFilter.class)
                .build();
    }

    @Bean
    PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    UserDetailsService userDetailsService(
            @Value("${app.security.user}") String username,
            @Value("${app.security.password}") String password,
            PasswordEncoder encoder) {
        return new InMemoryUserDetailsManager(User.withUsername(username)
                .password(encoder.encode(password)).roles("USER", "ADMIN").build());
    }
}
"""

RATE_LIMIT_FILTER = """package com.example.crud.configuration;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import java.io.IOException;
import java.time.Instant;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class RateLimitFilter extends OncePerRequestFilter {
    private final ConcurrentHashMap<String, Window> windows = new ConcurrentHashMap<>();
    private final int limit;

    public RateLimitFilter(@Value("${app.rate-limit.requests-per-minute:120}") int limit) {
        this.limit = limit;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
            FilterChain chain) throws ServletException, IOException {
        long minute = Instant.now().getEpochSecond() / 60;
        String key = request.getRemoteAddr();
        Window window = windows.compute(key, (ignored, current) ->
                current == null || current.minute != minute ? new Window(minute) : current);
        if (!window.allow(limit)) {
            response.setStatus(HttpStatus.TOO_MANY_REQUESTS.value());
            response.setContentType("application/json");
            response.getWriter().write("{\\\"message\\\":\\\"Rate limit exceeded\\\"}");
            return;
        }
        chain.doFilter(request, response);
    }

    private static final class Window {
        private final long minute;
        private int requests;
        private Window(long minute) { this.minute = minute; }
        private synchronized boolean allow(int limit) { return ++requests <= limit; }
    }
}
"""

IDEMPOTENCY_SERVICE = """package com.example.crud.configuration;

import lombok.RequiredArgsConstructor;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;
import java.util.function.Function;
import java.util.function.Supplier;
import java.util.function.ToIntFunction;

@Component
@RequiredArgsConstructor
public class IdempotencyService {
    private final JdbcTemplate jdbcTemplate;

    @Transactional
    public <T> T execute(String key, String resourceType, Supplier<T> creator,
            Function<Integer, T> loader, ToIntFunction<T> idExtractor) {
        if (key == null || key.isBlank() || key.length() > 128) {
            throw new IllegalArgumentException("Idempotency-Key debe tener entre 1 y 128 caracteres");
        }
        jdbcTemplate.query(
                "SELECT pg_advisory_xact_lock(hashtext(?))",
                rs -> null,
                resourceType + ":" + key);
        List<Integer> existing = jdbcTemplate.query(
                "SELECT resource_id FROM idempotency_keys " +
                        "WHERE idempotency_key=? AND resource_type=?",
                (rs, row) -> rs.getInt(1), key, resourceType);
        if (!existing.isEmpty()) {
            return loader.apply(existing.get(0));
        }
        T created = creator.get();
        jdbcTemplate.update(
                "INSERT INTO idempotency_keys " +
                        "(idempotency_key, resource_type, resource_id) VALUES (?, ?, ?)",
                key, resourceType, idExtractor.applyAsInt(created));
        return created;
    }
}
"""

def get_exception_handler():
    return shared_templates.render_global_exception_handler("com.example.crud.exception")

EXCEPTION_CLASS = """package com.example.crud.exception;
public class ResourceNotFoundException extends RuntimeException {
    public ResourceNotFoundException(String message) { super(message); }
}
"""

def get_service_test(entity_name):
    return f"""package com.example.crud.service;

import com.example.crud.dto.{entity_name}CreateDTO;
import com.example.crud.dto.{entity_name}ResponseDTO;
import com.example.crud.entity.{entity_name};
import com.example.crud.exception.ResourceNotFoundException;
import com.example.crud.mapper.{entity_name}Mapper;
import com.example.crud.repository.{entity_name}Repository;
import com.example.crud.service.impl.{entity_name}ServiceImpl;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class {entity_name}ServiceTest {{

    @Mock
    private {entity_name}Repository repository;

    @Mock
    private {entity_name}Mapper mapper;

    @InjectMocks
    private {entity_name}ServiceImpl service;

    private {entity_name} entity;
    private {entity_name}ResponseDTO responseDTO;

    @BeforeEach
    void setUp() {{
        entity = new {entity_name}();
        responseDTO = new {entity_name}ResponseDTO();
    }}

    @Test
    void create_ReturnsResponseDTO() {{
        {entity_name}CreateDTO createDTO = new {entity_name}CreateDTO();

        when(mapper.toEntity(any({entity_name}CreateDTO.class))).thenReturn(entity);
        when(repository.save(any({entity_name}.class))).thenReturn(entity);
        when(mapper.toDto(any({entity_name}.class))).thenReturn(responseDTO);

        {entity_name}ResponseDTO result = service.create(createDTO);

        assertNotNull(result);
        verify(repository).save(any({entity_name}.class));
    }}

    @Test
    void findById_ExistingId_ReturnsResponseDTO() {{
        when(repository.findById(1)).thenReturn(Optional.of(entity));
        when(mapper.toDto(entity)).thenReturn(responseDTO);

        {entity_name}ResponseDTO result = service.findById(1);

        assertNotNull(result);
    }}

    @Test
    void findById_NonExistingId_ThrowsException() {{
        when(repository.findById(99)).thenReturn(Optional.empty());

        assertThrows(ResourceNotFoundException.class, () -> service.findById(99));
    }}
}}
"""

def get_controller_test(
    entity_name,
    entity_lower,
    create_assignments,
    has_required_fields,
    invalid_assignments,
    endpoints=None,
    enum_import_lines="",
):
    endpoints = set(endpoints) if endpoints else set(DEFAULT_ENDPOINTS)

    tests = []
    if "create" in endpoints:
        invalid_test = ""
        if has_required_fields:
            invalid_test = f"""
    @Test
    void create_MissingRequiredInput_Returns400() throws Exception {{
        {entity_name}CreateDTO createDTO = new {entity_name}CreateDTO();

        mockMvc.perform(post("/api/{entity_lower}s").with(csrf())
                .header("Idempotency-Key", "test-key")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(createDTO)))
                .andExpect(status().isBadRequest());

        Mockito.verifyNoInteractions(service);
    }}
"""

        constraint_test = ""
        if invalid_assignments:
            constraint_test = f"""
    @Test
    void create_InvalidValue_Returns400() throws Exception {{
        {entity_name}CreateDTO createDTO = new {entity_name}CreateDTO();
{invalid_assignments}

        mockMvc.perform(post("/api/{entity_lower}s").with(csrf())
                .header("Idempotency-Key", "test-key")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(createDTO)))
                .andExpect(status().isBadRequest());

        Mockito.verifyNoInteractions(service);
    }}
"""
        tests.append(f"""
    @Test
    void create_ValidInput_Returns201() throws Exception {{
        {entity_name}CreateDTO createDTO = new {entity_name}CreateDTO();
{create_assignments}
        {entity_name}ResponseDTO responseDTO = new {entity_name}ResponseDTO();
        responseDTO.setId(1);

        Mockito.when(idempotencyService.execute(any(), any(), any(), any(), any()))
                .thenReturn(responseDTO);

        mockMvc.perform(post("/api/{entity_lower}s").with(csrf())
                .header("Idempotency-Key", "test-key")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(createDTO)))
                .andExpect(status().isCreated())
                .andExpect(header().string("Location", "http://localhost/api/{entity_lower}s/1"));
    }}
{invalid_test}{constraint_test}""")
    if "list" in endpoints:
        tests.append(f"""
    @Test
    void findAll_WithFilterQueryParam_Returns200() throws Exception {{
        Mockito.when(service.findAll(any(), any())).thenReturn(new PageImpl<>(List.of()));

        mockMvc.perform(get("/api/{entity_lower}s?page=0&size=5&estadoInventado=cualquier-valor"))
                .andExpect(status().isOk());
    }}""")
    if "patch" in endpoints:
        tests.append(f"""
    @Test
    void patch_EmptyInput_Returns200() throws Exception {{
        {entity_name}ResponseDTO responseDTO = new {entity_name}ResponseDTO();
        Mockito.when(service.patch(Mockito.eq(1), any({entity_name}PatchDTO.class)))
                .thenReturn(responseDTO);

        mockMvc.perform(patch("/api/{entity_lower}s/1").with(csrf())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{{}}"))
                .andExpect(status().isOk());
    }}""")
    if "get" in endpoints:
        tests.append(f"""
    @Test
    void findById_ExistingId_Returns200() throws Exception {{
        {entity_name}ResponseDTO responseDTO = new {entity_name}ResponseDTO();

        Mockito.when(service.findById(1)).thenReturn(responseDTO);

        mockMvc.perform(get("/api/{entity_lower}s/1")
                .contentType(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }}""")

    needs_idempotency = "create" in endpoints
    needs_patch_dto = "patch" in endpoints
    needs_page = "list" in endpoints
    needs_get = bool({"list", "get"} & endpoints)

    imports = []
    if enum_import_lines:
        imports.append(enum_import_lines)
    if needs_idempotency:
        imports.append(f"import com.example.crud.dto.{entity_name}CreateDTO;")
    if needs_patch_dto:
        imports.append(f"import com.example.crud.dto.{entity_name}PatchDTO;")
    imports.append(f"import com.example.crud.dto.{entity_name}ResponseDTO;")
    if needs_idempotency:
        imports.append("import com.example.crud.configuration.IdempotencyService;")
    imports.append(f"import com.example.crud.service.{entity_name}Service;")
    imports.append("import com.fasterxml.jackson.databind.ObjectMapper;")
    imports.append("import org.junit.jupiter.api.Test;")
    imports.append("import org.mockito.Mockito;")
    imports.append("import org.springframework.beans.factory.annotation.Autowired;")
    imports.append("import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;")
    imports.append("import org.springframework.boot.test.mock.mockito.MockBean;")
    imports.append("import org.springframework.http.MediaType;")
    imports.append("import org.springframework.test.web.servlet.MockMvc;")
    imports.append("import org.springframework.security.test.context.support.WithMockUser;")
    imports.append("")
    imports.append("import java.time.LocalDate;")
    imports.append("import java.time.LocalDateTime;")
    imports.append("import java.math.BigDecimal;")
    imports.append("")
    if needs_page:
        imports.append("import org.springframework.data.domain.PageImpl;")
    imports.append("import java.util.List;")
    imports.append("")
    imports.append("import static org.mockito.ArgumentMatchers.any;")
    if needs_get:
        imports.append("import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;")
    if needs_patch_dto:
        imports.append("import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;")
    if "create" in endpoints:
        imports.append("import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;")
    imports.append("import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;")
    imports.append("import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;")

    field_lines = [
        "    @Autowired",
        "    private MockMvc mockMvc;",
        "",
        "    @MockBean",
        f"    private {entity_name}Service service;",
    ]
    if needs_idempotency:
        field_lines.extend(["", "    @MockBean", "    private IdempotencyService idempotencyService;"])
    field_lines.extend(["", "    @Autowired", "    private ObjectMapper objectMapper;"])

    imports_block = "\n".join(imports)
    fields_block = "\n".join(field_lines)
    tests_block = "\n".join(tests)

    return f"""package com.example.crud.controller;

{imports_block}

@WebMvcTest({entity_name}Controller.class)
@WithMockUser(roles = "ADMIN")
class {entity_name}ControllerTest {{

{fields_block}
{tests_block}
}}
"""


def get_postgres_integration_test(entity_lower):
    return f"""package com.example.crud.integration;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;
import com.example.crud.configuration.IdempotencyService;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@Testcontainers(disabledWithoutDocker = true)
class PostgreSQLIntegrationTest {{
    @Container
    static final PostgreSQLContainer<?> POSTGRES =
            new PostgreSQLContainer<>("postgres:16-alpine");

    @DynamicPropertySource
    static void properties(DynamicPropertyRegistry registry) {{
        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", POSTGRES::getUsername);
        registry.add("spring.datasource.password", POSTGRES::getPassword);
        registry.add("spring.flyway.url", POSTGRES::getJdbcUrl);
        registry.add("spring.flyway.user", POSTGRES::getUsername);
        registry.add("spring.flyway.password", POSTGRES::getPassword);
        registry.add("app.security.user", () -> "integration-admin");
        registry.add("app.security.password", () -> "integration-password");
    }}

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Autowired
    private IdempotencyService idempotencyService;

    @Autowired
    private MockMvc mockMvc;

    @Test
    void flywayCreatesTableAndVersionColumn() {{
        Integer tables = jdbcTemplate.queryForObject(
                "SELECT count(*) FROM information_schema.tables " +
                        "WHERE table_schema='public' AND table_name='{entity_lower}s'",
                Integer.class);
        Integer versions = jdbcTemplate.queryForObject(
                "SELECT count(*) FROM information_schema.columns " +
                        "WHERE table_schema='public' AND table_name='{entity_lower}s' " +
                        "AND column_name='version'",
                Integer.class);
        assertEquals(1, tables);
        assertEquals(1, versions);
    }}

    @Test
    void idempotencyKeyCreatesTheResourceOnlyOnce() {{
        AtomicInteger creations = new AtomicInteger();
        Integer first = idempotencyService.execute(
                "integration-key", "integration-resource",
                () -> {{ creations.incrementAndGet(); return 41; }},
                id -> id, Integer::intValue);
        Integer repeated = idempotencyService.execute(
                "integration-key", "integration-resource",
                () -> {{ creations.incrementAndGet(); return 99; }},
                id -> id, Integer::intValue);

        assertEquals(41, first);
        assertEquals(41, repeated);
        assertEquals(1, creations.get());
    }}

    @Test
    void apiRejectsUnauthenticatedRequests() throws Exception {{
        mockMvc.perform(get("/api/{entity_lower}s"))
                .andExpect(status().isUnauthorized());
    }}
}}
"""


def get_cucumber_runner():
    """Unico por proyecto. El nombre termina en 'Test' a propósito: es el
    patron por defecto que reconoce Surefire/Failsafe, y el que dispara la
    ejecucion real de los .feature via el motor 'cucumber' de JUnit 5. Las
    clases de pasos (p.ej. PedidoSteps) NO siguen ese patron a proposito,
    para que Surefire no intente ejecutarlas como si fueran tests JUnit por
    si mismas."""
    return """package com.example.crud.cucumber;

import io.cucumber.junit.platform.engine.Constants;
import org.junit.platform.suite.api.ConfigurationParameter;
import org.junit.platform.suite.api.IncludeEngines;
import org.junit.platform.suite.api.SelectClasspathResource;
import org.junit.platform.suite.api.Suite;

@Suite
@IncludeEngines("cucumber")
@SelectClasspathResource("features")
@ConfigurationParameter(key = Constants.GLUE_PROPERTY_NAME, value = "com.example.crud.cucumber")
@ConfigurationParameter(
        key = Constants.PLUGIN_PROPERTY_NAME,
        value = "io.qameta.allure.cucumber7jvm.AllureCucumber7Jvm")
public class RunCucumberTest {
}
"""


def get_cucumber_spring_configuration():
    """Contexto Spring compartido por todas las clases de pasos: un unico
    Testcontainers de Postgres para toda la ejecucion de Cucumber, igual que
    PostgreSQLIntegrationTest pero arrancado a mano. Cucumber no ejecuta esta
    clase como un test JUnit 5 (solo la referencia via
    @CucumberContextConfiguration), asi que @Testcontainers/@Container -que
    dependen del ciclo de vida BeforeAllCallback de JUnit 5- nunca arrancarian
    el contenedor: 'Mapped port can only be obtained after the container is
    started'."""
    return """package com.example.crud.cucumber;

import io.cucumber.spring.CucumberContextConfiguration;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;

@CucumberContextConfiguration
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public class CucumberSpringConfiguration {

    static final PostgreSQLContainer<?> POSTGRES =
            new PostgreSQLContainer<>("postgres:16-alpine");

    static {
        POSTGRES.start();
    }

    @DynamicPropertySource
    static void properties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", POSTGRES::getUsername);
        registry.add("spring.datasource.password", POSTGRES::getPassword);
        registry.add("spring.flyway.url", POSTGRES::getJdbcUrl);
        registry.add("spring.flyway.user", POSTGRES::getUsername);
        registry.add("spring.flyway.password", POSTGRES::getPassword);
        registry.add("app.security.user", () -> "cucumber-admin");
        registry.add("app.security.password", () -> "cucumber-password");
    }
}
"""


def get_cucumber_feature(entity_name, entity_lower, endpoints, has_reference):
    """has_reference: si la entidad tiene un campo 'reference', se omite el
    escenario de alta valida (necesitaria crear antes la entidad referenciada,
    fuera del alcance de este generador) y solo se cubren list/validacion/404,
    que no dependen de otra entidad ya existente en la base de datos."""
    endpoints = set(endpoints)
    scenarios = []
    if "list" in endpoints:
        scenarios.append(f"""
  Scenario: Listar {entity_lower}s
    When se listan los {entity_lower}s
    Then la respuesta tiene estado 200""")
    if "create" in endpoints and not has_reference:
        scenarios.append(f"""
  Scenario: Crear un {entity_lower} valido
    When se crea un {entity_lower} valido
    Then la respuesta tiene estado 201
    When se consulta el {entity_lower} creado
    Then la respuesta tiene estado 200""")
    if "create" in endpoints:
        scenarios.append(f"""
  Scenario: Crear un {entity_lower} sin campos obligatorios
    When se crea un {entity_lower} sin campos obligatorios
    Then la respuesta tiene estado 400""")
    if "get" in endpoints:
        scenarios.append(f"""
  Scenario: Consultar un {entity_lower} inexistente
    When se consulta el {entity_lower} con id 999999
    Then la respuesta tiene estado 404""")
    body = "\n".join(scenarios)
    return f"""Feature: CRUD de {entity_name}
{body}
"""


def get_cucumber_steps(entity_name, entity_lower, create_assignments, has_required_fields, endpoints, enum_import_lines=""):
    endpoints = set(endpoints)
    enum_imports = f"{enum_import_lines}\n" if enum_import_lines else ""

    steps = []
    if "list" in endpoints:
        steps.append(f"""
    @When("se listan los {entity_lower}s")
    public void seListanLos{entity_name}s() {{
        response = authenticated().get("/api/{entity_lower}s");
    }}""")
    if "create" in endpoints:
        steps.append(f"""
    @When("se crea un {entity_lower} valido")
    public void seCreaUn{entity_name}Valido() throws Exception {{
        {entity_name}CreateDTO dto = new {entity_name}CreateDTO();
{create_assignments}
        response = authenticated()
                .header("Idempotency-Key", java.util.UUID.randomUUID().toString())
                .contentType("application/json")
                .body(objectMapper.writeValueAsString(dto))
                .post("/api/{entity_lower}s");
        if (response.statusCode() == 201) {{
            createdId = response.jsonPath().getInt("id");
        }}
    }}

    @When("se crea un {entity_lower} sin campos obligatorios")
    public void seCreaUn{entity_name}SinCamposObligatorios() {{
        response = authenticated()
                .header("Idempotency-Key", java.util.UUID.randomUUID().toString())
                .contentType("application/json")
                .body("{{}}")
                .post("/api/{entity_lower}s");
    }}""")
    if "get" in endpoints:
        steps.append(f"""
    @When("se consulta el {entity_lower} con id {{int}}")
    public void seConsultaEl{entity_name}ConId(Integer id) {{
        response = authenticated().get("/api/{entity_lower}s/" + id);
    }}

    @When("se consulta el {entity_lower} creado")
    public void seConsultaEl{entity_name}Creado() {{
        response = authenticated().get("/api/{entity_lower}s/" + createdId);
    }}""")
    steps_block = "\n".join(steps)

    validation_note = "" if has_required_fields else (
        f"    // {entity_name} no tiene campos obligatorios: el escenario de "
        "alta invalida solo comprueba que un cuerpo vacio no rompe la API.\n"
    )

    return f"""package com.example.crud.cucumber;

import com.example.crud.dto.{entity_name}CreateDTO;
{enum_imports}import com.fasterxml.jackson.databind.ObjectMapper;
import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;
import io.restassured.RestAssured;
import io.restassured.response.Response;
import io.restassured.specification.RequestSpecification;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.test.web.server.LocalServerPort;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

import static org.junit.jupiter.api.Assertions.assertEquals;

public class {entity_name}Steps {{

    @LocalServerPort
    private int port;

    @Value("${{app.security.user}}")
    private String username;

    @Value("${{app.security.password}}")
    private String password;

    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();
    private Response response;
    private Integer createdId;

{validation_note}    private RequestSpecification authenticated() {{
        return RestAssured.given()
                .port(port)
                .auth().preemptive().basic(username, password);
    }}
{steps_block}

    @Then("la respuesta tiene estado {{int}}")
    public void laRespuestaTieneEstado(int statusCode) {{
        assertEquals(statusCode, response.statusCode());
    }}
}}
"""
