import contextlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from crud_generator.generator import generate_project_from_json
from crud_generator.json_schema import load_schema
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

            entity_name, architecture, attrs = load_schema(path)

            self.assertEqual("Producto", entity_name)
            self.assertEqual("hexagonal", architecture)
            self.assertEqual(2, len(attrs))

    def test_architecture_is_optional(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_json(
                directory,
                {"entity": "Producto", "fields": [{"name": "id", "type": "int"}]},
            )

            _, architecture, _ = load_schema(path)

            self.assertIsNone(architecture)

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


if __name__ == "__main__":
    unittest.main()
