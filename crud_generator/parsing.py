"""Conversión y validación de las entradas del generador."""

import re

from .types import JAVA_TYPES, SQL_TYPES


ATTRIBUTE_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
ENTITY_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")


class DefinitionError(ValueError):
    """Indica que la definición solicitada no puede generar un CRUD válido."""


def normalize_entity_name(entity_name):
    entity_name = entity_name.strip()
    if not entity_name:
        raise DefinitionError("El nombre de la entidad no puede estar vacío.")
    if not ENTITY_NAME_PATTERN.fullmatch(entity_name):
        raise DefinitionError(
            f"Nombre de entidad no válido: '{entity_name}'. "
            "Usa únicamente letras y números, comenzando por una letra."
        )
    return entity_name[0].upper() + entity_name[1:]


def to_camel_case(snake_str):
    components = snake_str.split("_")
    return components[0] + "".join(component.title() for component in components[1:])


def parse_attributes(attrs_str):
    if not attrs_str.strip():
        raise DefinitionError("Debes indicar al menos un atributo.")

    attrs = []
    seen_names = set()
    for position, raw_attr in enumerate(attrs_str.split(","), start=1):
        attr = raw_attr.strip()
        if not attr:
            raise DefinitionError(f"El atributo {position} está vacío.")

        name_type = attr.split(":")
        if len(name_type) != 2:
            raise DefinitionError(
                f"Formato no válido en el atributo {position}: '{attr}'. "
                "Usa nombre:tipo."
            )

        name = name_type[0].strip()
        type_name = name_type[1].strip().lower()
        if not ATTRIBUTE_NAME_PATTERN.fullmatch(name):
            raise DefinitionError(
                f"Nombre de atributo no válido: '{name}'. Usa lower_snake_case."
            )
        if name in seen_names:
            raise DefinitionError(f"El atributo '{name}' está duplicado.")
        if type_name not in JAVA_TYPES:
            accepted_types = ", ".join(JAVA_TYPES)
            raise DefinitionError(
                f"Tipo desconocido '{type_name}' para '{name}'. "
                f"Tipos admitidos: {accepted_types}."
            )

        seen_names.add(name)
        attrs.append(
            {
                "name": name,
                "camel_name": to_camel_case(name),
                "java_type": JAVA_TYPES[type_name],
                "sql_type": SQL_TYPES[type_name],
                "is_id": name.lower() == "id",
                "is_date": type_name in ["datetime", "date"],
            }
        )

    id_count = sum(attr["is_id"] for attr in attrs)
    if id_count == 0:
        raise DefinitionError("La definición debe incluir un atributo 'id'.")
    if id_count > 1:
        raise DefinitionError("La definición solo puede incluir un atributo 'id'.")

    return attrs
