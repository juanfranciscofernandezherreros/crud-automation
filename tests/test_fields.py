import unittest

from crud_generator.fields import (
    format_default_java_literal,
    generate_dto_fields,
    generate_entity_fields,
    generate_enum_import_lines,
    generate_invalid_test_dto_assignments,
    generate_specification_filter_cases,
    generate_sql_fields,
    generate_sql_indexes,
    generate_table_unique_constraints_annotation,
    generate_test_dto_assignments,
    get_enum_types,
    get_valid_test_value,
    has_default,
)
from crud_generator.parsing import parse_attributes, parse_attributes_from_fields


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

    def test_generates_typed_specification_filter_cases(self):
        attributes = parse_attributes(
            "id:int, nombre:string, importe:decimal:precision=10:scale=2, "
            "activo:boolean, nacimiento:date, creado:datetime"
        )

        cases = generate_specification_filter_cases(attributes)

        self.assertIn('case "nombre" -> spec = spec.and(', cases)
        self.assertIn('cb.equal(root.get("nombre"), value)', cases)
        self.assertIn('cb.equal(root.get("importe"), new BigDecimal(value))', cases)
        self.assertIn('cb.equal(root.get("activo"), Boolean.valueOf(value))', cases)
        self.assertIn('cb.equal(root.get("nacimiento"), LocalDate.parse(value))', cases)
        self.assertIn('cb.equal(root.get("creado"), LocalDateTime.parse(value))', cases)
        self.assertIn('case "id" -> spec = spec.and(', cases)


class FloatingPointSqlTypeTest(unittest.TestCase):
    def test_float_and_double_map_to_floating_point_sql_types_not_decimal(self):
        # DECIMAL es un tipo de punto fijo: Hibernate valida el esquema
        # esperando REAL/DOUBLE PRECISION para campos Java float/Double y
        # rechaza el arranque si Flyway creo la columna como DECIMAL.
        attributes = parse_attributes(
            "id:int, temperatura:float:required, humedad:double:required"
        )

        sql = generate_sql_fields(attributes)

        self.assertIn("temperatura REAL NOT NULL", sql)
        self.assertIn("humedad DOUBLE PRECISION NOT NULL", sql)
        self.assertNotIn("DECIMAL", sql)


class EnumFieldGenerationTest(unittest.TestCase):
    def _attrs(self, default=None):
        field = {
            "name": "estado",
            "type": "enum",
            "values": ["PENDIENTE", "PAGADO", "ENVIADO"],
            "required": True,
        }
        if default is not None:
            field["default"] = default
        return parse_attributes_from_fields([{"name": "id", "type": "int"}, field])

    def test_sql_adds_check_in_with_declared_values(self):
        sql = generate_sql_fields(self._attrs(), table_name="pedidos")
        self.assertIn(
            "estado VARCHAR(9) NOT NULL CHECK "
            "(estado IN ('PENDIENTE', 'PAGADO', 'ENVIADO'))",
            sql,
        )

    def test_sql_default_is_quoted_like_a_string(self):
        sql = generate_sql_fields(self._attrs(default="PENDIENTE"), table_name="pedidos")
        self.assertIn("DEFAULT 'PENDIENTE'", sql)

    def test_entity_field_gets_enumerated_annotation(self):
        entity_fields = generate_entity_fields(self._attrs(default="PENDIENTE"))
        self.assertIn("@Enumerated(EnumType.STRING)", entity_fields)
        self.assertIn("private Estado estado = Estado.PENDIENTE;", entity_fields)

    def test_java_default_literal_qualifies_the_enum_constant(self):
        attrs = self._attrs(default="PAGADO")
        estado = attrs[1]
        self.assertEqual("Estado.PAGADO", format_default_java_literal(estado))

    def test_valid_test_value_uses_first_declared_constant(self):
        attrs = self._attrs()
        estado = attrs[1]
        self.assertEqual("Estado.PENDIENTE", get_valid_test_value(estado))

    def test_enum_import_lines_reference_the_entity_package(self):
        attrs = self._attrs()
        self.assertEqual(
            "import com.example.crud.entity.Estado;",
            generate_enum_import_lines(attrs, "com.example.crud.entity"),
        )

    def test_get_enum_types_maps_class_to_declared_values(self):
        attrs = self._attrs()
        self.assertEqual(
            {"Estado": ["PENDIENTE", "PAGADO", "ENVIADO"]}, get_enum_types(attrs)
        )


