import unittest

from crud_generator.fields import (
    generate_dto_fields,
    generate_invalid_test_dto_assignments,
    generate_test_dto_assignments,
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


if __name__ == "__main__":
    unittest.main()
