"""Construcción de campos para las plantillas Java y SQL."""

from decimal import Decimal, ROUND_CEILING

from .parsing import expand_datetime_default


def generate_composite_unique_groups(attrs):
    """Agrupa por nombre de grupo las columnas SQL de los atributos con
    'composite_unique=<grupo>' (para 'reference', la columna es '{name}_id')."""
    groups = {}
    for attr in attrs:
        group = attr["validations"].get("composite_unique")
        if group:
            groups.setdefault(group, []).append(attr["sql_column"])
    return groups


def has_default(attrs):
    return any("default" in attr["validations"] for attr in attrs)


def get_enum_types(attrs):
    """Diccionario {clase_enum: valores}, uno por cada campo 'enum' distinto de
    la entidad (deduplicado por nombre de clase, que se deriva del nombre del
    campo y por tanto ya es unico dentro de una misma entidad)."""
    return {
        attr["enum_class"]: attr["enum_values"]
        for attr in attrs
        if attr["type"] == "enum"
    }


def generate_enum_import_lines(attrs, package):
    """Una linea 'import {package}.{Clase};' por cada tipo enum de la entidad,
    para los ficheros (DTOs, tests) que viven en un paquete distinto al de la
    clase enum (que se genera junto a la entidad)."""
    return "\n".join(
        f"import {package}.{enum_class};" for enum_class in sorted(get_enum_types(attrs))
    )


# Cómo convertir el valor de un query param (siempre String) al tipo Java real
# del campo antes de comparar en el Specification. None => tipo no filtrable.
FILTER_VALUE_PARSERS = {
    "String": "value",
    "Integer": "Integer.valueOf(value)",
    "Boolean": "Boolean.valueOf(value)",
    "BigDecimal": "new BigDecimal(value)",
    "Float": "Float.valueOf(value)",
    "Double": "Double.valueOf(value)",
    "LocalDate": "LocalDate.parse(value)",
    "LocalDateTime": "LocalDateTime.parse(value)",
}


def generate_specification_filter_cases(attrs):
    """Un 'case' de switch por atributo filtrable, para {Entity}Specifications.fromFilters.
    Una 'reference' se filtra por su id ('?clienteId=5'), navegando a la
    asociacion JPA sin necesidad de un join explicito."""
    lines = []
    for attr in attrs:
        if attr["type"] == "reference":
            lines.append(
                f'                case "{attr["camel_name"]}Id" -> spec = spec.and('
                f'(root, query, cb) -> cb.equal('
                f'root.get("{attr["camel_name"]}").get("id"), Integer.valueOf(value)));'
            )
            continue
        parser = FILTER_VALUE_PARSERS.get(attr["java_type"])
        if parser is None:
            continue
        lines.append(
            f'                case "{attr["camel_name"]}" -> spec = spec.and('
            f'(root, query, cb) -> cb.equal(root.get("{attr["camel_name"]}"), {parser}));'
        )
    return "\n".join(lines)


def compute_inverse_relations(entities):
    """entities: [(entity_name, attrs), ...] de un JSON multi-entidad. Devuelve
    {entity_name: [(entidad_que_referencia, campo_camelCase_en_esa_entidad), ...]}
    — para que el lado 'uno' de una 'reference' (p.ej. Cliente, referenciado por
    Pedido.cliente) pueda generar su @OneToMany inverso. Una entidad sin nada
    que la referencie sale con lista vacia; una autoreferencia (arbol) no
    genera una relacion inversa hacia si misma con este mecanismo."""
    inverse = {name: [] for name, _ in entities}
    for entity_name, attrs in entities:
        for attr in attrs:
            if attr["type"] != "reference":
                continue
            referenced = attr["references"]
            if referenced in inverse and referenced != entity_name:
                inverse[referenced].append((entity_name, attr["camel_name"]))
    return inverse


# La JVM limita un constructor a 255 argumentos, incluida la referencia implicita
# al objeto en construccion (JLS 8.4.1 / JVMS 4.11). Con 'version' incluido, un
# @AllArgsConstructor + @Builder deja de compilar a partir de ahi.
JVM_CONSTRUCTOR_PARAM_LIMIT = 254


def exceeds_constructor_param_limit(attrs):
    return len(attrs) + 1 > JVM_CONSTRUCTOR_PARAM_LIMIT


def format_default_sql_literal(attr):
    type_name = attr["type"]
    value = attr["validations"]["default"]
    if type_name in {"string", "text", "enum"}:
        return "'{}'".format(value.replace("'", "''"))
    if type_name == "boolean":
        return value
    if type_name == "date":
        return f"DATE '{value}'"
    if type_name == "datetime":
        return f"TIMESTAMP '{expand_datetime_default(value)}'"
    return value


