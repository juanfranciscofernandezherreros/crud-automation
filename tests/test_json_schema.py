import contextlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from crud_generator.generator import generate_project_from_json
from crud_generator.json_schema import (
    is_multi_entity_document,
    load_entities_schema,
    load_schema,
)
from crud_generator.parsing import DefinitionError, parse_attributes_from_fields


@contextlib.contextmanager
def working_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class ParseAttributesFromFieldsTest(unittest.TestCase):
    def test_parses_typed_fields_equivalent_to_the_text_dsl(self):
        attrs = parse_attributes_from_fields(
            [
                {"name": "id", "type": "int"},
                {
                    "name": "isin",
                    "type": "string",
                    "max": 12,
                    "not_blank": True,
                    "unique": True,
                    "index": True,
                },
                {
                    "name": "patrimonio",
                    "type": "decimal",
                    "precision": 18,
                    "scale": 2,
                    "required": True,
                    "positive": True,
                },
            ]
        )

        self.assertEqual("VARCHAR(255)", attrs[1]["sql_type"])
        self.assertEqual("12", attrs[1]["validations"]["max"])
        self.assertTrue(attrs[1]["validations"]["not_blank"])
        self.assertEqual("DECIMAL(18, 2)", attrs[2]["sql_type"])
        self.assertEqual(18, attrs[2]["precision"])
        self.assertEqual(2, attrs[2]["scale"])

    def test_default_values_are_not_restricted_by_dsl_delimiters(self):
        attrs = parse_attributes_from_fields(
            [
                {"name": "id", "type": "int"},
                {"name": "nota", "type": "string", "default": "A, B: C"},
                {
                    "name": "evento_at",
                    "type": "datetime",
                    "default": "2026-01-31T10:30:00",
                },
            ]
        )

        self.assertEqual("A, B: C", attrs[1]["validations"]["default"])
        # Se normaliza a la forma compacta interna (sin ':') pero el valor de
        # entrada SI podia llevar ':', a diferencia del DSL de texto.
        self.assertEqual("2026-01-31T103000", attrs[2]["validations"]["default"])

    def test_composite_unique_group_works_like_the_text_dsl(self):
        attrs = parse_attributes_from_fields(
            [
                {"name": "id", "type": "int"},
                {
                    "name": "refitid",
                    "type": "string",
                    "not_blank": True,
                    "composite_unique": "refit_key",
                },
                {
                    "name": "refitidctrl",
                    "type": "string",
                    "not_blank": True,
                    "composite_unique": "refit_key",
                },
            ]
        )

        self.assertEqual("refit_key", attrs[1]["validations"]["composite_unique"])
        self.assertEqual("refit_key", attrs[2]["validations"]["composite_unique"])

    def test_rejects_composite_unique_group_with_a_single_member(self):
        with self.assertRaisesRegex(DefinitionError, "al menos dos"):
            parse_attributes_from_fields(
                [
                    {"name": "id", "type": "int"},
                    {
                        "name": "refitid",
                        "type": "string",
                        "composite_unique": "solo",
                    },
                ]
            )

    def test_rejects_unknown_field_key(self):
        with self.assertRaisesRegex(DefinitionError, "Claves desconocidas"):
            parse_attributes_from_fields(
                [
                    {"name": "id", "type": "int"},
                    {"name": "x", "type": "string", "not_a_real_rule": True},
                ]
            )

    def test_rejects_unknown_type(self):
        with self.assertRaisesRegex(DefinitionError, "Tipo desconocido"):
            parse_attributes_from_fields(
                [{"name": "id", "type": "int"}, {"name": "x", "type": "uuid"}]
            )

    def test_rejects_definition_without_id(self):
        with self.assertRaisesRegex(DefinitionError, "incluir un atributo 'id'"):
            parse_attributes_from_fields([{"name": "nombre", "type": "string"}])

    def test_rejects_precision_without_scale(self):
        with self.assertRaisesRegex(DefinitionError, "precision.*scale.*juntos"):
            parse_attributes_from_fields(
                [
                    {"name": "id", "type": "int"},
                    {"name": "importe", "type": "decimal", "precision": 10},
                ]
            )


