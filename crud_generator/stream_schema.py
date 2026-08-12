"""Carga y validación de una definición de stream Kafka (formato usado por
'python generate_crud.py --stream <fichero>').

No es un DSL general para topologías Kafka Streams arbitrarias: generaliza un
patrón concreto y ya probado — filtrar un topic de entrada por un umbral
numérico opcional, reagrupar por una clave, sumar un campo numérico con estado
(KTable en RocksDB) y unir el stream original con esa tabla para producir un
evento enriquecido con el total acumulado — parametrizando topics, nombres de
evento, campos y tipos. Operaciones no cubiertas por este patrón (windowing,
branch, joins entre streams, múltiples agregaciones) quedan fuera.

"processing" es opcional en su totalidad. Sin ella (o sin
"group_by_field"/"aggregate_field"/"aggregate_as", que van juntos o ninguno),
el stream generado es un simple paso ("passthrough"): lee el topic de
entrada y reescribe cada evento, sin cambios, en el topic de salida — sin
estado, sin KTable, sin join. "filter_field"/"filter_operator"/"filter_value"
siguen siendo independientes y aplican igual con o sin agregación.

Formato (con agregación)::

    {
        "project": "sales-streams",
        "package": "com.example.sales",
        "input": {
            "topic": "orders-topic1",
            "event": "Order",
            "fields": [
                {"name": "order_id", "type": "string"},
                {"name": "customer_id", "type": "string"},
                {"name": "amount", "type": "double"}
            ]
        },
        "output": {
            "topic": "total-sales-topic1",
            "event": "OrderWithTotal"
        },
        "processing": {
            "group_by_field": "customer_id",
            "aggregate_field": "amount",
            "aggregate_as": "total_amount",
            "filter_field": "amount",
            "filter_operator": ">",
            "filter_value": 10
        }
    }

Formato (passthrough, sin "processing")::

    {
        "project": "crypto-relay",
        "package": "com.example.crypto",
        "input": {"topic": "crypto-prices-in", "event": "CryptoPrice", "fields": [...]},
        "output": {"topic": "crypto-prices-out", "event": "CryptoPriceRelayed"}
    }

"filter_field"/"filter_operator"/"filter_value" son opcionales (juntos, o
ninguno): sin ellos no se filtra nada. "aggregate_field" debe ser "double" en
esta primera versión (es el tipo que usa el acumulador y el Serde del store,
igual que en el proyecto de referencia).
"""

import json
import re

from .parsing import ATTRIBUTE_NAME_PATTERN, DefinitionError, ENTITY_NAME_PATTERN, to_camel_case

STREAM_JAVA_TYPES = {
    "string": "String",
    "int": "Integer",
    "long": "Long",
    "double": "Double",
    "boolean": "Boolean",
}

NUMERIC_STREAM_TYPES = {"int", "long", "double"}

FILTER_OPERATORS = (">", ">=", "<", "<=", "==", "!=")

PROJECT_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
TOPIC_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            raw = handle.read()
    except OSError as error:
        raise DefinitionError(f"No se pudo leer el fichero JSON '{path}': {error}.") from error
    try:
        return json.loads(raw)
    except json.JSONDecodeError as error:
        raise DefinitionError(f"El fichero JSON '{path}' no es válido: {error}.") from error


def _require_dict(value, name):
    if not isinstance(value, dict):
        raise DefinitionError(f"'{name}' debe ser un objeto JSON.")
    return value


def _require_str(value, name):
    if not isinstance(value, str) or not value.strip():
        raise DefinitionError(f"'{name}' debe ser un texto no vacío.")
    return value


