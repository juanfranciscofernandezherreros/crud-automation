import unittest

from crud_generator import ports_templates, templates
from crud_generator.fields import exceeds_constructor_param_limit
from crud_generator.parsing import parse_attributes


class ConstructorParamLimitTest(unittest.TestCase):
    def test_small_entity_does_not_exceed_the_limit(self):
        attrs = parse_attributes("id:int, nombre:string")

        self.assertFalse(exceeds_constructor_param_limit(attrs))

    def test_very_wide_entity_exceeds_the_limit(self):
        fields = ", ".join(f"campo{i}:string" for i in range(260))
        attrs = parse_attributes(f"id:int, {fields}")

        self.assertTrue(exceeds_constructor_param_limit(attrs))


class EntityTemplateBuilderTest(unittest.TestCase):
    def test_includes_all_args_and_builder_by_default(self):
        entity = templates.get_entity("Producto", "producto", "    private Integer id;")

        self.assertIn("@AllArgsConstructor", entity)
        self.assertIn("@Builder", entity)

    def test_omits_all_args_and_builder_for_wide_entities(self):
        entity = templates.get_entity(
            "Producto",
            "producto",
            "    private Integer id;",
            include_all_args_builder=False,
        )

        self.assertNotIn("@AllArgsConstructor", entity)
        self.assertNotIn("@Builder", entity)
        # El resto de la generacion JPA sigue intacta.
        self.assertIn("@NoArgsConstructor", entity)
        self.assertIn("@EntityListeners", entity)

    def test_ports_persistence_entity_omits_builder_for_wide_entities(self):
        entity = ports_templates.get_persistence_entity(
            "Producto",
            "producto",
            "com.example.crud.adapter.out.persistence",
            "    private Integer id;",
            include_all_args_builder=False,
        )

        self.assertNotIn("@AllArgsConstructor", entity)
        self.assertNotIn("@Builder", entity)

    def test_ports_domain_omits_builder_for_wide_entities(self):
        domain = ports_templates.get_domain(
            "Producto",
            "com.example.crud.domain.model",
            "    private Integer id;",
            include_all_args_builder=False,
        )

        self.assertNotIn("@AllArgsConstructor", domain)
        self.assertNotIn("@Builder", domain)
        self.assertIn("@NoArgsConstructor", domain)


if __name__ == "__main__":
    unittest.main()