def format_default_java_literal(attr):
    type_name = attr["type"]
    value = attr["validations"]["default"]
    if type_name in {"string", "text"}:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if type_name == "enum":
        return f"{attr['enum_class']}.{value}"
    if type_name == "boolean":
        return value
    if type_name == "int":
        return value
    if type_name == "decimal":
        return f'new BigDecimal("{value}")'
    if type_name == "float":
        return f"{value}f"
    if type_name == "double":
        return f"{value}d"
    if type_name == "date":
        return f'java.time.LocalDate.parse("{value}")'
    if type_name == "datetime":
        return f'java.time.LocalDateTime.parse("{expand_datetime_default(value)}")'
    raise ValueError(f"Tipo no soportado para 'default': {type_name}")


def generate_table_unique_constraints_annotation(attrs):
    """Fragmento para @Table(...) con las claves UNIQUE compuestas (composite_unique)."""
    groups = generate_composite_unique_groups(attrs)
    if not groups:
        return ""
    entries = []
    for group, members in groups.items():
        columns = ", ".join(f'"{name}"' for name in members)
        entries.append(
            f'@UniqueConstraint(name = "uq_{group}", columnNames = {{{columns}}})'
        )
    joined = ",\n        ".join(entries)
    return f",\n    uniqueConstraints = {{\n        {joined}\n    }}"


def generate_plain_fields(attrs):
    """Campos del modelo de dominio (hexagonal/clean): un objeto de datos
    plano, sin anotaciones JPA. Una 'reference' se representa como el mismo
    '{campo}Id' (Integer) que usan los DTO, no como el objeto relacionado:
    el dominio no tiene acceso a un repositorio para resolverlo, eso lo hace
    el adaptador de persistencia (ver ports_templates.get_persistence_adapter)."""
    fields = []
    for attr in attrs:
        if attr["type"] == "reference":
            fields.append(f"    private Integer {attr['camel_name']}Id;")
        else:
            fields.append(f"    private {attr['java_type']} {attr['camel_name']};")
    fields.append("    private Long version;")
    return "\n".join(fields)


def generate_domain_update_statements(attrs, patch=False):
    """El modelo de dominio (hexagonal/clean) representa una 'reference'
    como '{campo}Id' (ver generate_plain_fields), no como el objeto
    relacionado, asi que el getter/setter correspondiente lleva el sufijo
    'Id' igual que en los DTO."""
    lines = []
    for attr in attrs:
        if attr["is_id"] or attr["is_audit"]:
            continue
        suffix = attr["camel_name"][0].upper() + attr["camel_name"][1:]
        if attr["type"] == "reference":
            suffix += "Id"
        assignment = f"current.set{suffix}({'changes' if patch else 'replacement'}.get{suffix}());"
        if patch:
            lines.append(
                f"        if (changes.get{suffix}() != null) {{\n"
                f"            {assignment}\n"
                "        }"
            )
        else:
            lines.append(f"        {assignment}")
    return "\n".join(lines)


def generate_entity_fields(attrs, reference_type_suffix="", inverse_relations=None):
    """reference_type_suffix: layered no lo necesita ('Cliente' es a la vez
    el dominio y la entidad JPA), pero en hexagonal/clean la entidad JPA de
    una 'reference' debe apuntar a la clase de persistencia de la entidad
    referenciada ('ClienteJpaEntity'), no a su modelo de dominio ('Cliente').

    inverse_relations: [(entidad_que_me_referencia, campo_en_esa_entidad), ...]
    (ver compute_inverse_relations) — el lado 'uno' de una 'reference' (p.ej.
    Cliente, al que apunta Pedido.cliente) recibe ademas un
    @OneToMany(mappedBy=...) de solo lectura hacia esa coleccion. No se
    expone en DTOs ni dominio: consultar 'los Pedidos de un Cliente' se hace
    con el filtro generico ya existente (GET /api/pedidos?clienteId=5), no
    incrustando la coleccion (evita N+1 y respuestas de tamano no acotado)."""
    lines = []
    for attr in attrs:
        if attr["is_id"]:
            lines.append(
                "    @Id\n"
                "    @GeneratedValue(strategy = GenerationType.IDENTITY)\n"
                f"    private {attr['java_type']} {attr['camel_name']};"
            )
        elif attr["name"] in ["creado_en", "created_at"]:
            lines.append(
                "    @CreatedDate\n"
                f"    @Column(name = \"{attr['name']}\", updatable = false)\n"
                f"    private {attr['java_type']} {attr['camel_name']};"
            )
        elif attr["name"] in ["actualizado_en", "updated_at"]:
            lines.append(
                "    @LastModifiedDate\n"
                f"    @Column(name = \"{attr['name']}\")\n"
                f"    private {attr['java_type']} {attr['camel_name']};"
            )
        elif attr["type"] == "reference":
            nullable = ", nullable = false" if attr["validations"].get("required") else ""
            referenced_type = f"{attr['java_type']}{reference_type_suffix}"
            lines.append(
                "    @ManyToOne(fetch = FetchType.LAZY)\n"
                f"    @JoinColumn(name = \"{attr['sql_column']}\"{nullable})\n"
                f"    private {referenced_type} {attr['camel_name']};"
            )
        else:
            initializer = (
                f" = {format_default_java_literal(attr)}"
                if "default" in attr["validations"]
                else ""
            )
            enumerated = "    @Enumerated(EnumType.STRING)\n" if attr["type"] == "enum" else ""
            lines.append(
                f"{enumerated}"
                f"    @Column(name = \"{attr['name']}\")\n"
                f"    private {attr['java_type']} {attr['camel_name']}{initializer};"
            )
    lines.append("    @Version\n    private Long version;")
    for referencing_entity, owner_field in (inverse_relations or []):
        referencing_type = f"{referencing_entity}{reference_type_suffix}"
        collection_field = f"{referencing_entity[0].lower()}{referencing_entity[1:]}s"
        lines.append(
            f'    @OneToMany(mappedBy = "{owner_field}", fetch = FetchType.LAZY)\n'
            f"    private List<{referencing_type}> {collection_field};"
        )
    return "\n\n".join(lines)


