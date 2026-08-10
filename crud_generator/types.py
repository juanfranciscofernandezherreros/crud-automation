"""Mapeos de tipos aceptados por el generador."""

JAVA_TYPES = {
    "int": "Integer",
    "string": "String",
    "float": "Float",
    "double": "Double",
    "decimal": "BigDecimal",
    "boolean": "Boolean",
    "datetime": "LocalDateTime",
    "date": "LocalDate",
}

SQL_TYPES = {
    "int": "INT",
    "string": "VARCHAR(255)",
    "float": "DECIMAL(10, 2)",
    "double": "DECIMAL(19, 4)",
    "decimal": "DECIMAL(19, 4)",
    "boolean": "BOOLEAN",
    "datetime": "TIMESTAMP",
    "date": "DATE",
}
