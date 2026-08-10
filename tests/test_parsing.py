import unittest

from crud_generator.parsing import (
    DefinitionError,
    normalize_entity_name,
    parse_attributes,
)
from crud_generator.generator import generate_project


class ParseAttributesTest(unittest.TestCase):
    def test_parses_valid_definition(self):
        attributes = parse_attributes("id:int, created_at:datetime, name:string")

        self.assertEqual("createdAt", attributes[1]["camel_name"])
        self.assertEqual("LocalDateTime", attributes[1]["java_type"])
        self.assertEqual("VARCHAR(255)", attributes[2]["sql_type"])

    def test_rejects_malformed_attribute(self):
        with self.assertRaisesRegex(DefinitionError, "nombre:tipo"):
            parse_attributes("id:int, nombre")

    def test_rejects_unknown_type(self):
        with self.assertRaisesRegex(DefinitionError, "Tipo desconocido 'uuid'"):
            parse_attributes("id:int, referencia:uuid")

    def test_rejects_duplicate_attribute(self):
        with self.assertRaisesRegex(DefinitionError, "duplicado"):
            parse_attributes("id:int, nombre:string, nombre:string")

    def test_rejects_definition_without_id(self):
        with self.assertRaisesRegex(DefinitionError, "incluir un atributo 'id'"):
            parse_attributes("nombre:string")

    def test_rejects_invalid_attribute_name(self):
        with self.assertRaisesRegex(DefinitionError, "lower_snake_case"):
            parse_attributes("id:int, Nombre Completo:string")


class NormalizeEntityNameTest(unittest.TestCase):
    def test_preserves_internal_capitalization(self):
        self.assertEqual("PedidoItem", normalize_entity_name("pedidoItem"))

    def test_rejects_invalid_entity_name(self):
        with self.assertRaisesRegex(DefinitionError, "Nombre de entidad no válido"):
            normalize_entity_name("pedido-item")

    def test_generator_rejects_invalid_entity_name(self):
        with self.assertRaisesRegex(DefinitionError, "Nombre de entidad no válido"):
            generate_project("pedido-item", "id:int")


if __name__ == "__main__":
    unittest.main()
