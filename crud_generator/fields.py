"""Construcción de campos para las plantillas Java y SQL."""

from decimal import Decimal, ROUND_CEILING

from .parsing import expand_datetime_default


def generate_composite_unique_groups(attrs):
    """Agrupa por nombre de grupo los atributos con 'composite_unique=<grupo>'."""
    groups = {}
    for attr in attrs:
        group = attr["validations"].get("composite_unique")
        if group:
            groups.setdefault(group, []).append(attr["name"])
    return groups


def has_default(attrs):
    return any("default" in attr["validations"] for attr in attrs)


def format_default_sql_literal(attr):
    type_name = attr["type"]
    value = attr["validations"]["default"]
    if type_name in {"string", "text"}:
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
    fields = [
        f"    private {attr['java_type']} {attr['camel_name']};" for attr in attrs
    ]
    fields.append("    private Long version;")
    return "\n".join(fields)


def generate_domain_update_statements(attrs, patch=False):
    lines = []
    for attr in attrs:
        if attr["is_id"] or attr["is_audit"]:
            continue
        suffix = attr["camel_name"][0].upper() + attr["camel_name"][1:]
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


def generate_entity_fields(attrs):
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
        else:
            initializer = (
                f" = {format_default_java_literal(attr)}"
                if "default" in attr["validations"]
                else ""
            )
            lines.append(
                f"    @Column(name = \"{attr['name']}\")\n"
                f"    private {attr['java_type']} {attr['camel_name']}{initializer};"
            )
    lines.append("    @Version\n    private Long version;")
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
        value = get_valid_test_value(attr)
        setter_name = attr["camel_name"][0].upper() + attr["camel_name"][1:]
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


def generate_sql_fields(attrs, table_name="tabla"):
    lines = []
    for attr in attrs:
        if attr["is_id"]:
            lines.append(f"    {attr['name']} SERIAL PRIMARY KEY")
            continue

        validations = attr["validations"]
        sql_type = attr["sql_type"]
        if attr["type"] == "string" and "max" in validations:
            sql_type = f"VARCHAR({validations['max']})"
        constraints = []
        if attr["name"] in ["creado_en", "created_at"]:
            constraints.extend(["NOT NULL", "DEFAULT CURRENT_TIMESTAMP"])
        elif validations.get("required") or validations.get("not_blank"):
            constraints.append("NOT NULL")
        if "default" in validations:
            constraints.append(f"DEFAULT {format_default_sql_literal(attr)}")
        if validations.get("unique"):
            constraints.append("UNIQUE")
        checks = []
        if validations.get("not_blank"):
            checks.append(f"btrim({attr['name']}) <> ''")
        if validations.get("positive"):
            checks.append(f"{attr['name']} > 0")
        if "min" in validations:
            expression = (
                f"char_length({attr['name']}) >= {validations['min']}"
                if attr["type"] in {"string", "text"}
                else f"{attr['name']} >= {validations['min']}"
            )
            checks.append(expression)
        if "max" in validations:
            if attr["type"] == "text":
                checks.append(f"char_length({attr['name']}) <= {validations['max']}")
            elif attr["type"] != "string":
                checks.append(f"{attr['name']} <= {validations['max']}")
        constraints.extend(f"CHECK ({check})" for check in checks)
        suffix = f" {' '.join(constraints)}" if constraints else ""
        lines.append(f"    {attr['name']} {sql_type}{suffix}")

    for group, members in generate_composite_unique_groups(attrs).items():
        columns = ", ".join(members)
        lines.append(f"    CONSTRAINT uq_{table_name}_{group} UNIQUE ({columns})")

    lines.append("    version BIGINT NOT NULL DEFAULT 0")
    return ",\n".join(lines)


def generate_sql_indexes(attrs, table_name):
    return "\n".join(
        f"CREATE INDEX idx_{table_name}_{attr['name']} "
        f"ON {table_name} ({attr['name']});"
        for attr in attrs
        if attr["validations"].get("index")
        and not attr["validations"].get("unique")
    )
