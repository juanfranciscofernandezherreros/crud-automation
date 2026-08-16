"""Conversión y validación de las entradas del generador."""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from .types import JAVA_TYPES, SQL_TYPES, STRING_LIKE_TYPES


ATTRIBUTE_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
ENTITY_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
GROUP_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
NUMERIC_TYPES = {"int", "float", "double", "decimal"}
BOOLEAN_LITERALS = {"true", "false"}
AUDIT_FIELD_NAMES = {"creado_en", "created_at", "actualizado_en", "updated_at"}
MAX_DECIMAL_PRECISION = 38

# El valor de una regla nunca puede contener ':' (separa nombre:tipo:regla) ni ','
# (separa atributos), así que un default datetime usa hora sin separadores: HHMMSS.
DATETIME_DEFAULT_PATTERN = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})(?:T(?P<hour>\d{2})(?P<minute>\d{2})(?P<second>\d{2})?)?$"
)


def expand_datetime_default(value):
    """Convierte 'AAAA-MM-DDTHHMMSS' (sin ':') al ISO con ':' que entienden Java y SQL."""
    match = DATETIME_DEFAULT_PATTERN.fullmatch(value)
    date_part = match.group("date")
    hour = match.group("hour")
    if hour is None:
        return f"{date_part}T00:00:00"
    minute = match.group("minute")
    second = match.group("second") or "00"
    return f"{date_part}T{hour}:{minute}:{second}"


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


PACKAGE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:\.[a-z][a-z0-9]*)*$")


def normalize_base_package(value):
    value = value.strip()
    if not value:
        raise DefinitionError("'package' no puede estar vacío.")
    if not PACKAGE_PATTERN.fullmatch(value):
        raise DefinitionError(
            f"'package' no válido: '{value}'. Usa minúsculas separadas por puntos, "
            "como 'com.miempresa.proyecto'."
        )
    return value


VALID_ENDPOINTS = ("list", "get", "create", "update", "patch", "delete")
DEFAULT_ENDPOINTS = VALID_ENDPOINTS


def normalize_endpoints(values):
    if not isinstance(values, list) or not values:
        raise DefinitionError(
            "'endpoints' debe ser una lista no vacía con alguno de: "
            f"{', '.join(VALID_ENDPOINTS)}."
        )
    normalized = []
    seen = set()
    for value in values:
        if not isinstance(value, str):
            raise DefinitionError(f"Cada endpoint debe ser texto: '{value}'.")
        endpoint = value.strip().lower()
        if endpoint not in VALID_ENDPOINTS:
            raise DefinitionError(
                f"Endpoint desconocido '{value}'. Opciones: {', '.join(VALID_ENDPOINTS)}."
            )
        if endpoint in seen:
            raise DefinitionError(f"El endpoint '{endpoint}' está duplicado.")
        seen.add(endpoint)
        normalized.append(endpoint)
    return normalized


VALID_HTTP_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")

# Cada segmento del path es un literal (letras/numeros/'_'/'-') o el placeholder
# literal '{id}' -- el unico path variable que el resto del generador sabe
# resolver (@PathVariable Integer id, igual que get/update/patch/delete).
CUSTOM_ENDPOINT_PATH_PATTERN = re.compile(
    r"^/(?:\{id\}|[a-zA-Z0-9_-]+)(?:/(?:\{id\}|[a-zA-Z0-9_-]+))*$"
)

_CUSTOM_ENDPOINT_FIELD_KEYS = {"name", "type"}
_CUSTOM_ENDPOINT_KEYS = {"name", "method", "path", "request", "response"}


def normalize_http_method(value):
    method = value.strip().upper() if isinstance(value, str) else value
    if method not in VALID_HTTP_METHODS:
        raise DefinitionError(
            f"'method' desconocido '{value}'. Opciones: {', '.join(VALID_HTTP_METHODS)}."
        )
    return method


