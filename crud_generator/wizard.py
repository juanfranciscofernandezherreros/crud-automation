"""Asistente interactivo: hace antes de generar las preguntas que hacen
falta para un uso "profesional" del generador (arquitectura, endpoints,
paquete, si hace falta un endpoint de negocio propio...) en vez de exigir
que ya vengan resueltas en flags o en un JSON.

Solo recopila respuestas y genera el proyecto -- el resto del ciclo
(verificar/publicar/recordar convenciones) lo sigue haciendo cli.main() con
sus propios helpers, exactamente igual que en el modo de flags, para que
ambos caminos se comporten de forma idéntica una vez generado."""

import sys

from .architectures import ARCHITECTURES, normalize_architecture
from .generator import generate_project
from .parsing import (
    VALID_ENDPOINTS,
    DefinitionError,
    normalize_custom_endpoints,
    normalize_endpoints,
    normalize_entity_name,
    parse_attributes,
)


def _yes_no(prompt, default=False):
    suffix = "S/n" if default else "s/N"
    raw = input(f"{prompt} ({suffix}): ").strip().lower()
    if not raw:
        return default
    return raw in ("s", "si", "sí", "y", "yes")


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
    """CRUD de negocio fuera del molde fijo (list/get/create/update/patch/
    delete): el generador no puede inventar la lógica, así que solo se
    scaffolds -- ver parsing.normalize_custom_endpoints."""
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


def _print_fixed_infrastructure_notice():
    """Preguntas de la sesión "qué preguntarme para uso profesional" que el
    generador no puede resolver con una respuesta -- son fijas en las
    plantillas. Se informan en vez de preguntarse, para que se sepa antes de
    generar si encajan con la infraestructura real."""
    print()
    print("Infraestructura fija en las plantillas generadas (no configurable aquí):")
    print("  - Base de datos: PostgreSQL (Flyway, tipos, todo asume Postgres).")
    print("  - CI: GitHub Actions (.github/workflows/ci.yml).")
    print("  - Seguridad: HTTP Basic con roles USER/ADMIN.")
    print("  - Observabilidad: Prometheus + Loki + Grafana en docker-compose.yml.")
    print()


def run_wizard(conventions=None):
    """Ejecuta el asistente y genera el proyecto resultante. Devuelve
    (base_dir, verify, push_github, repo_name, private, remember,
    architecture, base_package, endpoints) para que cli.main() complete el
    ciclo post-generación (verificar/publicar/recordar) con sus propios
    helpers, igual que en el modo de flags."""
    if not sys.stdin.isatty():
        raise DefinitionError(
            "--wizard necesita una terminal interactiva; usa los flags "
            "normales (--json/--architecture/...) en scripts o CI."
        )

    conventions = conventions or {}

    entity_name = _ask_entity_name()
    attrs_str = _ask_fields()
    architecture = _ask_architecture(conventions.get("architecture"))
    endpoints = _ask_endpoints(conventions.get("endpoints"))
    custom_endpoints = _ask_custom_endpoints()

    default_package = conventions.get("package") or "com.example.crud"
    base_package = input(f"Paquete base [{default_package}]: ").strip() or default_package

    _print_fixed_infrastructure_notice()

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
        f"Proyecto {base_dir} generado con éxito, "
        "incluyendo todas las capas, tests y docs/index.html."
    )

    return (
        base_dir, verify, push_github, repo_name, private, remember,
        architecture, base_package, endpoints,
    )
