"""Migraciones Flyway, incrementales cuando el proyecto ya existe en disco.

Regenerar sobre un directorio ya generado antes (con --force) no debe reescribir
V1__Create_Table_*.sql: esa migracion pudo haberse aplicado ya contra una base de
datos real, y Flyway rechaza un checksum distinto para una version ya aplicada.
En su lugar, se añade V{n}__Update_Table_*.sql solo con las columnas nuevas.

No es un motor de diff SQL completo: no detecta columnas eliminadas ni cambios de
tipo en una columna existente (eso exigiria parsear el SQL en profundidad); esos
casos se dejan para una migracion manual, y se advierte en el fichero generado.
"""

import os
import re

from .fields import generate_sql_column_definition, generate_sql_fields, generate_sql_indexes

_VERSION_PATTERN = re.compile(r"^V(\d+)__.*\.sql$")
_ENTITY_VERSION_PATTERN_TEMPLATE = r"^V(\d+)__(?:Create|Update)_Table_{entity}\.sql$"
_COLUMN_LINE_PATTERN = re.compile(r"^\s{4}([a-z][a-z0-9_]*)\s+[A-Z]")


def _migration_dir_on_disk(res_base):
    return os.path.join(*res_base.split("/"), "db", "migration")


def _all_existing_versions(migration_dir):
    if not os.path.isdir(migration_dir):
        return []
    versions = []
    for name in os.listdir(migration_dir):
        match = _VERSION_PATTERN.match(name)
        if match:
            versions.append(int(match.group(1)))
    return sorted(versions)


def _existing_versions_for_entity(migration_dir, entity_name):
    """Solo las migraciones YA escritas para esta entidad. Un proyecto
    multi-entidad comparte un unico directorio db/migration/, asi que no basta
    con mirar si el directorio tiene ficheros: hay que filtrar por el nombre de
    la entidad para no confundir la primera migracion de una entidad con una
    actualizacion incremental de otra."""
    if not os.path.isdir(migration_dir):
        return []
    pattern = re.compile(_ENTITY_VERSION_PATTERN_TEMPLATE.format(entity=re.escape(entity_name)))
    versions = []
    for name in os.listdir(migration_dir):
        match = pattern.match(name)
        if match:
            versions.append((int(match.group(1)), name))
    return sorted(versions)


def _columns_already_migrated(migration_dir, existing_versions):
    """Nombres de columna que ya aparecen en alguna migracion previa DE ESTA
    ENTIDAD, mediante una lectura linea a linea (no un parser SQL): basta con
    reconocer el patron de indentacion de 4 espacios que usan
    generate_sql_fields/generate_sql_column_definition."""
    columns = set()
    for _, filename in existing_versions:
        with open(
            os.path.join(migration_dir, filename), encoding="utf-8"
        ) as handle:
            for line in handle:
                match = _COLUMN_LINE_PATTERN.match(line)
                if match:
                    columns.add(match.group(1))
    return columns


def write_migration(res_base, entity_name, entity_lower, table_name, attrs, write_file, get_sql_migration):
    """Escribe la migracion de la entidad: V1 si esta entidad aun no tenia
    migraciones, o V{n}__Update_Table_{Entity}.sql con las columnas nuevas si ya
    las tenia (regeneracion sobre un proyecto existente). El numero de version
    es unico para todo el proyecto aunque varias entidades compartan carpeta."""
    migration_dir = _migration_dir_on_disk(res_base)
    entity_versions = _existing_versions_for_entity(migration_dir, entity_name)
    all_versions = _all_existing_versions(migration_dir)
    next_version = (max(all_versions) if all_versions else 0) + 1

    if not entity_versions:
        write_file(
            f"{res_base}/db/migration/V{next_version}__Create_Table_{entity_name}.sql",
            get_sql_migration(
                entity_lower,
                generate_sql_fields(attrs, table_name),
                generate_sql_indexes(attrs, table_name),
            ),
        )
        return

    known_columns = _columns_already_migrated(migration_dir, entity_versions)
    new_attrs = [
        attr
        for attr in attrs
        if not attr["is_id"] and attr["name"] not in known_columns
    ]
    if not new_attrs:
        return

    lines = [f"ALTER TABLE {table_name} ADD COLUMN "
             f"{generate_sql_column_definition(attr, force_nullable=True)};"
             for attr in new_attrs]
    warnings = [
        attr["name"]
        for attr in new_attrs
        if (attr["validations"].get("required") or attr["validations"].get("not_blank"))
        and "default" not in attr["validations"]
    ]
    header = (
        "-- Migracion incremental generada automaticamente al regenerar el "
        f"proyecto con --force.\n-- Anade solo las columnas nuevas de '{entity_name}'; "
        "no borra ni modifica columnas existentes.\n"
    )
    if warnings:
        header += (
            "-- ATENCION: "
            + ", ".join(warnings)
            + " son obligatorias en el DSL/JSON pero se crean aqui como NULL "
            "porque la tabla puede tener filas: rellena los valores y anade "
            "una migracion posterior que fije NOT NULL.\n"
        )
    content = header + "\n".join(lines) + "\n"
    write_file(
        f"{res_base}/db/migration/V{next_version}__Update_Table_{entity_name}.sql",
        content,
    )
