"""Construcción de campos para las plantillas Java y SQL."""


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


def generate_dto_fields(attrs, ignore_id=False, ignore_dates=False):
    lines = []
    for attr in attrs:
        if ignore_id and attr["is_id"]:
            continue
        if ignore_dates and attr["is_date"]:
            continue
        lines.append(f"    private {attr['java_type']} {attr['camel_name']};")
    return "\n".join(lines)


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
