"""Valida crud_generator/schema/entity.schema.json contra ejemplos reales.

El generador en si no depende de 'jsonschema' (cero dependencias externas,
ver README); este test usa la libreria solo si esta instalada, para revisar
que el schema publicado sigue reflejando lo que parsing.py/json_schema.py
realmente aceptan. Si no esta instalada, se salta en vez de fallar."""

import json
import unittest
from pathlib import Path

try:
    import jsonschema

    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "crud_generator" / "schema" / "entity.schema.json"
EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


@unittest.skipUnless(HAS_JSONSCHEMA, "jsonschema no instalado (dependencia opcional, solo para este test)")
class EntitySchemaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_schema_is_a_valid_draft7_document(self):
        jsonschema.Draft7Validator.check_schema(self.schema)

    def test_every_bundled_example_validates(self):
        example_files = list(EXAMPLES_DIR.glob("*.json"))
        self.assertTrue(example_files, "no hay ejemplos en examples/ para validar")
        for path in example_files:
            with self.subTest(example=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                jsonschema.validate(data, self.schema)

    def test_multi_entity_document_with_a_reference_field_validates(self):
        document = {
            "project": "ventas",
            "entities": [
                {
                    "entity": "Cliente",
                    "fields": [
                        {"name": "id", "type": "int"},
                        {"name": "nombre", "type": "string", "not_blank": True},
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
                        {
                            "name": "estado",
                            "type": "enum",
                            "values": ["PENDIENTE", "PAGADO"],
                            "default": "PENDIENTE",
                        },
                    ],
                },
            ],
        }
        jsonschema.validate(document, self.schema)

    def test_rejects_mixing_single_and_multi_entity_keys(self):
        document = {
            "entity": "X",
            "fields": [{"name": "id", "type": "int"}],
            "entities": [{"entity": "Y", "fields": [{"name": "id", "type": "int"}]}],
        }
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(document, self.schema)

    def test_rejects_reference_field_without_references_key(self):
        document = {
            "entity": "X",
            "fields": [
                {"name": "id", "type": "int"},
                {"name": "padre", "type": "reference"},
            ],
        }
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(document, self.schema)

    def test_rejects_enum_field_with_a_single_value(self):
        document = {
            "entity": "X",
            "fields": [
                {"name": "id", "type": "int"},
                {"name": "estado", "type": "enum", "values": ["UNICO"]},
            ],
        }
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(document, self.schema)


if __name__ == "__main__":
    unittest.main()
