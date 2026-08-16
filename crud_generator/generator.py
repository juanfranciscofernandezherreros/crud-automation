"""Orquestación de la generación de un proyecto CRUD."""

import os

from .architectures import (
    DEFAULT_BASE_PACKAGE,
    PORTS_ARCHITECTURES,
    build_ports_architectures,
    normalize_architecture,
)
from .fields import (
    compute_inverse_relations,
    exceeds_constructor_param_limit,
    generate_dto_fields,
    generate_entity_fields,
    generate_enum_import_lines,
    generate_invalid_test_dto_assignments,
    generate_specification_filter_cases,
    generate_table_unique_constraints_annotation,
    generate_test_dto_assignments,
    get_enum_types,
    has_default,
    has_required_input,
)
from .parsing import DEFAULT_ENDPOINTS, DefinitionError, normalize_entity_name, parse_attributes
from . import documentation, migrations, shared_templates, templates
from .observability import write_observability_stack as _write_observability_stack
from .writer import write_file as _write_file


def _guard_existing_directory(base_dir, overwrite):
    if os.path.isdir(base_dir) and not overwrite:
        raise DefinitionError(
            f"El directorio '{base_dir}' ya existe. Vuelve a ejecutar con --force "
            "para regenerarlo (los ficheros que ya no formen parte de la entidad "
            "no se borran, y las migraciones ya aplicadas se conservan; ver "
            "'migraciones incrementales' en la documentacion generada)."
        )


def generate_project(
    entity_name,
    attrs_str,
    architecture="layered",
    base_package=None,
    endpoints=None,
    overwrite=False,
    custom_endpoints=None,
):
    entity_name = normalize_entity_name(entity_name)
    architecture = normalize_architecture(architecture)
    base_package = base_package or DEFAULT_BASE_PACKAGE
    if architecture in PORTS_ARCHITECTURES:
        from .ports_generator import generate_ports_project_from_attrs

        attrs = parse_attributes(attrs_str)
        layout = build_ports_architectures(base_package)[architecture]
        return generate_ports_project_from_attrs(
            entity_name, attrs, layout, attrs_str, base_package, endpoints, overwrite,
            custom_endpoints=custom_endpoints,
        )
    return generate_layered_project(
        entity_name, attrs_str, base_package, endpoints, overwrite,
        custom_endpoints=custom_endpoints,
    )


def generate_project_from_json(json_path, architecture_override=None, overwrite=False):
    """Igual que generate_project(), pero leyendo entidad(es) y campos de un JSON.
    Si el JSON define varias entidades ('entities'), delega en el generador
    multi-entidad correspondiente a la arquitectura elegida."""
    from .json_schema import is_multi_entity_document, load_entities_schema, load_schema

    if is_multi_entity_document(json_path):
        (
            project_name,
            architecture_from_json,
            base_package,
            endpoints,
            entities,
        ) = load_entities_schema(json_path)
        architecture = normalize_architecture(
            architecture_override or architecture_from_json or "layered"
        )
        base_package = base_package or DEFAULT_BASE_PACKAGE
        command_hint = f"__JSON__:{json_path}"
        if architecture in PORTS_ARCHITECTURES:
            from .ports_generator import generate_multi_entity_ports_project

            layout = build_ports_architectures(base_package)[architecture]
            return generate_multi_entity_ports_project(
                project_name, entities, layout, command_hint, base_package, endpoints, overwrite
            )
        return generate_multi_entity_layered_project(
            project_name, entities, command_hint, base_package, endpoints, overwrite
        )

    (
        entity_name,
        architecture_from_json,
        base_package,
        endpoints,
        attrs,
        custom_endpoints,
    ) = load_schema(json_path)
    entity_name = normalize_entity_name(entity_name)
    architecture = normalize_architecture(
        architecture_override or architecture_from_json or "layered"
    )
    base_package = base_package or DEFAULT_BASE_PACKAGE
    command_hint = f"__JSON__:{json_path}"
    if architecture in PORTS_ARCHITECTURES:
        from .ports_generator import generate_ports_project_from_attrs

        layout = build_ports_architectures(base_package)[architecture]
        return generate_ports_project_from_attrs(
            entity_name, attrs, layout, command_hint, base_package, endpoints, overwrite,
            custom_endpoints=custom_endpoints,
        )
    return generate_layered_project_from_attrs(
        entity_name, attrs, command_hint, base_package, endpoints, overwrite,
        custom_endpoints=custom_endpoints,
    )


