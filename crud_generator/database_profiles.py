"""Perfiles de base de datos para el generador CRUD.

PostgreSQL sigue siendo el perfil por defecto. El perfil ``sqlserver`` adapta
las plantillas existentes en tiempo de generación para no duplicar el motor
completo de scaffolding.
"""

SUPPORTED_DATABASES = {"postgresql", "sqlserver"}

SQLSERVER_SQL_TYPES = {
    "int": "INT",
    "string": "NVARCHAR(255)",
    "text": "NVARCHAR(MAX)",
    "float": "REAL",
    "double": "FLOAT",
    "decimal": "DECIMAL(19, 4)",
    "boolean": "BIT",
    "datetime": "DATETIME2",
    "date": "DATE",
}


def normalize_database(value):
    value = (value or "postgresql").strip().lower()
    aliases = {
        "postgres": "postgresql",
        "postgresql": "postgresql",
        "mssql": "sqlserver",
        "sql-server": "sqlserver",
        "sqlserver": "sqlserver",
    }
    try:
        return aliases[value]
    except KeyError as exc:
        allowed = ", ".join(sorted(SUPPORTED_DATABASES))
        raise ValueError(
            f"Base de datos no soportada: '{value}'. Usa una de: {allowed}."
        ) from exc


def extract_database_argument(args):
    """Extrae --database/-d sin acoplar la CLI principal a perfiles concretos."""
    args = list(args)
    database = "postgresql"

    for index, arg in enumerate(list(args)):
        if arg.startswith("--database="):
            database = normalize_database(arg.split("=", 1)[1])
            del args[index]
            return args, database

    for option in ("--database", "-d"):
        if option in args:
            index = args.index(option)
            if index + 1 >= len(args):
                raise ValueError(f"Falta el valor de {option}.")
            database = normalize_database(args[index + 1])
            del args[index : index + 2]
            break
    return args, database


def _sqlserver_pom(postgres_pom):
    return (
        postgres_pom
        .replace(
            "<artifactId>flyway-database-postgresql</artifactId>",
            "<artifactId>flyway-sqlserver</artifactId>",
        )
        .replace(
            "<dependency><groupId>org.postgresql</groupId><artifactId>postgresql</artifactId><scope>runtime</scope></dependency>",
            "<dependency><groupId>com.microsoft.sqlserver</groupId><artifactId>mssql-jdbc</artifactId><scope>runtime</scope></dependency>",
        )
        .replace(
            "<dependency><groupId>org.testcontainers</groupId><artifactId>postgresql</artifactId><scope>test</scope></dependency>",
            "<dependency><groupId>org.testcontainers</groupId><artifactId>mssqlserver</artifactId><scope>test</scope></dependency>",
        )
    )


def _sqlserver_application_yml(entity_lower):
    return f"""server:
  port: 8080
spring:
  application:
    name: {entity_lower}-service
  datasource:
    sqlserverdb:
      url: jdbc:sqlserver://${{HOSTNAME}};database=${{DATABASENAME}};encrypt=true;trustServerCertificate=true;
      driver-class-name: com.microsoft.sqlserver.jdbc.SQLServerDriver
      username: ${{USERNAME}}
      password: ${{PASSWORD}}
      hikari:
        connection-timeout: 30000
        idle-timeout: 300000
        max-lifetime: 900000
        maximum-pool-size: 40
        minimum-idle: 25
        pool-name: ConnPool
  jpa:
    hibernate:
      ddl-auto: validate
    show-sql: ${{JPA_SHOW_SQL:false}}
    properties:
      hibernate:
        format_sql: true
        dialect: org.hibernate.dialect.SQLServerDialect
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


def _sqlserver_env_defaults():
    return """HOSTNAME=localhost
DATABASENAME=master
USERNAME=sa
PASSWORD=YourStrong!Passw0rd
APP_SECURITY_USER=admin
APP_SECURITY_PASSWORD=otra-clave-segura
"""


def _sqlserver_env_example():
    return (
        '# Copia este fichero a ".env" y ajusta los valores antes de desplegar.\n'
        "# Para Docker Compose, HOSTNAME se sobrescribe a 'db'.\n"
        + _sqlserver_env_defaults()
    )


def _sqlserver_env_default():
    return (
        "# Generado automaticamente para desarrollo local. Cambia PASSWORD\n"
        "# antes de desplegar en cualquier entorno compartido.\n"
        + _sqlserver_env_defaults()
    )


def _sqlserver_docker_compose(entity_lower):
    return f"""version: '3.8'
