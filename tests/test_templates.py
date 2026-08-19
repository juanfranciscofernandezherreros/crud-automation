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


class DockerEnvFileTest(unittest.TestCase):
    def test_env_example_defines_every_variable_required_by_docker_compose(self):
        compose = templates.get_docker_compose("producto")
        env_example = templates.get_env_example()

        required_vars = [
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "APP_SECURITY_USER",
            "APP_SECURITY_PASSWORD",
        ]
        for var in required_vars:
            with self.subTest(var=var):
                self.assertIn(f"${{{var}:?", compose)
                self.assertIn(f"{var}=", env_example)

    def test_env_default_is_ready_to_use_without_manual_copy(self):
        env_default = templates.get_env_default()

        required_vars = [
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "APP_SECURITY_USER",
            "APP_SECURITY_PASSWORD",
        ]
        for var in required_vars:
            with self.subTest(var=var):
                self.assertIn(f"{var}=", env_default)

    def test_gitignore_excludes_env_and_build_output(self):
        self.assertIn(".env", templates.GITIGNORE)
        self.assertIn("target/", templates.GITIGNORE)


class GithubActionsWorkflowTest(unittest.TestCase):
    def test_workflow_runs_maven_verify_with_matching_java_version(self):
        workflow = templates.get_github_actions_workflow("producto")

        self.assertIn("mvn --batch-mode --no-transfer-progress verify", workflow)
        self.assertIn('java-version: "21"', workflow)
        self.assertIn("crud-producto-test-results", workflow)


class ObservabilityStackTest(unittest.TestCase):
    def test_docker_compose_wires_prometheus_loki_and_grafana(self):
        compose = templates.get_docker_compose("producto")

        for service in ("prometheus:", "loki:", "grafana:"):
            self.assertIn(service, compose)
        self.assertIn("./observability/prometheus.yml", compose)
        self.assertIn("./observability/loki-config.yml", compose)
        self.assertIn("./observability/grafana/provisioning", compose)

    def test_prometheus_scrapes_the_app_actuator_endpoint(self):
        config = templates.get_prometheus_config("producto")
        self.assertIn("targets: [\"app:8080\"]", config)
        self.assertIn("/actuator/prometheus", config)

    def test_grafana_datasources_point_to_compose_service_names(self):
        datasources = templates.get_grafana_datasources()
        self.assertIn("http://prometheus:9090", datasources)
        self.assertIn("http://loki:3100", datasources)

    def test_business_dashboard_is_valid_json_scoped_to_the_entity(self):
        import json

        dashboard = json.loads(
            templates.get_grafana_business_dashboard("Producto", "producto")
        )
        self.assertEqual("producto-overview", dashboard["uid"])
        self.assertEqual(4, len(dashboard["panels"]))

    def test_logback_ships_logs_to_loki_labeled_with_the_service_name(self):
        logback = templates.get_logback_spring_xml("producto")
        self.assertIn("com.github.loki4j.logback.Loki4jAppender", logback)
        self.assertIn("service_name=producto-service", logback)

    def test_pom_declares_loki_appender_dependency(self):
        pom = templates.get_pom_xml("producto")
        self.assertIn("loki-logback-appender", pom)


class GeneratedXmlIsWellFormedTest(unittest.TestCase):
    """Una plantilla f-string con una etiqueta de cierre equivocada (p.ej.
    '<artifactId>x</groupId>') no falla en Python: solo se ve al intentar
    compilar el proyecto generado con Maven. Parsear el XML aqui lo detecta
    en segundos en vez de esperar a una compilacion real."""

    def test_pom_xml_is_well_formed(self):
        import xml.etree.ElementTree as ET

        ET.fromstring(templates.get_pom_xml("producto"))

    def test_logback_spring_xml_is_well_formed(self):
        import xml.etree.ElementTree as ET

        ET.fromstring(templates.get_logback_spring_xml("producto"))


