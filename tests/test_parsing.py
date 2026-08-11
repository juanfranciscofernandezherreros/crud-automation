import unittest

from crud_generator.parsing import (
    DefinitionError,
    normalize_entity_name,
    parse_attributes,
)
from crud_generator.generator import generate_project


class ParseAttributesTest(unittest.TestCase):
    def test_parses_valid_definition(self):
        attributes = parse_attributes(
            "id:int, created_at:datetime, "
            "name:string:not_blank:max=120:unique:index"
        )

        self.assertEqual("createdAt", attributes[1]["camel_name"])
        self.assertEqual("LocalDateTime", attributes[1]["java_type"])
        self.assertEqual("VARCHAR(255)", attributes[2]["sql_type"])
        self.assertTrue(attributes[2]["validations"]["not_blank"])
        self.assertEqual("120", attributes[2]["validations"]["max"])
        self.assertTrue(attributes[2]["validations"]["unique"])
        self.assertTrue(attributes[2]["validations"]["index"])

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

    def test_rejects_validation_for_incompatible_type(self):
        with self.assertRaisesRegex(DefinitionError, "solo se puede aplicar a números"):
            parse_attributes("id:int, nombre:string:positive")

    def test_rejects_unknown_validation(self):
        with self.assertRaisesRegex(DefinitionError, "Validación desconocida"):
            parse_attributes("id:int, nombre:string:encrypted")

    def test_parses_decimal_as_big_decimal(self):
        attributes = parse_attributes("id:int, importe:decimal:required:positive")

        self.assertEqual("BigDecimal", attributes[1]["java_type"])
        self.assertEqual("DECIMAL(19, 4)", attributes[1]["sql_type"])

    def test_rejects_incoherent_limits(self):
        with self.assertRaisesRegex(DefinitionError, "no puede superar"):
            parse_attributes("id:int, nombre:string:min=10:max=5")

    def test_parses_text_type_without_length_limit(self):
        attributes = parse_attributes("id:int, cuerpo:text:not_blank:max=5000")

        self.assertEqual("String", attributes[1]["java_type"])
        self.assertEqual("TEXT", attributes[1]["sql_type"])

    def test_parses_decimal_with_precision_and_scale(self):
        attributes = parse_attributes(
            "id:int, importe:decimal:precision=31:scale=13"
        )

        self.assertEqual("DECIMAL(31, 13)", attributes[1]["sql_type"])
        self.assertEqual(31, attributes[1]["precision"])
        self.assertEqual(13, attributes[1]["scale"])
        self.assertNotIn("precision", attributes[1]["validations"])

    def test_rejects_precision_without_scale(self):
        with self.assertRaisesRegex(DefinitionError, "precision.*scale.*juntos"):
            parse_attributes("id:int, importe:decimal:precision=31")

    def test_rejects_precision_out_of_range(self):
        with self.assertRaisesRegex(DefinitionError, "precision"):
            parse_attributes("id:int, importe:decimal:precision=40:scale=2")

    def test_rejects_precision_on_non_decimal_type(self):
        with self.assertRaisesRegex(DefinitionError, "solo se puede aplicar a 'decimal'"):
            parse_attributes("id:int, cantidad:int:precision=10:scale=2")

    def test_parses_default_value_for_string(self):
        attributes = parse_attributes(
            "id:int, usuario:string:not_blank:default=usr"
        )

        self.assertEqual("usr", attributes[1]["validations"]["default"])

    def test_rejects_empty_default_value(self):
        with self.assertRaisesRegex(DefinitionError, "no puede estar vacío"):
            parse_attributes("id:int, usuario:string:not_blank:default=")

    def test_rejects_non_boolean_default(self):
        with self.assertRaisesRegex(DefinitionError, "'true' o 'false'"):
            parse_attributes("id:int, activo:boolean:default=quizas")

    def test_rejects_default_outside_min_max_range(self):
        with self.assertRaisesRegex(DefinitionError, "no puede superar su máximo"):
            parse_attributes("id:int, cantidad:int:max=10:default=20")

    def test_parses_datetime_default_without_colon(self):
        attributes = parse_attributes(
            "id:int, procesado_en:datetime:default=2026-01-31T153000"
        )

        self.assertEqual(
            "2026-01-31T153000", attributes[1]["validations"]["default"]
        )

    def test_rejects_malformed_datetime_default(self):
        with self.assertRaisesRegex(DefinitionError, "fecha/hora"):
            parse_attributes("id:int, procesado_en:datetime:default=2026-02-30T090000")

    def test_parses_composite_unique_group(self):
        attributes = parse_attributes(
            "id:int, refitid:string:not_blank:composite_unique=documento, "
            "refitidctrl:string:not_blank:composite_unique=documento"
        )

        self.assertEqual(
            "documento", attributes[1]["validations"]["composite_unique"]
        )
        self.assertEqual(
            "documento", attributes[2]["validations"]["composite_unique"]
        )

    def test_rejects_composite_unique_group_with_a_single_member(self):
        with self.assertRaisesRegex(DefinitionError, "al menos dos"):
            parse_attributes(
                "id:int, refitid:string:not_blank:composite_unique=documento"
            )


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
