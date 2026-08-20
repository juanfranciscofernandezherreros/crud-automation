"""Asistente interactivo para generar proyectos CRUD de forma guiada."""

import sys

from .architectures import ARCHITECTURES, normalize_architecture
from .database_profiles import install_database_profile
from .generator import generate_project
from .parsing import (
    VALID_ENDPOINTS,
    DefinitionError,
    normalize_custom_endpoints,
    normalize_endpoints,
    normalize_entity_name,
    parse_attributes,
)

JAVA_VERSIONS = ("17", "21")
DATABASES = ("postgresql", "sqlserver")


def _yes_no(prompt, default=False):
    suffix = "S/n" if default else "s/N"
    raw = input(f"{prompt} ({suffix}): ").strip().lower()
    if not raw:
        return default
    return raw in ("s", "si", "sí", "y", "yes")


def _ask_choice(label, choices, default):
    print(f"{label}:")
    for index, choice in enumerate(choices, start=1):
        marker = " (por defecto)" if choice == default else ""
        print(f"  {index}. {choice}{marker}")
    while True:
        raw = input(f"Selecciona una opción [{default}]: ").strip().lower()
        if not raw:
            return default
        if raw.isdigit() and 1 <= int(raw) <= len(choices):
            return choices[int(raw) - 1]
        if raw in choices:
            return raw
        print(f"  Opción no válida. Usa: {', '.join(choices)}")


def _ask_java_version():
    return _ask_choice("Versión de Java", JAVA_VERSIONS, "21")


def _ask_database():
    return _ask_choice("Base de datos", DATABASES, "postgresql")


def _install_java_version(java_version):
    """Adapta las plantillas Maven y Docker a Java 17 o 21 para esta ejecución."""
    if java_version not in JAVA_VERSIONS:
        raise DefinitionError(f"Versión Java no soportada: {java_version}")

    from . import templates

    original_get_pom_xml = templates.get_pom_xml

    def get_pom_xml(name):
        pom = original_get_pom_xml(name)
        return pom.replace("<java.version>21</java.version>", f"<java.version>{java_version}</java.version>")

    templates.get_pom_xml = get_pom_xml
    templates.DOCKERFILE = templates.DOCKERFILE.replace(
        "eclipse-temurin-21", f"eclipse-temurin-{java_version}"
    )


def _ask_entity_name():
    while True:
        raw = input("Nombre de la entidad (p.ej. Producto): ").strip()
        try:
            return normalize_entity_name(raw)
        except DefinitionError as error:
            print(f"  {error}")


def _ask_fields():
    print(
        "Campos, formato 'nombre:tipo[:regla]' separados por comas. "
        "Debe incluir 'id'."
    )
    print('  Ejemplo: id:int, nombre:string:not_blank:max=120, precio:decimal:positive')
    while True:
        attrs_str = input("Campos: ").strip()
        try:
            parse_attributes(attrs_str)
            return attrs_str
        except DefinitionError as error:
            print(f"  {error}")


def _ask_architecture(default_architecture):
    default_architecture = default_architecture or ARCHITECTURES[0]
    print("Arquitectura:")
    for index, architecture in enumerate(ARCHITECTURES, start=1):
        marker = " (por defecto)" if architecture == default_architecture else ""
        print(f"  {index}. {architecture}{marker}")
    while True:
        raw = input(f"Selecciona una opción [{default_architecture}]: ").strip()
        if not raw:
            return default_architecture
        if raw.isdigit() and 1 <= int(raw) <= len(ARCHITECTURES):
            return ARCHITECTURES[int(raw) - 1]
        try:
            return normalize_architecture(raw)
        except DefinitionError as error:
            print(f"  {error}")


def _ask_endpoints(default_endpoints):
    default_label = ", ".join(default_endpoints) if default_endpoints else "todos"
    while True:
        raw = input(
            f"Endpoints ({', '.join(VALID_ENDPOINTS)}), separados por comas "
            f"[{default_label}]: "
        ).strip()
        if not raw:
            return default_endpoints
        try:
            return normalize_endpoints([value.strip() for value in raw.split(",")])
        except DefinitionError as error:
            print(f"  {error}")