class CucumberAllureTest(unittest.TestCase):
    def test_pom_declares_cucumber_and_allure_dependencies(self):
        pom = templates.get_pom_xml("producto")
        for artifact in (
            "cucumber-java", "cucumber-junit-platform-engine", "cucumber-spring",
            "allure-cucumber7-jvm", "rest-assured", "allure-maven",
            "testcontainers-bom",
        ):
            self.assertIn(artifact, pom)

    def test_runner_class_name_ends_in_test_so_surefire_picks_it_up(self):
        runner = templates.get_cucumber_runner()
        self.assertIn("class RunCucumberTest", runner)
        self.assertIn('@SelectClasspathResource("features")', runner)
        self.assertIn("AllureCucumber7Jvm", runner)

    def test_pom_excludes_cucumber_from_the_default_run_but_includes_it_under_profile(self):
        # RunCucumberTest coincide con el patron *Test.java de Surefire, asi que
        # sin excluirlo explicitamente 'mvn verify' lo ejecutaria siempre, y
        # fallaria en cualquier maquina donde Testcontainers no pueda hablar con
        # Docker (frecuente en Windows con Docker Desktop via named pipe) aunque
        # el resto de tests no necesiten Docker en absoluto.
        pom = templates.get_pom_xml("producto")
        self.assertIn("<exclude>**/RunCucumberTest.java</exclude>", pom)
        self.assertIn('<id>cucumber</id>', pom)

    def test_ci_workflow_runs_cucumber_as_a_separate_opt_in_step(self):
        workflow = templates.get_github_actions_workflow("producto")
        self.assertIn("mvn --batch-mode --no-transfer-progress verify", workflow)
        self.assertIn("-Pcucumber -Dtest=RunCucumberTest", workflow)

    def test_feature_skips_happy_path_create_when_entity_has_a_reference(self):
        with_reference = templates.get_cucumber_feature(
            "Pedido", "pedido", ["list", "get", "create"],
            has_reference=True, has_required_fields=True,
        )
        without_reference = templates.get_cucumber_feature(
            "Producto", "producto", ["list", "get", "create"],
            has_reference=False, has_required_fields=True,
        )

        self.assertNotIn("Crear un pedido valido", with_reference)
        self.assertIn("Crear un producto valido", without_reference)
        self.assertIn("Crear un pedido sin campos obligatorios", with_reference)

    def test_feature_skips_missing_fields_scenario_when_entity_has_no_required_fields(self):
        # Con cero campos obligatorios, un cuerpo vacio es una entrada valida
        # (la API responde 201, no 400): incluir este escenario generaria un
        # test que siempre falla contra el comportamiento correcto de la API.
        feature = templates.get_cucumber_feature(
            "Producto", "producto", ["list", "get", "create"],
            has_reference=False, has_required_fields=False,
        )

        self.assertNotIn("sin campos obligatorios", feature)

    def test_steps_import_the_java_types_used_by_generated_test_values(self):
        # get_valid_test_value puede emitir BigDecimal/LocalDate/LocalDateTime
        # literales para cualquier entidad con esos tipos; sin el import el
        # fichero generado no compila.
        steps = templates.get_cucumber_steps(
            "Producto", "producto", "", True, ["list", "get", "create"]
        )
        self.assertIn("import java.math.BigDecimal;", steps)
        self.assertIn("import java.time.LocalDate;", steps)
        self.assertIn("import java.time.LocalDateTime;", steps)

    def test_steps_use_the_same_variable_name_the_dto_assignments_target(self):
        from crud_generator.fields import generate_test_dto_assignments
        from crud_generator.parsing import parse_attributes

        attrs = parse_attributes("id:int, nombre:string:required")
        assignments = generate_test_dto_assignments(attrs, variable_name="dto")
        steps = templates.get_cucumber_steps(
            "Producto", "producto", assignments, True, ["list", "get", "create"]
        )

        self.assertIn("ProductoCreateDTO dto = new ProductoCreateDTO();", steps)
        self.assertIn("dto.setNombre(", steps)
        self.assertNotIn("createDTO.set", steps)


