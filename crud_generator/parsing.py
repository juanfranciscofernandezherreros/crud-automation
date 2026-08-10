"""Conversión y validación de las entradas del generador."""

import re
from decimal import Decimal, InvalidOperation

from .types import JAVA_TYPES, SQL_TYPES


ATTRIBUTE_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
ENTITY_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
NUMERIC_TYPES = {"int", "float", "double", "decimal"}
AUDIT_FIELD_NAMES = {"creado_en", "created_at", "actualizado_en", "updated_at"}


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


def parse_validations(raw_validations, name, type_name):
    validations = {}
    for raw_validation in raw_validations:
        validation = raw_validation.strip().lower()
        if not validation:
            raise DefinitionError(f"Hay una validación vacía en '{name}'.")

        if "=" in validation:
            rule, value = validation.split("=", maxsplit=1)
            if rule not in {"min", "max"}:
                raise DefinitionError(f"Validación desconocida: '{validation}'.")
            if rule in validations:
                raise DefinitionError(f"La validación '{rule}' está duplicada en '{name}'.")
            try:
                numeric_value = Decimal(value)
            except InvalidOperation as error:
                raise DefinitionError(
                    f"El valor de '{rule}' en '{name}' debe ser numérico."
                ) from error
            if not numeric_value.is_finite():
                raise DefinitionError(
                    f"El valor de '{rule}' en '{name}' debe ser finito."
                )
            if type_name == "string" and numeric_value != int(numeric_value):
                raise DefinitionError(
                    f"El límite '{rule}' de un string debe ser un entero."
                )
            if type_name == "string" and numeric_value < 0:
                raise DefinitionError(
                    f"El límite '{rule}' de un string no puede ser negativo."
                )
            if type_name not in NUMERIC_TYPES | {"string"}:
                raise DefinitionError(
                    f"La validación '{rule}' no es compatible con '{type_name}'."
                )
            validations[rule] = value
            continue

        if validation not in {"required", "not_blank", "positive", "unique", "index"}:
            raise DefinitionError(f"Validación desconocida: '{validation}'.")
        if validation in validations:
            raise DefinitionError(
                f"La validación '{validation}' está duplicada en '{name}'."
            )
        if validation == "not_blank" and type_name != "string":
            raise DefinitionError("'not_blank' solo se puede aplicar a strings.")
        if validation == "positive" and type_name not in NUMERIC_TYPES:
            raise DefinitionError("'positive' solo se puede aplicar a números.")
        validations[validation] = True

    if "min" in validations and "max" in validations:
        if Decimal(validations["min"]) > Decimal(validations["max"]):
            raise DefinitionError(f"El mínimo de '{name}' no puede superar su máximo.")
    if validations.get("not_blank") and Decimal(validations.get("max", "1")) < 1:
        raise DefinitionError(f"'{name}' no puede ser no vacío y tener máximo cero.")
    if validations.get("positive") and Decimal(validations.get("max", "1")) <= 0:
        raise DefinitionError(f"'{name}' no puede ser positivo con ese máximo.")
    return validations


def parse_attributes(attrs_str):
    if not attrs_str.strip():
        raise DefinitionError("Debes indicar al menos un atributo.")

    attrs = []
    seen_names = set()
    for position, raw_attr in enumerate(attrs_str.split(","), start=1):
        attr = raw_attr.strip()
        if not attr:
            raise DefinitionError(f"El atributo {position} está vacío.")

        parts = attr.split(":")
        if len(parts) < 2:
            raise DefinitionError(
                f"Formato no válido en el atributo {position}: '{attr}'. "
                "Usa nombre:tipo[:validación]."
            )

        name = parts[0].strip()
        type_name = parts[1].strip().lower()
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

        validations = parse_validations(parts[2:], name, type_name)
        is_audit = name in AUDIT_FIELD_NAMES
        if validations and (name == "id" or is_audit):
            raise DefinitionError(
                f"El atributo gestionado '{name}' no admite validaciones de entrada."
            )

        seen_names.add(name)
        attrs.append(
            {
                "name": name,
                "camel_name": to_camel_case(name),
                "java_type": JAVA_TYPES[type_name],
                "sql_type": SQL_TYPES[type_name],
                "type": type_name,
                "validations": validations,
                "is_id": name.lower() == "id",
                "is_date": type_name in ["datetime", "date"],
                "is_audit": is_audit,
            }
        )

    id_count = sum(attr["is_id"] for attr in attrs)
    if id_count == 0:
        raise DefinitionError("La definición debe incluir un atributo 'id'.")
    if id_count > 1:
        raise DefinitionError("La definición solo puede incluir un atributo 'id'.")

    return attrs