def generate_layered_project(
    entity_name, attrs_str, base_package=None, endpoints=None, overwrite=False,
    custom_endpoints=None,
):
    attrs = parse_attributes(attrs_str)
    return generate_layered_project_from_attrs(
        entity_name, attrs, attrs_str, base_package, endpoints, overwrite,
        custom_endpoints=custom_endpoints,
    )


def _make_write_file(base_package):
    def write_file(path, content):
        if base_package != DEFAULT_BASE_PACKAGE:
            content = content.replace(DEFAULT_BASE_PACKAGE, base_package)
        _write_file(path, content)

    return write_file


def _write_layered_scaffolding(write_file, base_dir, project_lower, base_package, endpoints):
    """Ficheros de proyecto que se escriben una sola vez, sean una o varias
    entidades: build, Docker, CI, observabilidad, config compartida."""
    write_file(f"{base_dir}/pom.xml", templates.get_pom_xml(project_lower))
    write_file(f"{base_dir}/Dockerfile", templates.DOCKERFILE)
    write_file(
        f"{base_dir}/docker-compose.yml", templates.get_docker_compose(project_lower)
    )
    write_file(f"{base_dir}/.env.example", templates.get_env_example())
    write_file(f"{base_dir}/.env", templates.get_env_default())
    write_file(f"{base_dir}/.gitignore", templates.GITIGNORE)
    write_file(
        f"{base_dir}/.github/workflows/ci.yml",
        templates.get_github_actions_workflow(project_lower),
    )
    res_base = f"{base_dir}/src/main/resources"
    write_file(
        f"{res_base}/application.yml", templates.get_application_yml(project_lower)
    )
    write_file(
        f"{res_base}/logback-spring.xml",
        templates.get_logback_spring_xml(project_lower),
    )
    _write_observability_stack(write_file, base_dir, project_lower, project_lower)

    package_path = base_package.replace(".", "/")
    java_base = f"{base_dir}/src/main/java/{package_path}"
    write_file(f"{java_base}/CrudApplication.java", templates.APP_MAIN)
    write_file(
        f"{java_base}/configuration/JpaAuditingConfiguration.java",
        templates.AUDITING_CONFIG,
    )
    write_file(
        f"{java_base}/configuration/SecurityConfiguration.java",
        templates.SECURITY_CONFIG,
    )
    write_file(
        f"{java_base}/configuration/RateLimitFilter.java", templates.RATE_LIMIT_FILTER
    )
    write_file(
        f"{java_base}/configuration/IdempotencyService.java",
        templates.IDEMPOTENCY_SERVICE,
    )
    write_file(
        f"{java_base}/exception/GlobalExceptionHandler.java", templates.get_exception_handler()
    )
    write_file(
        f"{java_base}/exception/ResourceNotFoundException.java", templates.EXCEPTION_CLASS
    )

    test_base = f"{base_dir}/src/test/java/{package_path}"
    write_file(
        f"{test_base}/cucumber/RunCucumberTest.java", templates.get_cucumber_runner()
    )
    write_file(
        f"{test_base}/cucumber/CucumberSpringConfiguration.java",
        templates.get_cucumber_spring_configuration(),
    )


