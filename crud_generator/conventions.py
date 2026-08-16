"""Memoria local de convenciones (arquitectura/paquete/endpoints por defecto)
entre ejecuciones, para no repetir las mismas respuestas cada vez que se
genera un proyecto en el mismo repositorio/organización.

Deliberadamente NO incluye --verify ni --github: esas dos disparan acciones
reales (ejecutar una build, publicar un repositorio) y deben pedirse de
forma explícita en cada invocación, nunca activarse en silencio porque un
fichero de convenciones antiguo lo decía."""

import json

from .architectures import ARCHITECTURES
from .parsing import DefinitionError, VALID_ENDPOINTS, normalize_base_package

CONVENTIONS_FILENAME = "crud-automation.conventions.json"
_KNOWN_KEYS = {"architecture", "package", "endpoints"}


def load_conventions(base_dir="."):
    """Lee crud-automation.conventions.json en base_dir si existe. Devuelve
    {} si no existe -- no es un error, simplemente no hay convenciones
    guardadas todavía."""
    path = f"{base_dir}/{CONVENTIONS_FILENAME}"
    try:
        with open(path, encoding="utf-8") as handle:
            raw = handle.read()
    except OSError:
        return {}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        raise DefinitionError(
            f"'{CONVENTIONS_FILENAME}' no es un JSON válido: {error}."
        ) from error

    if not isinstance(data, dict):
        raise DefinitionError(f"'{CONVENTIONS_FILENAME}' debe ser un objeto JSON.")

    unknown = set(data) - _KNOWN_KEYS
    if unknown:
        raise DefinitionError(
            f"Claves desconocidas en '{CONVENTIONS_FILENAME}': "
            f"{', '.join(sorted(unknown))}."
        )

    architecture = data.get("architecture")
    if architecture is not None and architecture not in ARCHITECTURES:
        raise DefinitionError(
            f"'{CONVENTIONS_FILENAME}': arquitectura desconocida '{architecture}'. "
            f"Opciones: {', '.join(ARCHITECTURES)}."
        )

    package = data.get("package")
    if package is not None:
        package = normalize_base_package(package)

    endpoints = data.get("endpoints")
    if endpoints is not None:
        if not isinstance(endpoints, list) or not endpoints:
            raise DefinitionError(
                f"'{CONVENTIONS_FILENAME}': 'endpoints' debe ser una lista no vacía."
            )
        unknown_endpoints = set(endpoints) - set(VALID_ENDPOINTS)
        if unknown_endpoints:
            raise DefinitionError(
                f"'{CONVENTIONS_FILENAME}': endpoints desconocidos: "
                f"{', '.join(sorted(unknown_endpoints))}."
            )

    return {
        key: value
        for key, value in (
            ("architecture", architecture),
            ("package", package),
            ("endpoints", endpoints),
        )
        if value is not None
    }


def save_conventions(data, base_dir="."):
    """Escribe crud-automation.conventions.json en base_dir. Se espera que
    'data' ya venga solo con las claves conocidas (architecture/package/
    endpoints) y valores no nulos -- llama antes a load_conventions()-style
    validación si el valor viene de fuera de este módulo."""
    path = f"{base_dir}/{CONVENTIONS_FILENAME}"
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
    return path