def _ask_endpoint_field_list(label):
    print(f"  Campos de '{label}' (nombre:tipo), uno por línea. Línea vacía para terminar.")
    fields = []
    while True:
        raw = input(f"    campo de {label} (vacío para terminar): ").strip()
        if not raw:
            return fields or None
        if ":" not in raw:
            print("    Formato: nombre:tipo (p.ej. puntos_local:int)")
            continue
        name, type_name = (part.strip() for part in raw.split(":", 1))
        fields.append({"name": name, "type": type_name})


def _ask_custom_endpoints():
    raw_endpoints = []
    while _yes_no("¿Añadir un endpoint personalizado (fuera del CRUD)?", default=False):
        name = input("  Nombre (p.ej. finalizar): ").strip()
        method = input("  Método HTTP [POST]: ").strip() or "POST"
        path = input("  Path (p.ej. /{id}/finalizar): ").strip()
        request = _ask_endpoint_field_list("request")
        response = _ask_endpoint_field_list("response")
        spec = {"name": name, "method": method, "path": path}
        if request:
            spec["request"] = request
        if response:
            spec["response"] = response
        raw_endpoints.append(spec)
    if not raw_endpoints:
        return None
    return normalize_custom_endpoints(raw_endpoints)


def _print_infrastructure_notice(java_version, database):
    print()
    print("Configuración seleccionada:")
    print(f"  - Java: {java_version}")
    print(f"  - Base de datos: {database}")
    if database == "sqlserver":
        print("  - SQL Server: JDBC + Flyway + Testcontainers + HikariCP.")
    else:
        print("  - PostgreSQL: JDBC + Flyway + Testcontainers.")
    print("  - CI: GitHub Actions (.github/workflows/ci.yml).")
    print("  - Seguridad: HTTP Basic con roles USER/ADMIN.")
    print("  - Observabilidad: Prometheus + Loki + Grafana en docker-compose.yml.")
    print()


def run_wizard(conventions=None):
    """Ejecuta el asistente y genera el proyecto resultante."""
    if not sys.stdin.isatty():
        raise DefinitionError(
            "--wizard necesita una terminal interactiva; usa los flags "
            "normales (--json/--architecture/...) en scripts o CI."
        )

    conventions = conventions or {}

    # Estas decisiones se toman antes de parsear campos y generar archivos para
    # que el perfil SQL y las plantillas Maven/Docker sean coherentes entre sí.
    java_version = _ask_java_version()
    database = _ask_database()
    try:
        install_database_profile(database)
    except ValueError as error:
        raise DefinitionError(str(error)) from error
    _install_java_version(java_version)

    entity_name = _ask_entity_name()
    attrs_str = _ask_fields()
    architecture = _ask_architecture(conventions.get("architecture"))
    endpoints = _ask_endpoints(conventions.get("endpoints"))
    custom_endpoints = _ask_custom_endpoints()

    default_package = conventions.get("package") or "com.example.crud"
    base_package = input(f"Paquete base [{default_package}]: ").strip() or default_package

    _print_infrastructure_notice(java_version, database)

    overwrite = _yes_no("¿Sobrescribir si el directorio ya existe?", default=False)
    verify = _yes_no("¿Ejecutar 'mvn verify' tras generar?", default=False)

    push_github = _yes_no("¿Publicar el proyecto en GitHub?", default=False)
    repo_name = None
    private = False
    if push_github:
        repo_name = input("  Nombre del repositorio [el del directorio generado]: ").strip() or None
        private = _yes_no("  ¿Repositorio privado?", default=False)

    remember = _yes_no(
        "¿Guardar arquitectura/paquete/endpoints como convenciones para la próxima vez?",
        default=False,
    )

    base_dir = generate_project(
        entity_name, attrs_str, architecture,
        base_package=base_package, endpoints=endpoints, overwrite=overwrite,
        custom_endpoints=custom_endpoints,
    )
    print(
        f"Proyecto {base_dir} generado con éxito con Java {java_version} y {database}, "
        "incluyendo todas las capas, tests y docs/index.html."
    )

    return (
        base_dir, verify, push_github, repo_name, private, remember,
        architecture, base_package, endpoints,
    )