def generate_validation_annotations(attr, mode):
    validations = attr["validations"]
    annotations = []

    if mode == "write":
        if validations.get("not_blank"):
            annotations.append("    @NotBlank")
        elif validations.get("required"):
            annotations.append("    @NotNull")
    elif mode == "patch" and validations.get("not_blank"):
        annotations.append(
            '    @Pattern(regexp = ".*\\\\S.*", message = "no debe estar vacío")'
        )

    if validations.get("positive"):
        annotations.append("    @Positive")

    minimum = validations.get("min")
    maximum = validations.get("max")
    if attr["type"] in {"string", "text"} and (minimum is not None or maximum is not None):
        arguments = []
        if minimum is not None:
            arguments.append(f"min = {minimum}")
        if maximum is not None:
            arguments.append(f"max = {maximum}")
        annotations.append(f"    @Size({', '.join(arguments)})")
    elif attr["type"] in {"int", "float", "double", "decimal"}:
        if minimum is not None:
            annotations.append(f'    @DecimalMin("{minimum}")')
        if maximum is not None:
            annotations.append(f'    @DecimalMax("{maximum}")')

    return annotations


def generate_dto_fields(
    attrs, ignore_id=False, ignore_audit=False, validation_mode=None
):
    lines = []
    for attr in attrs:
        if ignore_id and attr["is_id"]:
            continue
        if ignore_audit and attr["is_audit"]:
            continue
        if validation_mode:
            lines.extend(generate_validation_annotations(attr, validation_mode))
        if attr["type"] == "reference":
            lines.append(f"    private Integer {attr['camel_name']}Id;")
        else:
            lines.append(f"    private {attr['java_type']} {attr['camel_name']};")
    return "\n".join(lines)


def has_required_input(attrs):
    return any(
        not attr["is_id"]
        and not attr["is_audit"]
        and (
            attr["validations"].get("required")
            or attr["validations"].get("not_blank")
        )
        for attr in attrs
    )


def generate_test_dto_assignments(attrs, variable_name="createDTO"):
    lines = []
    for attr in attrs:
        if attr["is_id"] or attr["is_audit"]:
            continue
        setter_name = attr["camel_name"][0].upper() + attr["camel_name"][1:]
        if attr["type"] == "reference":
            lines.append(f"        {variable_name}.set{setter_name}Id(1);")
            continue
        value = get_valid_test_value(attr)
        lines.append(f"        {variable_name}.set{setter_name}({value});")
    return "\n".join(lines)


def generate_invalid_test_dto_assignments(attrs, variable_name="createDTO"):
    valid_assignments = generate_test_dto_assignments(attrs, variable_name)
    constrained_attrs = [
        attr
        for attr in attrs
        if not attr["is_id"]
        and not attr["is_audit"]
        and any(
            rule in attr["validations"]
            for rule in ("positive", "not_blank", "min", "max")
        )
    ]
    if not constrained_attrs:
        return ""

    attr = next(
        (
            candidate
            for candidate in constrained_attrs
            if candidate["validations"].get("positive")
        ),
        constrained_attrs[0],
    )
    setter_name = attr["camel_name"][0].upper() + attr["camel_name"][1:]
    invalid_value = get_invalid_test_value(attr)
    override = f"        {variable_name}.set{setter_name}({invalid_value});"
    return f"{valid_assignments}\n{override}"