def parse_endpoint_fields(field_specs, label):
    """Campos de 'request'/'response' de un custom_endpoint: solo nombre y
    tipo, sin reglas de validacion (a diferencia de parse_attributes_from_fields,
    que tambien acepta required/unique/default/etc). Devuelve dicts con la
    misma forma minima que consume fields.generate_dto_fields."""
    if not isinstance(field_specs, list) or not field_specs:
        raise DefinitionError(f"'{label}' debe ser una lista no vacía de campos.")

    attrs = []
    seen = set()
    for position, field in enumerate(field_specs, start=1):
        if not isinstance(field, dict):
            raise DefinitionError(f"El campo {position} de '{label}' debe ser un objeto JSON.")

        name = field.get("name")
        if not isinstance(name, str) or not ATTRIBUTE_NAME_PATTERN.fullmatch(name):
            raise DefinitionError(
                f"Nombre de campo no válido en '{label}' ({position}): '{name}'. "
                "Usa lower_snake_case."
            )
        if name in seen:
            raise DefinitionError(f"El campo '{name}' está duplicado en '{label}'.")

        type_name = field.get("type")
        if type_name not in JAVA_TYPES:
            raise DefinitionError(
                f"Tipo desconocido '{type_name}' para '{name}' en '{label}'. "
                f"Tipos admitidos: {', '.join(JAVA_TYPES)}."
            )

        unknown_keys = set(field) - _CUSTOM_ENDPOINT_FIELD_KEYS
        if unknown_keys:
            raise DefinitionError(
                f"Claves desconocidas en '{name}' ({label}): {', '.join(sorted(unknown_keys))}."
            )

        seen.add(name)
        attrs.append({
            "name": name,
            "camel_name": to_camel_case(name),
            "type": type_name,
            "java_type": JAVA_TYPES[type_name],
            "is_id": False,
            "is_audit": False,
        })
    return attrs


def normalize_custom_endpoints(raw_list):
    """'custom_endpoints' de una entidad: endpoints de negocio ajenos al CRUD
    fijo (list/get/create/update/patch/delete), declarados con su path, metodo
    HTTP y forma de request/response. El generador scaffolds el DTO, el
    controller y un stub de servicio que lanza UnsupportedOperationException
    -- no puede inventar la logica de negocio."""
    if not isinstance(raw_list, list) or not raw_list:
        raise DefinitionError("'custom_endpoints' debe ser una lista no vacía si se indica.")

    endpoints = []
    seen_names = set()
    for position, spec in enumerate(raw_list, start=1):
        if not isinstance(spec, dict):
            raise DefinitionError(
                f"El endpoint {position} de 'custom_endpoints' debe ser un objeto JSON."
            )

        name = spec.get("name")
        if not isinstance(name, str) or not ATTRIBUTE_NAME_PATTERN.fullmatch(name):
            raise DefinitionError(
                f"Nombre de endpoint no válido en 'custom_endpoints' ({position}): '{name}'. "
                "Usa lower_snake_case."
            )
        if name in seen_names:
            raise DefinitionError(f"El endpoint '{name}' está duplicado en 'custom_endpoints'.")

        method = normalize_http_method(spec.get("method"))

        path = spec.get("path")
        if not isinstance(path, str) or not CUSTOM_ENDPOINT_PATH_PATTERN.fullmatch(path):
            raise DefinitionError(
                f"'path' no válido en el endpoint '{name}': '{path}'. Debe empezar por '/' y "
                "usar solo letras, números, '_', '-' o el segmento literal '{id}'."
            )

        request_fields = spec.get("request")
        request_attrs = (
            parse_endpoint_fields(request_fields, f"{name}.request")
            if request_fields is not None else []
        )

        response_fields = spec.get("response")
        response_attrs = (
            parse_endpoint_fields(response_fields, f"{name}.response")
            if response_fields is not None else []
        )

        unknown_keys = set(spec) - _CUSTOM_ENDPOINT_KEYS
        if unknown_keys:
            raise DefinitionError(
                f"Claves desconocidas en el endpoint '{name}': {', '.join(sorted(unknown_keys))}."
            )

        camel_name = to_camel_case(name)
        seen_names.add(name)
        endpoints.append({
            "name": name,
            "camel_name": camel_name,
            "pascal_name": camel_name[0].upper() + camel_name[1:],
            "method": method,
            "path": path,
            "has_id": "{id}" in path,
            "request_fields": request_attrs,
            "response_fields": response_attrs,
        })
    return endpoints


