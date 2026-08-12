"""Carga de una definición de entidad (o de varias relacionadas) desde JSON.

Formato de una sola entidad::

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

Formato multi-entidad, con relaciones @ManyToOne entre ellas (layered, hexagonal
y clean)::

    {
        "project": "ventas",
        "entities": [
            {"entity": "Cliente", "fields": [...]},
            {"entity": "Pedido", "fields": [
                {"name": "id", "type": "int"},
                {"name": "cliente", "type": "reference", "references": "Cliente",
                 "required": true},
                ...
            ]}
        ]
    }

Un campo "reference" genera una columna "{name}_id", una relación @ManyToOne en la
entidad JPA y un "{name}Id" (Integer) en los DTOs (y, en hexagonal/clean, tambien
en el modelo de dominio: el dominio no tiene acceso a un repositorio). Quien
resuelve el ID contra el repositorio de la entidad referenciada es el service
(layered) o el adaptador de persistencia (hexagonal/clean), justo antes de
guardar. El lado referenciado recibe ademas un @OneToMany de solo lectura
(no expuesto en DTOs/dominio) y un filtro "?{name}Id=" en el listado de quien
referencia. "references" debe nombrar otra entidad del mismo "entities" (o la propia
entidad, para relaciones reflexivas como un arbol de categorias).
"""

import json
import re

from .parsing import (
    DefinitionError,
    normalize_base_package,
    normalize_endpoints,
    normalize_entity_name,
    parse_attributes_from_fields,
)

PROJECT_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


def _read_json(path):
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
        raise DefinitionError("El JSON debe ser un objeto.")
    return data


def is_multi_entity_document(path):
    """True si el JSON define varias entidades ('entities') en vez de una sola
    ('entity'/'fields'). No valida nada mas; generate_project_from_json usa esto
    solo para elegir que loader completo invocar despues."""
    return "entities" in _read_json(path)


def _shared_top_level(data, extra_allowed=()):
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

    unknown_top_level = set(data) - {"architecture", "package", "endpoints", *extra_allowed}
    if unknown_top_level:
        raise DefinitionError(
            f"Claves desconocidas en el JSON: {', '.join(sorted(unknown_top_level))}."
        )
    return architecture, base_package, endpoints


def load_schema(path):
    data = _read_json(path)

    entity_name = data.get("entity")
    if not isinstance(entity_name, str) or not entity_name.strip():
        raise DefinitionError("El JSON debe indicar 'entity' con el nombre de la entidad.")

    fields = data.get("fields")
    if not isinstance(fields, list) or not fields:
        raise DefinitionError("El JSON debe indicar 'fields' como una lista no vacía.")

    architecture, base_package, endpoints = _shared_top_level(data, extra_allowed={"entity", "fields"})

    attrs = parse_attributes_from_fields(fields)
    reference = next((attr for attr in attrs if attr["type"] == "reference"), None)
    if reference:
        raise DefinitionError(
            f"'{reference['name']}' usa type=reference, pero este fichero define una "
            "sola entidad. Las relaciones entre entidades exigen el formato "
            "multi-entidad: {\"entities\": [...]} (ver documentación)."
        )
    return entity_name, architecture, base_package, endpoints, attrs


def load_entities_schema(path):
    """Carga el formato multi-entidad. Devuelve
    (project_name, architecture, base_package, endpoints, entities) donde
    'entities' es [(entity_name, attrs), ...] en orden topológico: una entidad
    referenciada por otra siempre aparece antes que quien la referencia, para
    que su tabla/migracion exista primero."""
    data = _read_json(path)

    raw_entities = data.get("entities")
    if not isinstance(raw_entities, list) or not raw_entities:
        raise DefinitionError("'entities' debe ser una lista no vacía de entidades.")

    project = data.get("project")
    if project is not None:
        if not isinstance(project, str) or not PROJECT_NAME_PATTERN.fullmatch(project):
            raise DefinitionError(
                "'project' debe usar letras, números, '_' o '-', empezando por una letra."
            )

    architecture, base_package, endpoints = _shared_top_level(
        data, extra_allowed={"entities", "project"}
    )

    parsed = {}
    order = []
    for position, spec in enumerate(raw_entities, start=1):
        if not isinstance(spec, dict):
            raise DefinitionError(f"La entidad {position} de 'entities' debe ser un objeto JSON.")
        entity_name = spec.get("entity")
        if not isinstance(entity_name, str) or not entity_name.strip():
            raise DefinitionError(
                f"La entidad {position} de 'entities' debe indicar 'entity'."
            )
        entity_name = normalize_entity_name(entity_name)
        fields = spec.get("fields")
        if not isinstance(fields, list) or not fields:
            raise DefinitionError(f"La entidad '{entity_name}' debe indicar 'fields'.")
        unknown = set(spec) - {"entity", "fields"}
        if unknown:
            raise DefinitionError(
                f"Claves desconocidas en la entidad '{entity_name}': "
                f"{', '.join(sorted(unknown))}."
            )
        if entity_name in parsed:
            raise DefinitionError(f"La entidad '{entity_name}' está duplicada en 'entities'.")
        parsed[entity_name] = parse_attributes_from_fields(fields)
        order.append(entity_name)

    for entity_name, attrs in parsed.items():
        for attr in attrs:
            if attr["type"] != "reference":
                continue
            if attr["references"] not in parsed:
                raise DefinitionError(
                    f"'{entity_name}.{attr['name']}' referencia '{attr['references']}', "
                    "que no está definida en 'entities'."
                )

    project_name = project if project else order[0]
    return (
        project_name,
        architecture,
        base_package,
        endpoints,
        _topologically_ordered(order, parsed),
    )


def _topologically_ordered(order, parsed):
    """Kahn con desempate estable por el orden original del JSON. Los campos
    'reference' autorreferenciados (una entidad que se referencia a si misma,
    p.ej. un arbol de categorias) no cuentan como dependencia: la FK puede
    crearse en la misma CREATE TABLE que la propia tabla."""
    dependents = {name: set() for name in order}
    remaining_deps = {name: set() for name in order}
    for entity_name, attrs in parsed.items():
        for attr in attrs:
            if attr["type"] != "reference":
                continue
            referenced = attr["references"]
            if referenced == entity_name:
                continue
            remaining_deps[entity_name].add(referenced)
            dependents[referenced].add(entity_name)

    result = []
    available = [name for name in order if not remaining_deps[name]]
    visited = set()
    while available:
        available.sort(key=order.index)
        current = available.pop(0)
        if current in visited:
            continue
        visited.add(current)
        result.append(current)
        for dependent in dependents[current]:
            remaining_deps[dependent].discard(current)
            if not remaining_deps[dependent] and dependent not in visited:
                available.append(dependent)

    if len(result) != len(order):
        cyclic = sorted(set(order) - visited)
        raise DefinitionError(
            "Dependencias circulares entre entidades vía 'reference': "
            f"{', '.join(cyclic)}."
        )
    return [(name, parsed[name]) for name in result]