class PortsEnumAndReferenceTest(unittest.TestCase):
    """Enum y 'reference' en hexagonal/clean (ports_templates.py), la
    contraparte de lo ya cubierto para layered."""

    def setUp(self):
        from crud_generator.architectures import build_ports_architectures

        self.layout = build_ports_architectures("com.example.crud")["hexagonal"]

    def test_ports_controller_test_builds_the_dto_as_createDTO(self):
        # Bug real encontrado al extender esto a ports: se paso
        # variable_name="dto" (pensado para los steps de Cucumber de
        # layered) a una llamada que en realidad alimenta
        # ports_templates.get_controller_test, cuyo test 'create_ValidInput'
        # declara la variable local como 'createDTO'. No compilaba.
        test_file = ports_templates.get_controller_test(
            "Producto", "producto", self.layout,
            "        createDTO.setNombre(\"x\");",
            True, "", ["list", "get", "create"],
        )
        self.assertIn("ProductoCreateDTO createDTO = new ProductoCreateDTO();", test_file)
        self.assertIn("createDTO.setNombre(", test_file)
        self.assertNotIn("dto.setNombre(", test_file)

    def test_ports_controller_test_covers_the_get_endpoint(self):
        # ports_templates.get_controller_test nunca tuvo el equivalente del
        # findById_ExistingId_Returns200 que templates.get_controller_test
        # (layered) sí genera para el endpoint 'get' -- un hueco de
        # cobertura real en cualquier proyecto hexagonal/clean generado,
        # no solo una diferencia cosmetica de codigo.
        test_file = ports_templates.get_controller_test(
            "Producto", "producto", self.layout, "", False, "", ["get"],
        )
        self.assertIn("findById_ExistingId_Returns200", test_file)
        self.assertIn("when(useCase.findById(1)).thenReturn(domain)", test_file)
        self.assertIn('get("/api/productos/1"', test_file)

    def test_persistence_entity_and_dto_accept_enum_import_lines(self):
        entity_file = ports_templates.get_persistence_entity(
            "Pedido", "pedido", self.layout.persistence_package, "    private Estado estado;",
            enum_import_lines="import com.example.crud.domain.model.Estado;",
        )
        dto_file = ports_templates.get_dto(
            "PedidoCreateDTO", self.layout.dto_package, "    private Estado estado;",
            enum_import_lines="import com.example.crud.domain.model.Estado;",
        )
        for generated in (entity_file, dto_file):
            self.assertIn("import com.example.crud.domain.model.Estado;", generated)

    def test_persistence_mapper_ignores_the_reference_field_both_ways(self):
        reference_attrs = [{"camel_name": "cliente", "references": "Cliente"}]
        mapper = ports_templates.get_persistence_mapper("Pedido", self.layout, reference_attrs)
        self.assertIn('@Mapping(target = "cliente", ignore = true)', mapper)
        self.assertIn(
            '@Mapping(target = "clienteId", '
            'expression = "java(entity.getCliente() != null ? '
            'entity.getCliente().getId() : null)")',
            mapper,
        )

    def test_persistence_adapter_resolves_the_reference_before_saving(self):
        reference_attrs = [{"camel_name": "cliente", "references": "Cliente"}]
        adapter = ports_templates.get_persistence_adapter("Pedido", self.layout, reference_attrs)
        self.assertIn("private final ClienteJpaRepository clienteRepository;", adapter)
        self.assertIn("jpaEntity.setCliente(resolveCliente(entity.getClienteId()));", adapter)
        self.assertIn("private ClienteJpaEntity resolveCliente(Integer clienteId)", adapter)
        self.assertIn(
            'new ResourceNotFoundException("Cliente no encontrado: " + clienteId)', adapter
        )

    def test_persistence_adapter_without_references_stays_unchanged(self):
        adapter = ports_templates.get_persistence_adapter("Producto", self.layout)
        self.assertNotIn("Repository;\n    private final", adapter)
        self.assertNotIn("resolve", adapter)


if __name__ == "__main__":
    unittest.main()