def _validate_default_literal(value, type_name, name):
    if type_name in STRING_LIKE_TYPES:
        return value
    if type_name == "boolean":
        normalized = value.lower()
        if normalized not in BOOLEAN_LITERALS:
            raise DefinitionError(
                f"El valor por defecto de '{name}' debe ser 'true' o 'false'."
            )
        return normalized
    if type_name in NUMERIC_TYPES:
        try:
            numeric_value = Decimal(value)
        except InvalidOperation as error:
            raise DefinitionError(
                f"El valor por defecto de '{name}' debe ser numérico."
            ) from error
        if not numeric_value.is_finite():
            raise DefinitionError(f"El valor por defecto de '{name}' debe ser finito.")
        if type_name == "int" and numeric_value != int(numeric_value):
            raise DefinitionError(f"El valor por defecto de '{name}' debe ser entero.")
        return value
    if type_name == "date":
        try:
            date.fromisoformat(value)
        except ValueError as error:
            raise DefinitionError(
                f"El valor por defecto de '{name}' debe ser una fecha AAAA-MM-DD válida."
            ) from error
        return value
    if type_name == "datetime":
        if DATETIME_DEFAULT_PATTERN.fullmatch(value):
            try:
                datetime.fromisoformat(expand_datetime_default(value))
            except ValueError as error:
                raise DefinitionError(
                    f"El valor por defecto de '{name}' no es una fecha/hora válida."
                ) from error
            return value
        # El DSL de texto solo puede llegar aquí en formato compacto (arriba), porque
        # ':' separa reglas en "nombre:tipo:regla". El JSON no tiene esa restricción,
        # así que también se acepta un ISO 8601 normal y se normaliza al formato
        # compacto que ya usan expand_datetime_default() y la generación SQL/Java.
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as error:
            raise DefinitionError(
                f"El valor por defecto de '{name}' debe tener formato AAAA-MM-DD, "
                "AAAA-MM-DDTHH:MM[:SS] (JSON) o AAAA-MM-DDTHHMMSS sin ':' (DSL de texto)."
            ) from error
        return parsed.strftime("%Y-%m-%dT%H%M%S")
    raise DefinitionError(f"'default' no es compatible con '{type_name}'.")


def parse_validations(raw_validations, name, type_name):
    validations = {}
    for raw_validation in raw_validations:
        validation = raw_validation.strip()
        if not validation:
            raise DefinitionError(f"Hay una validación vacía en '{name}'.")

        if "=" in validation:
            rule, value = validation.split("=", maxsplit=1)
            rule = rule.strip().lower()
            value = value.strip()
            if rule not in {"min", "max", "default", "composite_unique", "precision", "scale"}:
                raise DefinitionError(f"Validación desconocida: '{validation}'.")
            if rule in validations:
                raise DefinitionError(f"La validación '{rule}' está duplicada en '{name}'.")
            if not value:
                raise DefinitionError(f"El valor de '{rule}' en '{name}' no puede estar vacío.")

            if rule == "default":
                validations[rule] = _validate_default_literal(value, type_name, name)
                continue

            if rule == "composite_unique":
                if not GROUP_NAME_PATTERN.fullmatch(value.lower()):
                    raise DefinitionError(
                        f"El grupo '{value}' de '{name}' debe usar lower_snake_case."
                    )
                validations[rule] = value.lower()
                continue

            if rule in {"precision", "scale"}:
                if type_name != "decimal":
                    raise DefinitionError(
                        f"'{rule}' solo se puede aplicar a 'decimal', no a '{type_name}' ('{name}')."
                    )
                if not value.isdigit():
                    raise DefinitionError(
                        f"'{rule}' de '{name}' debe ser un entero no negativo."
                    )
                validations[rule] = value
                continue

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
            if type_name in STRING_LIKE_TYPES and numeric_value != int(numeric_value):
                raise DefinitionError(
                    f"El límite '{rule}' de un {type_name} debe ser un entero."
                )
            if type_name in STRING_LIKE_TYPES and numeric_value < 0:
                raise DefinitionError(
                    f"El límite '{rule}' de un {type_name} no puede ser negativo."
                )
            if type_name not in NUMERIC_TYPES | STRING_LIKE_TYPES:
                raise DefinitionError(
                    f"La validación '{rule}' no es compatible con '{type_name}'."
                )
            validations[rule] = value
            continue

        validation = validation.lower()
        if validation not in {"required", "not_blank", "positive", "unique", "index"}:
            raise DefinitionError(f"Validación desconocida: '{validation}'.")
        if validation in validations:
            raise DefinitionError(
                f"La validación '{validation}' está duplicada en '{name}'."
            )
        if validation == "not_blank" and type_name not in STRING_LIKE_TYPES:
            raise DefinitionError("'not_blank' solo se puede aplicar a strings o text.")
        if validation == "positive" and type_name not in NUMERIC_TYPES:
            raise DefinitionError("'positive' solo se puede aplicar a números.")
        validations[validation] = True

    _apply_coherence_checks(validations, type_name, name)
    return validations