def get_valid_test_value(attr):
    type_name = attr["type"]
    validations = attr["validations"]
    if type_name in {"string", "text"}:
        minimum = int(validations.get("min", 0))
        maximum = int(validations.get("max", 5))
        length = max(minimum, 1 if validations.get("not_blank") else 0)
        length = min(max(length, 1), maximum) if maximum > 0 else 0
        return f'"{"x" * length}"'
    if type_name in {"int", "float", "double", "decimal"}:
        minimum = Decimal(validations.get("min", "0"))
        value = max(minimum, Decimal("1")) if validations.get("positive") else minimum
        if type_name == "int":
            return str(int(value.to_integral_value(rounding=ROUND_CEILING)))
        if type_name == "decimal":
            return f'new BigDecimal("{value}")'
        suffix = "f" if type_name == "float" else "d"
        return f"{value}{suffix}"
    if type_name == "boolean":
        return "true"
    if type_name == "datetime":
        return "LocalDateTime.now()"
    if type_name == "date":
        return "LocalDate.now()"
    if type_name == "enum":
        return f"{attr['enum_class']}.{attr['enum_values'][0]}"
    raise ValueError(f"Tipo no soportado en tests: {type_name}")


def get_invalid_test_value(attr):
    type_name = attr["type"]
    validations = attr["validations"]
    if validations.get("positive"):
        return {
            "int": "-1",
            "float": "-1f",
            "double": "-1d",
            "decimal": 'new BigDecimal("-1")',
        }[type_name]
    if validations.get("not_blank"):
        return '" "'
    if type_name in {"string", "text"} and "min" in validations:
        length = max(int(validations["min"]) - 1, 0)
        return f'"{"x" * length}"'
    if type_name in {"string", "text"} and "max" in validations:
        return f'"{"x" * (int(validations["max"]) + 1)}"'
    if "min" in validations:
        value = Decimal(validations["min"]) - 1
    else:
        value = Decimal(validations["max"]) + 1
    if type_name == "int":
        return str(int(value.to_integral_value(rounding=ROUND_CEILING)))
    if type_name == "decimal":
        return f'new BigDecimal("{value}")'
    return f"{value}{'f' if type_name == 'float' else 'd'}"


def generate_sql_column_definition(attr, force_nullable=False):
    """Fragmento 'nombre TIPO restricciones' de una columna, sin indentacion ni
    coma final. Compartido por generate_sql_fields (CREATE TABLE) y migrations.py
    (ALTER TABLE ADD COLUMN de una migracion incremental).

    force_nullable evita anadir NOT NULL sin DEFAULT: en un ALTER TABLE sobre una
    tabla con filas, Postgres rechaza una columna NOT NULL sin valor por defecto
    para las filas ya existentes.
    """
    column = attr["sql_column"]
    validations = attr["validations"]
    sql_type = attr["sql_type"]
    if attr["type"] == "string" and "max" in validations:
        sql_type = f"VARCHAR({validations['max']})"
    constraints = []
    if attr["name"] in ["creado_en", "created_at"]:
        constraints.extend(["NOT NULL", "DEFAULT CURRENT_TIMESTAMP"])
    elif (validations.get("required") or validations.get("not_blank")) and not (
        force_nullable and "default" not in validations
    ):
        constraints.append("NOT NULL")
    if "default" in validations:
        constraints.append(f"DEFAULT {format_default_sql_literal(attr)}")
    if validations.get("unique"):
        constraints.append("UNIQUE")
    checks = []
    if validations.get("not_blank"):
        checks.append(f"btrim({column}) <> ''")
    if validations.get("positive"):
        checks.append(f"{column} > 0")
    if "min" in validations:
        expression = (
            f"char_length({column}) >= {validations['min']}"
            if attr["type"] in {"string", "text"}
            else f"{column} >= {validations['min']}"
        )
        checks.append(expression)
    if "max" in validations:
        if attr["type"] == "text":
            checks.append(f"char_length({column}) <= {validations['max']}")
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


def generate_sql_fields(attrs, table_name="tabla"):
    lines = []
    for attr in attrs:
        if attr["is_id"]:
            lines.append(f"    {attr['name']} SERIAL PRIMARY KEY")
            continue
        lines.append(f"    {generate_sql_column_definition(attr)}")

    for group, members in generate_composite_unique_groups(attrs).items():
        columns = ", ".join(members)
        lines.append(f"    CONSTRAINT uq_{table_name}_{group} UNIQUE ({columns})")

    lines.append("    version BIGINT NOT NULL DEFAULT 0")
    return ",\n".join(lines)


def generate_sql_indexes(attrs, table_name):
    return "\n".join(
        f"CREATE INDEX idx_{table_name}_{attr['sql_column']} "
        f"ON {table_name} ({attr['sql_column']});"
        for attr in attrs
        if attr["validations"].get("index")
        and not attr["validations"].get("unique")
    )