def _parse_event_fields(fields, owner):
    if not isinstance(fields, list) or not fields:
        raise DefinitionError(f"'{owner}.fields' debe ser una lista no vacía.")
    parsed = []
    seen = set()
    for position, field in enumerate(fields, start=1):
        if not isinstance(field, dict):
            raise DefinitionError(f"El campo {position} de '{owner}' debe ser un objeto JSON.")
        name = field.get("name")
        if not isinstance(name, str) or not ATTRIBUTE_NAME_PATTERN.fullmatch(name):
            raise DefinitionError(
                f"Nombre de campo no válido en '{owner}': '{name}'. Usa lower_snake_case."
            )
        if name in seen:
            raise DefinitionError(f"El campo '{name}' está duplicado en '{owner}'.")
        type_name = field.get("type")
        if type_name not in STREAM_JAVA_TYPES:
            accepted = ", ".join(STREAM_JAVA_TYPES)
            raise DefinitionError(
                f"Tipo desconocido '{type_name}' para '{owner}.{name}'. Tipos admitidos: {accepted}."
            )
        unknown = set(field) - {"name", "type"}
        if unknown:
            raise DefinitionError(
                f"Claves desconocidas en '{owner}.{name}': {', '.join(sorted(unknown))}."
            )
        seen.add(name)
        parsed.append(
            {"name": name, "camel_name": to_camel_case(name), "type": type_name,
             "java_type": STREAM_JAVA_TYPES[type_name]}
        )
    return parsed