class EnumFieldTest(unittest.TestCase):
    def test_parses_enum_with_values_and_default(self):
        attrs = parse_attributes_from_fields(
            [
                {"name": "id", "type": "int"},
                {
                    "name": "estado",
                    "type": "enum",
                    "values": ["PENDIENTE", "PAGADO"],
                    "required": True,
                    "default": "PENDIENTE",
                },
            ]
        )

        estado = attrs[1]
        self.assertEqual("enum", estado["type"])
        self.assertEqual("Estado", estado["java_type"])
        self.assertEqual("Estado", estado["enum_class"])
        self.assertEqual(["PENDIENTE", "PAGADO"], estado["enum_values"])
        self.assertEqual("VARCHAR(9)", estado["sql_type"])
        self.assertEqual("PENDIENTE", estado["validations"]["default"])
        self.assertTrue(estado["validations"]["required"])

    def test_rejects_enum_with_fewer_than_two_values(self):
        with self.assertRaisesRegex(DefinitionError, "al menos dos opciones"):
            parse_attributes_from_fields(
                [
                    {"name": "id", "type": "int"},
                    {"name": "estado", "type": "enum", "values": ["UNICO"]},
                ]
            )

    def test_rejects_lowercase_enum_values(self):
        with self.assertRaisesRegex(DefinitionError, "MAYUSCULAS"):
            parse_attributes_from_fields(
                [
                    {"name": "id", "type": "int"},
                    {"name": "estado", "type": "enum", "values": ["pendiente", "PAGADO"]},
                ]
            )

    def test_rejects_duplicate_enum_values(self):
        with self.assertRaisesRegex(DefinitionError, "duplicado"):
            parse_attributes_from_fields(
                [
                    {"name": "id", "type": "int"},
                    {"name": "estado", "type": "enum", "values": ["A", "A"]},
                ]
            )

    def test_rejects_default_outside_declared_values(self):
        with self.assertRaisesRegex(DefinitionError, "debe ser uno de"):
            parse_attributes_from_fields(
                [
                    {"name": "id", "type": "int"},
                    {
                        "name": "estado",
                        "type": "enum",
                        "values": ["A", "B"],
                        "default": "C",
                    },
                ]
            )

    def test_rejects_string_only_rules_on_enum(self):
        with self.assertRaisesRegex(DefinitionError, "not_blank"):
            parse_attributes_from_fields(
                [
                    {"name": "id", "type": "int"},
                    {
                        "name": "estado",
                        "type": "enum",
                        "values": ["A", "B"],
                        "not_blank": True,
                    },
                ]
            )