def _apply_coherence_checks(validations, type_name, name):
    """Reglas que dependen de varias validaciones a la vez. Compartido por el DSL de
    texto (parse_validations) y el de JSON (_build_validations_from_field)."""
    if "min" in validations and "max" in validations:
        if Decimal(validations["min"]) > Decimal(validations["max"]):
            raise DefinitionError(f"El mínimo de '{name}' no puede superar su máximo.")
    if validations.get("not_blank") and Decimal(validations.get("max", "1")) < 1:
        raise DefinitionError(f"'{name}' no puede ser no vacío y tener máximo cero.")
    if validations.get("positive") and Decimal(validations.get("max", "1")) <= 0:
        raise DefinitionError(f"'{name}' no puede ser positivo con ese máximo.")

    if "default" in validations:
        default_value = validations["default"]
        if type_name in NUMERIC_TYPES:
            default_numeric = Decimal(default_value)
            if validations.get("positive") and default_numeric <= 0:
                raise DefinitionError(
                    f"El valor por defecto de '{name}' debe ser positivo."
                )
            if "min" in validations and default_numeric < Decimal(validations["min"]):
                raise DefinitionError(
                    f"El valor por defecto de '{name}' no puede ser menor que su mínimo."
                )
            if "max" in validations and default_numeric > Decimal(validations["max"]):
                raise DefinitionError(
                    f"El valor por defecto de '{name}' no puede superar su máximo."
                )
        if type_name in STRING_LIKE_TYPES:
            length = len(default_value)
            if "min" in validations and length < int(validations["min"]):
                raise DefinitionError(
                    f"El valor por defecto de '{name}' es más corto que su mínimo."
                )
            if "max" in validations and length > int(validations["max"]):
                raise DefinitionError(
                    f"El valor por defecto de '{name}' supera su longitud máxima."
                )

    if ("precision" in validations) != ("scale" in validations):
        raise DefinitionError(
            f"'{name}' debe indicar 'precision' y 'scale' juntos, o ninguno."
        )
    if "precision" in validations:
        precision = int(validations["precision"])
        scale = int(validations["scale"])
        if not 1 <= precision <= MAX_DECIMAL_PRECISION:
            raise DefinitionError(
                f"'precision' de '{name}' debe estar entre 1 y {MAX_DECIMAL_PRECISION}."
            )
        if not 0 <= scale <= precision:
            raise DefinitionError(
                f"'scale' de '{name}' debe estar entre 0 y su precisión ({precision})."
            )


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
        seen_names.add(name)
        attrs.append(_finalize_attribute(name, type_name, validations))

    _validate_attrs(attrs)
    return attrs


def _finalize_attribute(name, type_name, validations):
    """Construye el dict de atributo final a partir de nombre/tipo/reglas ya validadas.
    Usado tanto por el DSL de texto (parse_attributes) como por JSON
    (parse_attributes_from_fields)."""
    precision = validations.pop("precision", None)
    scale = validations.pop("scale", None)
    enum_values = validations.pop("values", None)
    references = validations.pop("references", None)
    is_audit = name in AUDIT_FIELD_NAMES
    if validations and (name == "id" or is_audit):
        raise DefinitionError(
            f"El atributo gestionado '{name}' no admite validaciones de entrada."
        )

    camel_name = to_camel_case(name)
    sql_column = name
    if type_name == "enum":
        enum_class = camel_name[0].upper() + camel_name[1:]
        java_type = enum_class
        sql_type = f"VARCHAR({max(len(value) for value in enum_values)})"
    elif type_name == "reference":
        enum_class = None
        java_type = references
        sql_type = "INT"
        sql_column = f"{name}_id"
    else:
        enum_class = None
        java_type = JAVA_TYPES[type_name]
        sql_type = SQL_TYPES[type_name]
        if precision is not None:
            sql_type = f"DECIMAL({precision}, {scale})"

    return {
        "name": name,
        "camel_name": camel_name,
        "java_type": java_type,
        "sql_type": sql_type,
        "sql_column": sql_column,
        "type": type_name,
        "precision": int(precision) if precision is not None else None,
        "scale": int(scale) if scale is not None else None,
        "validations": validations,
        "is_id": name.lower() == "id",
        "is_date": type_name in ["datetime", "date"],
        "is_audit": is_audit,
        "enum_values": enum_values,
        "enum_class": enum_class,
        "references": references,
        "reference_table": f"{references.lower()}s" if references else None,
    }