def load_stream_definition(path):
    data = _require_dict(_read_json(path), "definicion")

    unknown_top_level = set(data) - {"project", "package", "input", "output", "processing"}
    if unknown_top_level:
        raise DefinitionError(
            f"Claves desconocidas en el JSON: {', '.join(sorted(unknown_top_level))}."
        )

    project = _require_str(data.get("project"), "project")
    if not PROJECT_NAME_PATTERN.fullmatch(project):
        raise DefinitionError(
            "'project' debe usar minúsculas, números y guiones (p.ej. 'sales-streams')."
        )

    package = data.get("package", "com.example.streams")
    if not isinstance(package, str) or not re.fullmatch(
        r"^[a-z][a-z0-9]*(\.[a-z][a-z0-9]*)*$", package
    ):
        raise DefinitionError(
            "'package' debe ser minúsculas separadas por puntos, como 'com.example.streams'."
        )

    input_spec = _require_dict(data.get("input"), "input")
    unknown_input = set(input_spec) - {"topic", "event", "fields"}
    if unknown_input:
        raise DefinitionError(f"Claves desconocidas en 'input': {', '.join(sorted(unknown_input))}.")
    input_topic = _require_str(input_spec.get("topic"), "input.topic")
    if not TOPIC_NAME_PATTERN.fullmatch(input_topic):
        raise DefinitionError("'input.topic' contiene caracteres no válidos para un topic Kafka.")
    input_event = _require_str(input_spec.get("event"), "input.event")
    if not ENTITY_NAME_PATTERN.fullmatch(input_event):
        raise DefinitionError("'input.event' debe empezar por letra y usar solo letras/números.")
    input_fields = _parse_event_fields(input_spec.get("fields"), "input")
    input_field_names = {f["name"] for f in input_fields}

    output_spec = _require_dict(data.get("output"), "output")
    unknown_output = set(output_spec) - {"topic", "event"}
    if unknown_output:
        raise DefinitionError(f"Claves desconocidas en 'output': {', '.join(sorted(unknown_output))}.")
    output_topic = _require_str(output_spec.get("topic"), "output.topic")
    if not TOPIC_NAME_PATTERN.fullmatch(output_topic):
        raise DefinitionError("'output.topic' contiene caracteres no válidos para un topic Kafka.")
    output_event = _require_str(output_spec.get("event"), "output.event")
    if not ENTITY_NAME_PATTERN.fullmatch(output_event):
        raise DefinitionError("'output.event' debe empezar por letra y usar solo letras/números.")
    if output_event == input_event:
        raise DefinitionError("'output.event' debe ser distinto de 'input.event'.")

    processing = data.get("processing", {})
    if not isinstance(processing, dict):
        raise DefinitionError("'processing' debe ser un objeto JSON.")
    unknown_processing = set(processing) - {
        "group_by_field", "aggregate_field", "aggregate_as",
        "filter_field", "filter_operator", "filter_value",
    }
    if unknown_processing:
        raise DefinitionError(
            f"Claves desconocidas en 'processing': {', '.join(sorted(unknown_processing))}."
        )

    aggregation_keys = {"group_by_field", "aggregate_field", "aggregate_as"}
    present_aggregation_keys = aggregation_keys & set(processing)
    if present_aggregation_keys and present_aggregation_keys != aggregation_keys:
        missing = aggregation_keys - present_aggregation_keys
        raise DefinitionError(
            "'group_by_field'/'aggregate_field'/'aggregate_as' van juntos o ninguno "
            "(sin ellos el stream es un simple paso de un topic a otro, sin agregación); "
            f"falta: {', '.join(sorted(missing))}."
        )

    group_by_field = aggregate_field = aggregate_as = None
    if present_aggregation_keys:
        group_by_field = _require_str(processing.get("group_by_field"), "processing.group_by_field")
        group_by_field_spec = next((f for f in input_fields if f["name"] == group_by_field), None)
        if group_by_field_spec is None:
            raise DefinitionError(
                f"'processing.group_by_field' ('{group_by_field}') no está en 'input.fields'."
            )
        if group_by_field_spec["type"] != "string":
            # La topologia reagrupa el stream con KStream<String, ...>: la clave
            # siempre es String (con fallback "UNKNOWN" si el campo es null), asi
            # que el campo de agrupacion debe ser 'string' o el selectKey no
            # compila (mezclar un tipo numerico con el literal "UNKNOWN" en el
            # operador ternario es un error de tipos en Java).
            raise DefinitionError(
                "'processing.group_by_field' debe ser de tipo 'string' (se usa como clave "
                "de Kafka tras reagrupar, y necesita un valor de repuesto 'UNKNOWN' si es null)."
            )

        aggregate_field = _require_str(processing.get("aggregate_field"), "processing.aggregate_field")
        aggregate_field_spec = next((f for f in input_fields if f["name"] == aggregate_field), None)
        if aggregate_field_spec is None:
            raise DefinitionError(
                f"'processing.aggregate_field' ('{aggregate_field}') no está en 'input.fields'."
            )
        if aggregate_field_spec["type"] != "double":
            raise DefinitionError(
                "'processing.aggregate_field' debe ser de tipo 'double' (es el tipo del "
                "acumulador y del store; ver limitaciones en la documentación)."
            )

        aggregate_as = _require_str(processing.get("aggregate_as"), "processing.aggregate_as")
        if not ATTRIBUTE_NAME_PATTERN.fullmatch(aggregate_as):
            raise DefinitionError("'processing.aggregate_as' debe usar lower_snake_case.")
        if aggregate_as in input_field_names:
            raise DefinitionError(
                f"'processing.aggregate_as' ('{aggregate_as}') ya existe en 'input.fields'; "
                "usa un nombre distinto para el campo agregado."
            )

    filter_keys = {"filter_field", "filter_operator", "filter_value"}
    present_filter_keys = filter_keys & set(processing)
    if present_filter_keys and present_filter_keys != filter_keys:
        missing = filter_keys - present_filter_keys
        raise DefinitionError(
            "'filter_field'/'filter_operator'/'filter_value' van juntos o ninguno; "
            f"falta: {', '.join(sorted(missing))}."
        )

    filter_field = filter_operator = filter_value = None
    if present_filter_keys:
        filter_field = _require_str(processing.get("filter_field"), "processing.filter_field")
        filter_field_spec = next((f for f in input_fields if f["name"] == filter_field), None)
        if filter_field_spec is None:
            raise DefinitionError(
                f"'processing.filter_field' ('{filter_field}') no está en 'input.fields'."
            )
        if filter_field_spec["type"] not in NUMERIC_STREAM_TYPES:
            raise DefinitionError("'processing.filter_field' debe ser numérico (int/long/double).")
        filter_operator = processing.get("filter_operator")
        if filter_operator not in FILTER_OPERATORS:
            accepted = ", ".join(FILTER_OPERATORS)
            raise DefinitionError(f"'processing.filter_operator' debe ser uno de: {accepted}.")
        filter_value_raw = processing.get("filter_value")
        if not isinstance(filter_value_raw, (int, float)) or isinstance(filter_value_raw, bool):
            raise DefinitionError("'processing.filter_value' debe ser numérico.")
        filter_value = filter_value_raw

    return {
        "project": project,
        "package": package,
        "input_topic": input_topic,
        "input_event": input_event,
        "input_fields": input_fields,
        "output_topic": output_topic,
        "output_event": output_event,
        "group_by_field": group_by_field,
        "aggregate_field": aggregate_field,
        "aggregate_as": aggregate_as,
        "filter_field": filter_field,
        "filter_operator": filter_operator,
        "filter_value": filter_value,
    }
