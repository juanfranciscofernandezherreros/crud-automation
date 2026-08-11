import unittest

from crud_generator.fields import (
    generate_dto_fields,
    generate_entity_fields,
    generate_invalid_test_dto_assignments,
    generate_sql_fields,
    generate_sql_indexes,
    generate_table_unique_constraints_annotation,
    generate_test_dto_assignments,
    has_default,
)
from crud_generator.parsing import parse_attributes


class DtoFieldsTest(unittest.TestCase):
    def setUp(self):
        self.attributes = parse_attributes(
            "id:int, nombre_completo:string:not_blank:min=2:max=80, "
            "saldo:double:required:positive, nacimiento:date:required, "
            "creado_en:datetime"
        )

    def test_generates_write_validations_and_keeps_business_dates(self):
        fields = generate_dto_fields(
            self.attributes,
            ignore_id=True,
            ignore_audit=True,
            validation_mode="write",
        )

        self.assertIn("@NotBlank", fields)
        self.assertIn("@Size(min = 2, max = 80)", fields)
        self.assertIn("@Positive", fields)
        self.assertIn("private LocalDate nacimiento;", fields)
        self.assertNotIn("creadoEn", fields)

    def test_patch_does_not_require_omitted_fields(self):
        fields = generate_dto_fields(
            self.attributes,
            ignore_id=True,
            ignore_audit=True,
            validation_mode="patch",
        )

        self.assertIn("@Pattern", fields)
        self.assertNotIn("@NotNull", fields)
        self.assertNotIn("@NotBlank", fields)

    def test_generates_compilable_test_values(self):
        assignments = generate_test_dto_assignments(self.attributes)

        self.assertIn('createDTO.setNombreCompleto("xx");', assignments)
        self.assertIn("createDTO.setSaldo(1d);", assignments)
        self.assertIn("createDTO.setNacimiento(LocalDate.now());", assignments)

    def test_generates_an_invalid_numeric_value_for_controller_tests(self):
        assignments = generate_invalid_test_dto_assignments(self.attributes)

        self.assertIn("createDTO.setSaldo(-1d);", assignments)

    def test_generates_big_decimal_values_and_database_constraints(self):
        attributes = parse_attributes(
            "id:int, referencia:string:not_blank:max=64:unique:index, "
            "importe:decimal:required:positive:min=0.01:max=999.99, "
            "estado:string:index"
        )

        assignments = generate_test_dto_assignments(attributes)
        sql = generate_sql_fields(attributes)
        indexes = generate_sql_indexes(attributes, "operaciones")

        self.assertIn('new BigDecimal("1")', assignments)
        self.assertIn("referencia VARCHAR(64) NOT NULL UNIQUE", sql)
        self.assertIn("CHECK (btrim(referencia) <> '')", sql)
        self.assertIn("importe DECIMAL(19, 4) NOT NULL", sql)
        self.assertIn("CHECK (importe > 0)", sql)
        self.assertIn("version BIGINT NOT NULL DEFAULT 0", sql)
        self.assertNotIn("idx_operaciones_referencia", indexes)
        self.assertIn("idx_operaciones_estado", indexes)

    def test_generates_default_value_default_and_dynamic_insert_flag(self):
        attributes = parse_attributes(
            "id:int, lstusr:string:not_blank:default=usr, "
            "activo:boolean:default=false:required"
        )

        sql = generate_sql_fields(attributes)
        entity = generate_entity_fields(attributes)

        self.assertIn("lstusr VARCHAR(255) NOT NULL DEFAULT 'usr'", sql)
        self.assertIn("activo BOOLEAN NOT NULL DEFAULT false", sql)
        self.assertIn('private String lstusr = "usr";', entity)
        self.assertIn("private Boolean activo = false;", entity)
        self.assertTrue(has_default(attributes))

    def test_generates_text_column_without_varchar_and_with_length_check(self):
        attributes = parse_attributes("id:int, cuerpo:text:not_blank:max=5000")

        sql = generate_sql_fields(attributes)

        self.assertIn("cuerpo TEXT NOT NULL", sql)
        self.assertNotIn("VARCHAR", sql)
        self.assertIn("CHECK (char_length(cuerpo) <= 5000)", sql)

    def test_generates_parametrized_decimal_column(self):
        attributes = parse_attributes(
            "id:int, importe:decimal:precision=31:scale=13"
        )

        sql = generate_sql_fields(attributes)

        self.assertIn("importe DECIMAL(31, 13)", sql)

    def test_generates_composite_unique_constraint_and_table_annotation(self):
        attributes = parse_attributes(
            "id:int, refitid:string:not_blank:composite_unique=documento, "
            "refitidctrl:string:not_blank:composite_unique=documento"
        )

        sql = generate_sql_fields(attributes, table_name="documentos")
        annotation = generate_table_unique_constraints_annotation(attributes)

        self.assertIn(
            "CONSTRAINT uq_documentos_documento UNIQUE (refitid, refitidctrl)", sql
        )
        self.assertIn(
            '@UniqueConstraint(name = "uq_documento", '
            'columnNames = {"refitid", "refitidctrl"})',
            annotation,
        )


if __name__ == "__main__":
    unittest.main()