def _write_layered_entity(
    write_file, base_dir, base_package, entity_name, attrs, endpoints, inverse_relations=None,
    custom_endpoints=None,
):
    """Todos los ficheros propios de UNA entidad: migracion, entidad JPA (+enums),
    repositorio, specification, DTOs, mapper, service, controller y sus tests
    (unitarios). Los campos 'reference' generan @ManyToOne y se resuelven en el
    service contra el repositorio de la entidad referenciada.

    inverse_relations: [(entidad_que_me_referencia, campo_en_esa_entidad), ...]
    (ver fields.compute_inverse_relations) — el lado 'uno' de esas 'reference'
    recibe ademas un @OneToMany de solo lectura.

    custom_endpoints: endpoints de negocio ajenos al CRUD fijo, ver
    parsing.normalize_custom_endpoints."""
    inverse_relations = inverse_relations or []
    custom_endpoints = custom_endpoints or []
    entity_lower = entity_name.lower()
    package_path = base_package.replace(".", "/")
    java_base = f"{base_dir}/src/main/java/{package_path}"
    res_base = f"{base_dir}/src/main/resources"
    test_base = f"{base_dir}/src/test/java/{package_path}"
    table_name = f"{entity_lower}s"

    migrations.write_migration(
        res_base, entity_name, entity_lower, table_name, attrs, write_file,
        templates.get_sql_migration,
    )

    write_file(
        f"{java_base}/entity/{entity_name}.java",
        templates.get_entity(
            entity_name,
            entity_lower,
            generate_entity_fields(attrs, inverse_relations=inverse_relations),
            generate_table_unique_constraints_annotation(attrs),
            has_default(attrs),
            not exceeds_constructor_param_limit(attrs),
            bool(inverse_relations),
        ),
    )
    for enum_class, enum_values in get_enum_types(attrs).items():
        write_file(
            f"{java_base}/entity/{enum_class}.java",
            templates.get_enum_class(enum_class, enum_values),
        )
    enum_import_lines = generate_enum_import_lines(attrs, "com.example.crud.entity")

    write_file(
        f"{java_base}/repository/{entity_name}Repository.java",
        templates.get_repository(entity_name),
    )
    write_file(
        f"{java_base}/specification/{entity_name}Specifications.java",
        templates.get_specification(
            entity_name, generate_specification_filter_cases(attrs)
        ),
    )

    dto_definitions = [
        (
            "CreateDTO",
            generate_dto_fields(
                attrs, ignore_id=True, ignore_audit=True, validation_mode="write"
            ),
        ),
        (
            "UpdateDTO",
            generate_dto_fields(
                attrs, ignore_id=True, ignore_audit=True, validation_mode="write"
            ),
        ),
        (
            "PatchDTO",
            generate_dto_fields(
                attrs, ignore_id=True, ignore_audit=True, validation_mode="patch"
            ),
        ),
        ("ResponseDTO", f"{generate_dto_fields(attrs)}\n    private Long version;"),
    ]
    for suffix, fields in dto_definitions:
        class_name = f"{entity_name}{suffix}"
        write_file(
            f"{java_base}/dto/{class_name}.java",
            templates.get_dto(class_name, fields, enum_import_lines),
        )

    for endpoint in custom_endpoints:
        for suffix, endpoint_fields in (
            ("RequestDTO", endpoint["request_fields"]),
            ("ResponseDTO", endpoint["response_fields"]),
        ):
            if not endpoint_fields:
                continue
            class_name = f"{entity_name}{endpoint['pascal_name']}{suffix}"
            write_file(
                f"{java_base}/dto/{class_name}.java",
                shared_templates.render_dto_class(
                    "com.example.crud.dto", class_name, generate_dto_fields(endpoint_fields)
                ),
            )

    reference_attrs = [attr for attr in attrs if attr["type"] == "reference"]
    generated_java_files = {
        f"mapper/{entity_name}Mapper.java": templates.get_mapper(
            entity_name, reference_attrs
        ),
        f"service/{entity_name}Service.java": templates.get_service(
            entity_name, custom_endpoints
        ),
        f"service/impl/{entity_name}ServiceImpl.java": templates.get_service_impl(
            entity_name, reference_attrs, custom_endpoints
        ),
        f"controller/{entity_name}Controller.java": templates.get_controller(
            entity_name, entity_lower, endpoints, custom_endpoints
        ),
    }
    for relative_path, content in generated_java_files.items():
        write_file(f"{java_base}/{relative_path}", content)

    write_file(
        f"{test_base}/service/{entity_name}ServiceTest.java",
        templates.get_service_test(entity_name),
    )
    write_file(
        f"{test_base}/controller/{entity_name}ControllerTest.java",
        templates.get_controller_test(
            entity_name,
            entity_lower,
            generate_test_dto_assignments(attrs),
            has_required_input(attrs),
            generate_invalid_test_dto_assignments(attrs),
            endpoints,
            enum_import_lines,
        ),
    )

    has_reference = bool(reference_attrs)
    write_file(
        f"{base_dir}/src/test/resources/features/{entity_lower}.feature",
        templates.get_cucumber_feature(entity_name, entity_lower, endpoints, has_reference),
    )
    write_file(
        f"{test_base}/cucumber/{entity_name}Steps.java",
        templates.get_cucumber_steps(
            entity_name,
            entity_lower,
            generate_test_dto_assignments(attrs, variable_name="dto"),
            has_required_input(attrs),
            endpoints,
            enum_import_lines,
        ),
    )