def _validate_attrs(attrs):
    id_count = sum(attr["is_id"] for attr in attrs)
    if id_count == 0:
        raise DefinitionError("La definición debe incluir un atributo 'id'.")
    if id_count > 1:
        raise DefinitionError("La definición solo puede incluir un atributo 'id'.")

    _validate_composite_unique_groups(attrs)


# ---------------------------------------------------------------------------
# Definición de entidad vía JSON: mismo modelo de atributos, sin las
# restricciones de caracteres del DSL de texto ('default' puede llevar ':' o ',').
# ---------------------------------------------------------------------------

_JSON_FLAG_KEYS = ("required", "not_blank", "positive", "unique", "index")
_JSON_NUMERIC_RULE_KEYS = ("min", "max")
_JSON_KNOWN_KEYS = {
    "name",
    "type",
    *_JSON_FLAG_KEYS,
    *_JSON_NUMERIC_RULE_KEYS,
    "default",
    "precision",
    "scale",
    "composite_unique",
    "values",
    "references",
}

ENUM_VALUE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")


def _build_enum_values(field, name):
    values = field.get("values")
    if not isinstance(values, list) or len(values) < 2:
        raise DefinitionError(
            f"'enum' en '{name}' necesita 'values' con al menos dos opciones."
        )
    normalized = []
    seen = set()
    for value in values:
        if not isinstance(value, str) or not ENUM_VALUE_PATTERN.fullmatch(value):
            raise DefinitionError(
                f"Cada valor de 'values' en '{name}' debe ser MAYUSCULAS_CON_GUION_BAJO "
                f"empezando por letra: '{value}'."
            )
        if value in seen:
            raise DefinitionError(f"El valor '{value}' está duplicado en '{name}'.")
        seen.add(value)
        normalized.append(value)
    return normalized


def _build_validations_from_field(field, name, type_name):
    validations = {}

    if type_name == "enum":
        unsupported = {"min", "max", "positive", "not_blank", "precision", "scale"} & set(field)
        if unsupported:
            raise DefinitionError(
                f"{', '.join(sorted(unsupported))} no se aplican a 'enum' ('{name}')."
            )
        validations["values"] = _build_enum_values(field, name)
        if field.get("required"):
            validations["required"] = True
        if field.get("unique"):
            validations["unique"] = True
        if field.get("index"):
            validations["index"] = True
        if "composite_unique" in field:
            group = field["composite_unique"]
            if not isinstance(group, str) or not GROUP_NAME_PATTERN.fullmatch(group.lower()):
                raise DefinitionError(
                    f"El grupo '{group}' de '{name}' debe usar lower_snake_case."
                )
            validations["composite_unique"] = group.lower()
        if "default" in field:
            default_value = str(field["default"])
            if default_value not in validations["values"]:
                raise DefinitionError(
                    f"El valor por defecto de '{name}' debe ser uno de "
                    f"{validations['values']}."
                )
            validations["default"] = default_value
        return validations

    if type_name == "reference":
        unsupported = {
            "min", "max", "positive", "not_blank", "precision", "scale", "default",
        } & set(field)
        if unsupported:
            raise DefinitionError(
                f"{', '.join(sorted(unsupported))} no se aplican a 'reference' ('{name}')."
            )
        references = field.get("references")
        if not isinstance(references, str) or not ENTITY_NAME_PATTERN.fullmatch(references):
            raise DefinitionError(
                f"'reference' en '{name}' necesita 'references' con el nombre de "
                "otra entidad definida en el mismo fichero."
            )
        validations["references"] = references[0].upper() + references[1:]
        if field.get("required"):
            validations["required"] = True
        if field.get("unique"):
            validations["unique"] = True
        if field.get("index"):
            validations["index"] = True
        if "composite_unique" in field:
            group = field["composite_unique"]
            if not isinstance(group, str) or not GROUP_NAME_PATTERN.fullmatch(group.lower()):
                raise DefinitionError(
                    f"El grupo '{group}' de '{name}' debe usar lower_snake_case."
                )
            validations["composite_unique"] = group.lower()
        return validations

    for key in _JSON_FLAG_KEYS:
        if not field.get(key):
            continue
        if key == "not_blank" and type_name not in STRING_LIKE_TYPES:
            raise DefinitionError(
                f"'not_blank' solo se puede aplicar a strings o text ('{name}')."
            )
        if key == "positive" and type_name not in NUMERIC_TYPES:
            raise DefinitionError(f"'positive' solo se puede aplicar a números ('{name}').")
        validations[key] = True

    for key in _JSON_NUMERIC_RULE_KEYS:
        if key not in field:
            continue
        raw_value = field[key]
        try:
            numeric_value = Decimal(str(raw_value))
        except InvalidOperation as error:
            raise DefinitionError(
                f"El valor de '{key}' en '{name}' debe ser numérico."
            ) from error
        if not numeric_value.is_finite():
            raise DefinitionError(f"El valor de '{key}' en '{name}' debe ser finito.")
        if type_name in STRING_LIKE_TYPES and numeric_value != int(numeric_value):
            raise DefinitionError(
                f"El límite '{key}' de un {type_name} debe ser un entero ('{name}')."
            )
        if type_name in STRING_LIKE_TYPES and numeric_value < 0:
            raise DefinitionError(
                f"El límite '{key}' de un {type_name} no puede ser negativo ('{name}')."
            )
        if type_name not in NUMERIC_TYPES | STRING_LIKE_TYPES:
            raise DefinitionError(
                f"La validación '{key}' no es compatible con '{type_name}' ('{name}')."
            )
        validations[key] = str(raw_value)

    if "precision" in field or "scale" in field:
        if type_name != "decimal":
            raise DefinitionError(
                f"'precision'/'scale' solo se pueden aplicar a 'decimal', "
                f"no a '{type_name}' ('{name}')."
            )
        if ("precision" in field) != ("scale" in field):
            raise DefinitionError(
                f"'{name}' debe indicar 'precision' y 'scale' juntos, o ninguno."
            )
        validations["precision"] = str(field["precision"])
        validations["scale"] = str(field["scale"])

    if "composite_unique" in field:
        group = field["composite_unique"]
        if not isinstance(group, str) or not GROUP_NAME_PATTERN.fullmatch(group.lower()):
            raise DefinitionError(
                f"El grupo '{group}' de '{name}' debe usar lower_snake_case."
            )
        validations["composite_unique"] = group.lower()

    if "default" in field:
        validations["default"] = _validate_default_literal(
            str(field["default"]), type_name, name
        )

    _apply_coherence_checks(validations, type_name, name)
    return validations


