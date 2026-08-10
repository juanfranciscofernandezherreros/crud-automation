"""Construcción de campos para las plantillas Java y SQL."""

from decimal import Decimal, ROUND_CEILING


def generate_plain_fields(attrs):
    return "\n".join(
        f"    private {attr['java_type']} {attr['camel_name']};" for attr in attrs
    )


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
            lines.append(
                f"    @Column(name = \"{attr['name']}\")\n"
                f"    private {attr['java_type']} {attr['camel_name']};"
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
    if attr["type"] == "string" and (minimum is not None or maximum is not None):
        arguments = []
        if minimum is not None:
            arguments.append(f"min = {minimum}")
        if maximum is not None:
            arguments.append(f"max = {maximum}")
        annotations.append(f"    @Size({', '.join(arguments)})")
    elif attr["type"] in {"int", "float", "double"}:
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
    if type_name == "string":
        minimum = int(validations.get("min", 0))
        maximum = int(validations.get("max", 5))
        length = max(minimum, 1 if validations.get("not_blank") else 0)
        length = min(max(length, 1), maximum) if maximum > 0 else 0
        return f'"{"x" * length}"'
    if type_name in {"int", "float", "double"}:
        minimum = Decimal(validations.get("min", "0"))
        value = max(minimum, Decimal("1")) if validations.get("positive") else minimum
        if type_name == "int":
            return str(int(value.to_integral_value(rounding=ROUND_CEILING)))
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
        return {"int": "-1", "float": "-1f", "double": "-1d"}[type_name]
    if validations.get("not_blank"):
        return '" "'
    if type_name == "string" and "min" in validations:
        length = max(int(validations["min"]) - 1, 0)
        return f'"{"x" * length}"'
    if type_name == "string" and "max" in validations:
        return f'"{"x" * (int(validations["max"]) + 1)}"'
    if "min" in validations:
        value = Decimal(validations["min"]) - 1
    else:
        value = Decimal(validations["max"]) + 1
    if type_name == "int":
        return str(int(value.to_integral_value(rounding=ROUND_CEILING)))
    return f"{value}{'f' if type_name == 'float' else 'd'}"


def generate_sql_fields(attrs):
    lines = []
    for attr in attrs:
        if attr["is_id"]:
            lines.append(f"    {attr['name']} SERIAL PRIMARY KEY")
        elif attr["name"] in ["creado_en", "created_at"]:
            lines.append(
                f"    {attr['name']} {attr['sql_type']} "
                "NOT NULL DEFAULT CURRENT_TIMESTAMP"
            )
        else:
            lines.append(f"    {attr['name']} {attr['sql_type']}")
    return ",\n".join(lines)