def generate_layered_project_from_attrs(
    entity_name, attrs, attrs_str, base_package=None, endpoints=None, overwrite=False,
    custom_endpoints=None,
):
    base_package = base_package or DEFAULT_BASE_PACKAGE
    endpoints = endpoints or list(DEFAULT_ENDPOINTS)
    write_file = _make_write_file(base_package)

    entity_lower = entity_name.lower()
    base_dir = f"crud-{entity_lower}"
    _guard_existing_directory(base_dir, overwrite)

    _write_layered_scaffolding(write_file, base_dir, entity_lower, base_package, endpoints)
    write_file(
        f"{base_dir}/docs/index.html",
        documentation.get_documentation_html(
            entity_name, entity_lower, "layered", attrs, attrs_str,
            base_package, endpoints,
        ),
    )
    _write_layered_entity(
        write_file, base_dir, base_package, entity_name, attrs, endpoints,
        custom_endpoints=custom_endpoints,
    )

    test_base = f"{base_dir}/src/test/java/{base_package.replace('.', '/')}"
    write_file(
        f"{test_base}/integration/PostgreSQLIntegrationTest.java",
        templates.get_postgres_integration_test(entity_lower),
    )

    return base_dir


def generate_multi_entity_layered_project(
    project_name, entities, attrs_str, base_package=None, endpoints=None, overwrite=False
):
    """entities: [(entity_name, attrs, custom_endpoints), ...] ya en orden
    topologico (ver json_schema.load_entities_schema): una entidad referenciada
    por otra se genera (y migra) antes que quien la referencia."""
    base_package = base_package or DEFAULT_BASE_PACKAGE
    endpoints = endpoints or list(DEFAULT_ENDPOINTS)
    write_file = _make_write_file(base_package)

    project_lower = project_name.lower()
    base_dir = f"crud-{project_lower}"
    _guard_existing_directory(base_dir, overwrite)

    _write_layered_scaffolding(write_file, base_dir, project_lower, base_package, endpoints)

    inverse_relations = compute_inverse_relations(
        [(entity_name, attrs) for entity_name, attrs, _ in entities]
    )
    doc_links = []
    for entity_name, attrs, custom_endpoints in entities:
        entity_lower = entity_name.lower()
        write_file(
            f"{base_dir}/docs/{entity_lower}.html",
            documentation.get_documentation_html(
                entity_name, entity_lower, "layered", attrs, attrs_str,
                base_package, endpoints,
            ),
        )
        doc_links.append(f'<li><a href="{entity_lower}.html">{entity_name}</a></li>')
        _write_layered_entity(
            write_file, base_dir, base_package, entity_name, attrs, endpoints,
            inverse_relations.get(entity_name, []), custom_endpoints=custom_endpoints,
        )

    write_file(
        f"{base_dir}/docs/index.html",
        "<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\">"
        f"<title>{project_name}</title></head><body>"
        f"<h1>{project_name}</h1><p>Entidades generadas en este proyecto:</p>"
        f"<ul>{''.join(doc_links)}</ul></body></html>",
    )

    first_entity_lower = entities[0][0].lower()
    test_base = f"{base_dir}/src/test/java/{base_package.replace('.', '/')}"
    write_file(
        f"{test_base}/integration/PostgreSQLIntegrationTest.java",
        templates.get_postgres_integration_test(first_entity_lower),
    )

    return base_dir