def parse_attributes_from_fields(field_specs):
    """Igual que parse_attributes(), pero a partir de una lista de dicts (JSON) en
    vez de la cadena 'nombre:tipo:regla,...'. No hay restricción de caracteres en
    los valores porque nunca se reconstruyen como texto delimitado por ':'/','."""
    if not field_specs:
        raise DefinitionError("Debes indicar al menos un campo.")

    attrs = []
    seen_names = set()
    for position, field in enumerate(field_specs, start=1):
        if not isinstance(field, dict):
            raise DefinitionError(f"El campo {position} debe ser un objeto JSON.")

        name = field.get("name")
        if not isinstance(name, str) or not ATTRIBUTE_NAME_PATTERN.fullmatch(name):
            raise DefinitionError(
                f"Nombre de atributo no válido en el campo {position}: '{name}'. "
                "Usa lower_snake_case."
            )
        if name in seen_names:
            raise DefinitionError(f"El atributo '{name}' está duplicado.")

        type_name = field.get("type")
        if type_name not in JAVA_TYPES and type_name not in ("enum", "reference"):
            accepted_types = ", ".join((*JAVA_TYPES, "enum", "reference"))
            raise DefinitionError(
                f"Tipo desconocido '{type_name}' para '{name}'. "
                f"Tipos admitidos: {accepted_types}."
            )

        unknown_keys = set(field) - _JSON_KNOWN_KEYS
        if unknown_keys:
            raise DefinitionError(
                f"Claves desconocidas en '{name}': {', '.join(sorted(unknown_keys))}."
            )

        validations = _build_validations_from_field(field, name, type_name)
        seen_names.add(name)
        attrs.append(_finalize_attribute(name, type_name, validations))

    _validate_attrs(attrs)
    return attrs


def _validate_composite_unique_groups(attrs):
    groups = {}
    for attr in attrs:
        group = attr["validations"].get("composite_unique")
        if group:
            groups.setdefault(group, []).append(attr["name"])
    for group, members in groups.items():
        if len(members) < 2:
            raise DefinitionError(
                f"El grupo de unicidad compuesta '{group}' necesita al menos dos "
                "campos con 'composite_unique="
                f"{group}'."
            )