class LoadSchemaTest(unittest.TestCase):
    def _write_json(self, directory, data):
        path = Path(directory) / "schema.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return str(path)

    def test_loads_entity_architecture_and_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_json(
                directory,
                {
                    "entity": "Producto",
                    "architecture": "hexagonal",
                    "fields": [
                        {"name": "id", "type": "int"},
                        {"name": "nombre", "type": "string", "not_blank": True},
                    ],
                },
            )

            entity_name, architecture, base_package, endpoints, attrs = load_schema(path)

            self.assertEqual("Producto", entity_name)
            self.assertEqual("hexagonal", architecture)
            self.assertIsNone(base_package)
            self.assertIsNone(endpoints)
            self.assertEqual(2, len(attrs))

    def test_architecture_is_optional(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_json(
                directory,
                {"entity": "Producto", "fields": [{"name": "id", "type": "int"}]},
            )

            _, architecture, _, _, _ = load_schema(path)

            self.assertIsNone(architecture)

    def test_loads_package_and_endpoints(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_json(
                directory,
                {
                    "entity": "Producto",
                    "package": "com.miempresa.catalogo",
                    "endpoints": ["list", "get"],
                    "fields": [{"name": "id", "type": "int"}],
                },
            )

            _, _, base_package, endpoints, _ = load_schema(path)

            self.assertEqual("com.miempresa.catalogo", base_package)
            self.assertEqual(["list", "get"], endpoints)

    def test_rejects_missing_file(self):
        with self.assertRaisesRegex(DefinitionError, "No se pudo leer"):
            load_schema("no-existe.json")

    def test_rejects_invalid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{ not valid json ", encoding="utf-8")

            with self.assertRaisesRegex(DefinitionError, "no es válido"):
                load_schema(str(path))

    def test_rejects_missing_entity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_json(
                directory, {"fields": [{"name": "id", "type": "int"}]}
            )

            with self.assertRaisesRegex(DefinitionError, "'entity'"):
                load_schema(path)

    def test_rejects_missing_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_json(directory, {"entity": "Producto"})

            with self.assertRaisesRegex(DefinitionError, "'fields'"):
                load_schema(path)

    def test_rejects_unknown_top_level_key(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_json(
                directory,
                {
                    "entity": "Producto",
                    "fields": [{"name": "id", "type": "int"}],
                    "sospechoso": True,
                },
            )

            with self.assertRaisesRegex(DefinitionError, "Claves desconocidas"):
                load_schema(path)


class GenerateProjectFromJsonTest(unittest.TestCase):
    def test_generates_a_full_project_with_defaults_preserved_verbatim(self):
        with tempfile.TemporaryDirectory() as directory:
            json_path = Path(directory) / "producto.json"
            json_path.write_text(
                json.dumps(
                    {
                        "entity": "ProductoJson",
                        "architecture": "layered",
                        "fields": [
                            {"name": "id", "type": "int"},
                            {
                                "name": "nombre",
                                "type": "string",
                                "not_blank": True,
                                "max": 120,
                            },
                            {
                                "name": "nota",
                                "type": "string",
                                "default": "A, B: C",
                            },
                            {
                                "name": "creado_evento",
                                "type": "datetime",
                                "default": "2026-01-31T10:30:00",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with working_directory(directory):
                base_dir = Path(generate_project_from_json(str(json_path)))
                migration = (
                    base_dir
                    / "src/main/resources/db/migration/V1__Create_Table_ProductoJson.sql"
                ).read_text(encoding="utf-8")
                docs = (base_dir / "docs/index.html").read_text(encoding="utf-8")

            self.assertIn("nota VARCHAR(255) DEFAULT 'A, B: C'", migration)
            self.assertIn(
                "creado_evento TIMESTAMP DEFAULT TIMESTAMP '2026-01-31T10:30:00'",
                migration,
            )
            self.assertIn("--json", docs)

    def test_architecture_override_takes_precedence_over_json(self):
        with tempfile.TemporaryDirectory() as directory:
            json_path = Path(directory) / "producto.json"
            json_path.write_text(
                json.dumps(
                    {
                        "entity": "ProductoJsonHex",
                        "architecture": "layered",
                        "fields": [{"name": "id", "type": "int"}],
                    }
                ),
                encoding="utf-8",
            )

            with working_directory(directory):
                base_dir = generate_project_from_json(
                    str(json_path), architecture_override="hexagonal"
                )

            self.assertTrue(base_dir.endswith("-hexagonal"))


class LoadEntitiesSchemaTest(unittest.TestCase):
    def _write_json(self, directory, data, name="schema.json"):
        path = Path(directory) / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return str(path)

    def test_is_multi_entity_document_detects_the_entities_key(self):
        with tempfile.TemporaryDirectory() as directory:
            single = self._write_json(
                directory,
                {"entity": "X", "fields": [{"name": "id", "type": "int"}]},
                name="single.json",
            )
            multi = self._write_json(
                directory,
                {
                    "entities": [
                        {"entity": "X", "fields": [{"name": "id", "type": "int"}]}
                    ]
                },
                name="multi.json",
            )
            self.assertFalse(is_multi_entity_document(single))
            self.assertTrue(is_multi_entity_document(multi))

    def test_orders_entities_so_referenced_ones_come_first(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_json(
                directory,
                {
                    "project": "ventas",
                    "entities": [
                        {
                            "entity": "Pedido",
                            "fields": [
                                {"name": "id", "type": "int"},
                                {
                                    "name": "cliente",
                                    "type": "reference",
                                    "references": "Cliente",
                                    "required": True,
                                },
                            ],
                        },
                        {
                            "entity": "Cliente",
                            "fields": [{"name": "id", "type": "int"}],
                        },
                    ],
                },
            )

            project_name, architecture, base_package, endpoints, entities = (
                load_entities_schema(path)
            )

            self.assertEqual("ventas", project_name)
            self.assertEqual(["Cliente", "Pedido"], [name for name, _ in entities])

    def test_rejects_reference_to_undefined_entity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_json(
                directory,
                {
                    "entities": [
                        {
                            "entity": "Pedido",
                            "fields": [
                                {"name": "id", "type": "int"},
                                {
                                    "name": "cliente",
                                    "type": "reference",
                                    "references": "Cliente",
                                },
                            ],
                        }
                    ]
                },
            )
            with self.assertRaisesRegex(DefinitionError, "no está definida"):
                load_entities_schema(path)

    def test_rejects_circular_references(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_json(
                directory,
                {
                    "entities": [
                        {
                            "entity": "A",
                            "fields": [
                                {"name": "id", "type": "int"},
                                {"name": "b", "type": "reference", "references": "B"},
                            ],
                        },
                        {
                            "entity": "B",
                            "fields": [
                                {"name": "id", "type": "int"},
                                {"name": "a", "type": "reference", "references": "A"},
                            ],
                        },
                    ]
                },
            )
            with self.assertRaisesRegex(DefinitionError, "circulares"):
                load_entities_schema(path)

    def test_allows_self_reference_without_treating_it_as_a_cycle(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_json(
                directory,
                {
                    "entities": [
                        {
                            "entity": "Categoria",
                            "fields": [
                                {"name": "id", "type": "int"},
                                {
                                    "name": "padre",
                                    "type": "reference",
                                    "references": "Categoria",
                                },
                            ],
                        }
                    ]
                },
            )
            _, _, _, _, entities = load_entities_schema(path)
            self.assertEqual(["Categoria"], [name for name, _ in entities])

    def test_project_name_defaults_to_first_entity_when_project_key_absent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_json(
                directory,
                {
                    "entities": [
                        {"entity": "Cliente", "fields": [{"name": "id", "type": "int"}]},
                    ]
                },
            )
            project_name, *_ = load_entities_schema(path)
            self.assertEqual("Cliente", project_name)

    def test_single_entity_document_rejects_reference_type(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_json(
                directory,
                {
                    "entity": "Pedido",
                    "fields": [
                        {"name": "id", "type": "int"},
                        {
                            "name": "cliente",
                            "type": "reference",
                            "references": "Cliente",
                        },
                    ],
                },
            )
            with self.assertRaisesRegex(DefinitionError, "multi-entidad"):
                load_schema(path)

    def test_generate_project_from_json_dispatches_multi_entity_layered_project(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_json(
                directory,
                {
                    "project": "ventas",
                    "package": "com.miempresa.ventas",
                    "entities": [
                        {
                            "entity": "Cliente",
                            "fields": [
                                {
                                    "name": "nombre",
                                    "type": "string",
                                    "not_blank": True,
                                    "required": True,
                                },
                                {"name": "id", "type": "int"},
                            ],
                        },
                        {
                            "entity": "Pedido",
                            "fields": [
                                {"name": "id", "type": "int"},
                                {
                                    "name": "cliente",
                                    "type": "reference",
                                    "references": "Cliente",
                                    "required": True,
                                },
                            ],
                        },
                    ],
                },
            )

            with working_directory(directory):
                base_dir = Path(generate_project_from_json(path))
                self.assertEqual("crud-ventas", base_dir.name)
                self.assertTrue(
                    (base_dir / "src/main/java/com/miempresa/ventas/entity/Cliente.java").is_file()
                )
                self.assertTrue(
                    (base_dir / "src/main/java/com/miempresa/ventas/entity/Pedido.java").is_file()
                )
                migrations_dir = base_dir / "src/main/resources/db/migration"
                self.assertEqual(
                    ["V1__Create_Table_Cliente.sql", "V2__Create_Table_Pedido.sql"],
                    sorted(path.name for path in migrations_dir.iterdir()),
                )

    def test_generate_project_from_json_dispatches_multi_entity_ports_project(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_json(
                directory,
                {
                    "project": "ventas",
                    "architecture": "hexagonal",
                    "package": "com.miempresa.ventas",
                    "entities": [
                        {
                            "entity": "Cliente",
                            "fields": [
                                {
                                    "name": "nombre",
                                    "type": "string",
                                    "not_blank": True,
                                    "required": True,
                                },
                                {"name": "id", "type": "int"},
                            ],
                        },
                        {
                            "entity": "Pedido",
                            "fields": [
                                {"name": "id", "type": "int"},
                                {
                                    "name": "cliente",
                                    "type": "reference",
                                    "references": "Cliente",
                                    "required": True,
                                },
                            ],
                        },
                    ],
                },
            )

            with working_directory(directory):
                base_dir = Path(generate_project_from_json(path))
                self.assertEqual("crud-ventas-hexagonal", base_dir.name)
                persistence = base_dir / "src/main/java/com/miempresa/ventas/adapter/out/persistence"
                self.assertTrue((persistence / "ClienteJpaEntity.java").is_file())
                self.assertTrue((persistence / "PedidoJpaEntity.java").is_file())
                self.assertTrue((persistence / "PedidoPersistenceAdapter.java").is_file())
                migrations_dir = base_dir / "src/main/resources/db/migration"
                self.assertEqual(
                    ["V1__Create_Table_Cliente.sql", "V2__Create_Table_Pedido.sql"],
                    sorted(path.name for path in migrations_dir.iterdir()),
                )


if __name__ == "__main__":
    unittest.main()
