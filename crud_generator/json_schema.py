"""Carga de una definición de entidad desde un fichero JSON.

Formato esperado::

    {
        "entity": "FondoInversion",
        "architecture": "hexagonal",
        "fields": [
            {"name": "id", "type": "int"},
            {"name": "isin", "type": "string", "max": 12, "not_blank": true,
             "unique": true, "index": true},
            {"name": "patrimonio", "type": "decimal", "precision": 18, "scale": 2,
             "required": true, "positive": true},
            {"name": "activo", "type": "boolean", "required": true, "default": true}
        ]
    }

"architecture" es opcional (por defecto "layered", o el valor de --architecture si
se indica en la CLI). A diferencia del DSL de texto, los valores de las reglas
("default", etc.) no tienen restricción de caracteres.
"""

import json

from .parsing import (
    DefinitionError,
    normalize_base_package,
    normalize_endpoints,
    parse_attributes_from_fields,
)


def load_schema(path):
    try:
        with open(path, encoding="utf-8") as handle:
            raw = handle.read()
    except OSError as error:
        raise DefinitionError(f"No se pudo leer el fichero JSON '{path}': {error}.") from error

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        raise DefinitionError(f"El fichero JSON '{path}' no es válido: {error}.") from error

    if not isinstance(data, dict):
        raise DefinitionError("El JSON debe ser un objeto con 'entity' y 'fields'.")

    entity_name = data.get("entity")
    if not isinstance(entity_name, str) or not entity_name.strip():
        raise DefinitionError("El JSON debe indicar 'entity' con el nombre de la entidad.")

    fields = data.get("fields")
    if not isinstance(fields, list) or not fields:
        raise DefinitionError("El JSON debe indicar 'fields' como una lista no vacía.")

    architecture = data.get("architecture")
    if architecture is not None and not isinstance(architecture, str):
        raise DefinitionError("'architecture' debe ser un texto si se indica en el JSON.")

    base_package = data.get("package")
    if base_package is not None:
        if not isinstance(base_package, str):
            raise DefinitionError("'package' debe ser un texto si se indica en el JSON.")
        base_package = normalize_base_package(base_package)

    endpoints = data.get("endpoints")
    if endpoints is not None:
        endpoints = normalize_endpoints(endpoints)

    unknown_top_level = set(data) - {
        "entity",
        "architecture",
        "package",
        "endpoints",
        "fields",
    }
    if unknown_top_level:
        raise DefinitionError(
            f"Claves desconocidas en el JSON: {', '.join(sorted(unknown_top_level))}."
        )

    attrs = parse_attributes_from_fields(fields)
    return entity_name, architecture, base_package, endpoints, attrs