class ReferenceFieldGenerationTest(unittest.TestCase):
    def _attrs(self):
        return parse_attributes_from_fields(
            [
                {"name": "id", "type": "int"},
                {
                    "name": "cliente",
                    "type": "reference",
                    "references": "Cliente",
                    "required": True,
                    "index": True,
                },
                {"name": "total", "type": "decimal", "precision": 10, "scale": 2},
            ]
        )

    def test_sql_column_is_the_id_suffixed_name_with_fk_constraint(self):
        sql = generate_sql_fields(self._attrs(), table_name="pedidos")
        self.assertIn("cliente_id INT NOT NULL REFERENCES clientes(id)", sql)

    def test_sql_index_uses_the_id_suffixed_column(self):
        indexes = generate_sql_indexes(self._attrs(), "pedidos")
        self.assertIn("idx_pedidos_cliente_id ON pedidos (cliente_id)", indexes)

    def test_layered_entity_field_holds_the_referenced_type_directly(self):
        entity_fields = generate_entity_fields(self._attrs())
        self.assertIn("@ManyToOne(fetch = FetchType.LAZY)", entity_fields)
        self.assertIn('@JoinColumn(name = "cliente_id", nullable = false)', entity_fields)
        self.assertIn("private Cliente cliente;", entity_fields)

    def test_ports_entity_field_holds_the_jpa_entity_type_with_suffix(self):
        # En hexagonal/clean la entidad JPA no puede apuntar al modelo de
        # dominio de la entidad referenciada: debe apuntar a SU entidad JPA.
        entity_fields = generate_entity_fields(self._attrs(), reference_type_suffix="JpaEntity")
        self.assertIn("private ClienteJpaEntity cliente;", entity_fields)

    def test_domain_model_holds_only_the_id_not_the_referenced_object(self):
        # El dominio (hexagonal/clean) no tiene acceso a un repositorio para
        # resolver la referencia, asi que guarda el mismo '{campo}Id' que los DTO.
        from crud_generator.fields import generate_plain_fields

        plain_fields = generate_plain_fields(self._attrs())
        self.assertIn("private Integer clienteId;", plain_fields)
        self.assertNotIn("private Cliente cliente;", plain_fields)

    def test_dto_field_is_the_id_not_the_referenced_object(self):
        dto_fields = generate_dto_fields(self._attrs(), ignore_id=True, ignore_audit=True)
        self.assertIn("private Integer clienteId;", dto_fields)
        self.assertNotIn("Cliente cliente", dto_fields)

    def test_domain_update_statements_use_the_id_suffixed_accessor(self):
        # Bug real: generaba current.setCliente(replacement.getCliente()),
        # pero el dominio solo tiene getClienteId()/setClienteId() (ver
        # generate_plain_fields) — no compilaba.
        from crud_generator.fields import generate_domain_update_statements

        update = generate_domain_update_statements(self._attrs())
        self.assertIn("current.setClienteId(replacement.getClienteId());", update)
        self.assertNotIn("getCliente()", update)
        self.assertNotIn("setCliente(", update)

        patch = generate_domain_update_statements(self._attrs(), patch=True)
        self.assertIn("if (changes.getClienteId() != null)", patch)
        self.assertIn("current.setClienteId(changes.getClienteId());", patch)


if __name__ == "__main__":
    unittest.main()