services:
  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      - HOSTNAME=db
      - DATABASENAME=${{DATABASENAME:-master}}
      - USERNAME=${{USERNAME:-sa}}
      - PASSWORD=${{PASSWORD:?Set PASSWORD}}
      - APP_SECURITY_USER=${{APP_SECURITY_USER:?Set APP_SECURITY_USER}}
      - APP_SECURITY_PASSWORD=${{APP_SECURITY_PASSWORD:?Set APP_SECURITY_PASSWORD}}
      - OTEL_EXPORTER_OTLP_ENDPOINT=${{OTEL_EXPORTER_OTLP_ENDPOINT:-http://host.docker.internal:4318/v1/traces}}
      - LOKI_URL=${{LOKI_URL:-http://loki:3100}}
    depends_on:
      db:
        condition: service_healthy

  db:
    image: mcr.microsoft.com/mssql/server:2022-latest
    environment:
      - ACCEPT_EULA=Y
      - MSSQL_PID=Developer
      - MSSQL_SA_PASSWORD=${{PASSWORD:?Set PASSWORD}}
    ports:
      - "1433:1433"
    healthcheck:
      test: ["CMD-SHELL", "/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P '$${{MSSQL_SA_PASSWORD}}' -C -Q 'SELECT 1' || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 20s

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


def _sqlserver_column_definition(fields, attr, force_nullable=False):
    column = attr["sql_column"]
    validations = attr["validations"]
    sql_type = attr["sql_type"]
    if attr["type"] == "string" and "max" in validations:
        sql_type = f"NVARCHAR({validations['max']})"

    constraints = []
    if attr["name"] in ["creado_en", "created_at"]:
        constraints.extend(["NOT NULL", "DEFAULT CURRENT_TIMESTAMP"])
    elif (validations.get("required") or validations.get("not_blank")) and not (
        force_nullable and "default" not in validations
    ):
        constraints.append("NOT NULL")

    if "default" in validations:
        literal = fields.format_default_sql_literal(attr)
        if attr["type"] == "boolean":
            literal = "1" if str(validations["default"]).lower() == "true" else "0"
        constraints.append(f"DEFAULT {literal}")
    if validations.get("unique"):
        constraints.append("UNIQUE")

    checks = []
    if validations.get("not_blank"):
        checks.append(f"LTRIM(RTRIM({column})) <> ''")
    if validations.get("positive"):
        checks.append(f"{column} > 0")
    if "min" in validations:
        expression = (
            f"LEN({column}) >= {validations['min']}"
            if attr["type"] in {"string", "text"}
            else f"{column} >= {validations['min']}"
        )
        checks.append(expression)
    if "max" in validations:
        if attr["type"] == "text":
            checks.append(f"LEN({column}) <= {validations['max']}")
        elif attr["type"] != "string":
            checks.append(f"{column} <= {validations['max']}")
    if attr["type"] == "enum":
        options = ", ".join(f"'{value}'" for value in attr["enum_values"])
        checks.append(f"{column} IN ({options})")
    constraints.extend(f"CHECK ({check})" for check in checks)

    if attr["type"] == "reference":
        constraints.append(f"REFERENCES {attr['reference_table']}(id)")

    suffix = f" {' '.join(constraints)}" if constraints else ""
    return f"{column} {sql_type}{suffix}"


def _sqlserver_fields(fields, attrs, table_name="tabla"):
    lines = []
    for attr in attrs:
        if attr["is_id"]:
            lines.append(f"    {attr['name']} INT IDENTITY(1,1) PRIMARY KEY")
            continue
        lines.append(f"    {_sqlserver_column_definition(fields, attr)}")

    for group, members in fields.generate_composite_unique_groups(attrs).items():
        columns = ", ".join(members)
        lines.append(f"    CONSTRAINT uq_{table_name}_{group} UNIQUE ({columns})")

    lines.append("    version BIGINT NOT NULL DEFAULT 0")
    return ",\n".join(lines)


def _sqlserver_migration(entity_lower, sql_fields, sql_indexes=""):
    table = _pluralize(entity_lower)
    indexes = f"\n{sql_indexes}\n" if sql_indexes else ""
    return f"""CREATE TABLE {table} (
{sql_fields}
);
{indexes}
IF OBJECT_ID(N'idempotency_keys', N'U') IS NULL
BEGIN
    CREATE TABLE idempotency_keys (
        idempotency_key NVARCHAR(128) NOT NULL,
        resource_type NVARCHAR(100) NOT NULL,
        resource_id INT NOT NULL,
        created_at DATETIME2 NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT pk_idempotency_keys PRIMARY KEY (idempotency_key, resource_type)
    );
END;
"""


def _pluralize(value):
    # Se sustituye en install_database_profile por parsing.pluralize para mantener
    # exactamente las mismas reglas del generador.
    return value + "s"


def _data_source_properties(base_package):
    return f"""package {base_package}.configuration;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import lombok.Data;

@Data
@Component
@ConfigurationProperties("spring.datasource.sqlserverdb")
public class DataSourceProperties {{

    private String url;
    private String username;
    private String password;
    private String driverClassName;

    private Hikari hikari = new Hikari();

    @Data
    public static class Hikari {{
        private int connectionTimeout;
        private int idleTimeout;
        private int maxLifetime;
        private int maximumPoolSize;
        private int minimumIdle;
        private String poolName;
    }}
}}
"""


def _data_source_configuration(base_package):
    return f"""package {base_package}.configuration;

import javax.sql.DataSource;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import com.zaxxer.hikari.HikariDataSource;

import lombok.RequiredArgsConstructor;

@Configuration
@RequiredArgsConstructor
public class DataSourceConfiguration {{

    private final DataSourceProperties properties;

    @Bean
    public DataSource dataSource() {{
        HikariDataSource dataSource = new HikariDataSource();
        dataSource.setJdbcUrl(properties.getUrl());
        dataSource.setUsername(properties.getUsername());
        dataSource.setPassword(properties.getPassword());
        dataSource.setDriverClassName(properties.getDriverClassName());

        DataSourceProperties.Hikari hikari = properties.getHikari();
        dataSource.setConnectionTimeout(hikari.getConnectionTimeout());
        dataSource.setIdleTimeout(hikari.getIdleTimeout());
        dataSource.setMaxLifetime(hikari.getMaxLifetime());
        dataSource.setMaximumPoolSize(hikari.getMaximumPoolSize());
        dataSource.setMinimumIdle(hikari.getMinimumIdle());
        dataSource.setPoolName(hikari.getPoolName());
        return dataSource;
    }}
}}
"""


def _write_sqlserver_configuration(write_file, base_dir, base_package):
    package_path = base_package.replace(".", "/")
    java_base = f"{base_dir}/src/main/java/{package_path}/configuration"
    write_file(
        f"{java_base}/DataSourceProperties.java",
        _data_source_properties(base_package),
    )
    write_file(
        f"{java_base}/DataSourceConfiguration.java",
        _data_source_configuration(base_package),
    )


def _sqlserver_write_migration(
    migrations, fields, res_base, entity_name, entity_lower, table_name, attrs,
    write_file, get_sql_migration,
):
    migration_dir = migrations._migration_dir_on_disk(res_base)
    entity_versions = migrations._existing_versions_for_entity(migration_dir, entity_name)
    all_versions = migrations._all_existing_versions(migration_dir)
    next_version = (max(all_versions) if all_versions else 0) + 1

    if not entity_versions:
        write_file(
            f"{res_base}/db/migration/V{next_version}__Create_Table_{entity_name}.sql",
            get_sql_migration(
                entity_lower,
                fields.generate_sql_fields(attrs, table_name),
                fields.generate_sql_indexes(attrs, table_name),
            ),
        )
        return

    known_columns = migrations._columns_already_migrated(migration_dir, entity_versions)
    new_attrs = [
        attr for attr in attrs
        if not attr["is_id"] and attr["name"] not in known_columns
    ]
    if not new_attrs:
        return

    lines = [
        f"ALTER TABLE {table_name} ADD "
        f"{fields.generate_sql_column_definition(attr, force_nullable=True)};"
        for attr in new_attrs
    ]
    warnings = [
        attr["name"]
        for attr in new_attrs
        if (attr["validations"].get("required") or attr["validations"].get("not_blank"))
        and "default" not in attr["validations"]
    ]
    header = (
        "-- Migracion incremental generada automaticamente al regenerar el proyecto con --force.\n"
        f"-- Anade solo las columnas nuevas de '{entity_name}'; no borra ni modifica columnas existentes.\n"
    )
    if warnings:
        header += (
            "-- ATENCION: "
            + ", ".join(warnings)
            + " son obligatorias en el DSL/JSON pero se crean aqui como NULL "
              "porque la tabla puede tener filas; rellena valores y fija NOT NULL despues.\n"
        )
    write_file(
        f"{res_base}/db/migration/V{next_version}__Update_Table_{entity_name}.sql",
        header + "\n".join(lines) + "\n",
    )


def install_database_profile(database):
    """Instala el perfil solicitado antes de ejecutar la CLI del generador."""
    database = normalize_database(database)
    if database == "postgresql":
        return database

    # Primero se cambia el mapa antes de importar parsing.py, que captura
    # SQL_TYPES mediante ``from .types import SQL_TYPES``.
    from . import types
    types.SQL_TYPES.clear()
    types.SQL_TYPES.update(SQLSERVER_SQL_TYPES)

    from . import parsing
    global _pluralize
    _pluralize = parsing.pluralize

    from . import fields
    fields.generate_sql_column_definition = (
        lambda attr, force_nullable=False:
        _sqlserver_column_definition(fields, attr, force_nullable)
    )
    fields.generate_sql_fields = (
        lambda attrs, table_name="tabla":
        _sqlserver_fields(fields, attrs, table_name)
    )

    from . import templates
    original_pom = templates.get_pom_xml
    templates.get_pom_xml = lambda name: _sqlserver_pom(original_pom(name))
    templates.get_application_yml = _sqlserver_application_yml
    templates.get_docker_compose = _sqlserver_docker_compose
    templates.get_env_example = _sqlserver_env_example
    templates.get_env_default = _sqlserver_env_default
    templates.get_sql_migration = _sqlserver_migration

    from . import migrations
    migrations.generate_sql_column_definition = fields.generate_sql_column_definition
    migrations.generate_sql_fields = fields.generate_sql_fields
    migrations.write_migration = lambda res_base, entity_name, entity_lower, table_name, attrs, write_file, get_sql_migration: _sqlserver_write_migration(
        migrations, fields, res_base, entity_name, entity_lower, table_name, attrs,
        write_file, get_sql_migration,
    )

    # Añade las clases Java sin duplicar la lógica de scaffolding existente.
    from . import generator
    original_layered_scaffolding = generator._write_layered_scaffolding

    def layered_scaffolding(write_file, base_dir, project_lower, base_package, endpoints):
        original_layered_scaffolding(
            write_file, base_dir, project_lower, base_package, endpoints
        )
        _write_sqlserver_configuration(write_file, base_dir, base_package)

    generator._write_layered_scaffolding = layered_scaffolding

    from . import ports_generator
    original_ports_scaffolding = ports_generator._write_ports_scaffolding

    def ports_scaffolding(
        write_file, base_dir, project_lower, base_package, main_java, resources
    ):
        original_ports_scaffolding(
            write_file, base_dir, project_lower, base_package, main_java, resources
        )
        package_path = base_package.replace(".", "/")
        config_root = f"{main_java}/{package_path}/configuration"
        write_file(
            f"{config_root}/DataSourceProperties.java",
            _data_source_properties(base_package),
        )
        write_file(
            f"{config_root}/DataSourceConfiguration.java",
            _data_source_configuration(base_package),
        )

    ports_generator._write_ports_scaffolding = ports_scaffolding
    return database
