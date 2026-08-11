"""Mapeos de tipos aceptados por el generador."""

JAVA_TYPES = {
    "int": "Integer",
    "string": "String",
    "text": "String",
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
    "text": "TEXT",
    "float": "REAL",
    "double": "DOUBLE PRECISION",
    "decimal": "DECIMAL(19, 4)",
    "boolean": "BOOLEAN",
    "datetime": "TIMESTAMP",
    "date": "DATE",
}

# Tipos que se comportan como texto a efectos de reglas (not_blank, min/max, @Size).
STRING_LIKE_TYPES = {"string", "text"}
