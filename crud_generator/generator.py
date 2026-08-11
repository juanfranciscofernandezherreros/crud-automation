"""Orquestación de la generación de un proyecto CRUD."""

from .architectures import (
    DEFAULT_BASE_PACKAGE,
    PORTS_ARCHITECTURES,
    build_ports_architectures,
    normalize_architecture,
)
from .fields import (
    exceeds_constructor_param_limit,
    generate_dto_fields,
    generate_entity_fields,
    generate_invalid_test_dto_assignments,
    generate_specification_filter_cases,
    generate_sql_fields,
    generate_sql_indexes,
    generate_table_unique_constraints_annotation,
    generate_test_dto_assignments,
    has_default,
    has_required_input,
)
from .parsing import DEFAULT_ENDPOINTS, normalize_entity_name, parse_attributes
from . import documentation, templates
from .writer import write_file as _write_file


def generate_project(
    entity_name, attrs_str, architecture="layered", base_package=None, endpoints=None
):
    entity_name = normalize_entity_name(entity_name)
    architecture = normalize_architecture(architecture)
    base_package = base_package or DEFAULT_BASE_PACKAGE
    if architecture in PORTS_ARCHITECTURES:
        from .ports_generator import generate_ports_project_from_attrs

        attrs = parse_attributes(attrs_str)
        layout = build_ports_architectures(base_package)[architecture]
        return generate_ports_project_from_attrs(
            entity_name, attrs, layout, attrs_str, base_package, endpoints
        )
    return generate_layered_project(entity_name, attrs_str, base_package, endpoints)


def generate_project_from_json(json_path, architecture_override=None):
    """Igual que generate_project(), pero leyendo entidad y campos de un JSON."""
    from .json_schema import load_schema

    (
        entity_name,
        architecture_from_json,
        base_package,
        endpoints,
        attrs,
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
            entity_name, attrs, layout, command_hint, base_package, endpoints
        )
    return generate_layered_project_from_attrs(
        entity_name, attrs, command_hint, base_package, endpoints
    )


def generate_layered_project(entity_name, attrs_str, base_package=None, endpoints=None):
    attrs = parse_attributes(attrs_str)
    return generate_layered_project_from_attrs(
        entity_name, attrs, attrs_str, base_package, endpoints
    )


def generate_layered_project_from_attrs(
    entity_name, attrs, attrs_str, base_package=None, endpoints=None
):
    base_package = base_package or DEFAULT_BASE_PACKAGE
    endpoints = endpoints or list(DEFAULT_ENDPOINTS)

    def write_file(path, content):
        if base_package != DEFAULT_BASE_PACKAGE:
            content = content.replace(DEFAULT_BASE_PACKAGE, base_package)
        _write_file(path, content)

    entity_lower = entity_name.lower()
    base_dir = f"crud-{entity_lower}"
    package_path = base_package.replace(".", "/")
    java_base = f"{base_dir}/src/main/java/{package_path}"
    res_base = f"{base_dir}/src/main/resources"
    test_base = f"{base_dir}/src/test/java/{package_path}"

    table_name = f"{entity_lower}s"
    entity_fields = generate_entity_fields(attrs)
    sql_fields = generate_sql_fields(attrs, table_name)

    write_file(f"{base_dir}/pom.xml", templates.get_pom_xml(entity_lower))
    write_file(
        f"{base_dir}/docs/index.html",
        documentation.get_documentation_html(
            entity_name, entity_lower, "layered", attrs, attrs_str,
            base_package, endpoints,
        ),
    )
    write_file(f"{base_dir}/Dockerfile", templates.DOCKERFILE)
    write_file(
        f"{base_dir}/docker-compose.yml",
        templates.get_docker_compose(entity_lower),
    )
    write_file(f"{base_dir}/.env.example", templates.get_env_example())
    write_file(f"{base_dir}/.gitignore", templates.GITIGNORE)
    write_file(
        f"{res_base}/application.yml", templates.get_application_yml(entity_lower)
    )
    write_file(
        f"{res_base}/db/migration/V1__Create_Table_{entity_name}.sql",
        templates.get_sql_migration(
            entity_lower,
            sql_fields,
            generate_sql_indexes(attrs, table_name),
        ),
    )

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
        f"{java_base}/configuration/RateLimitFilter.java",
        templates.RATE_LIMIT_FILTER,
    )
    write_file(
        f"{java_base}/configuration/IdempotencyService.java",
        templates.IDEMPOTENCY_SERVICE,
    )
    write_file(
        f"{java_base}/exception/GlobalExceptionHandler.java",
        templates.EXCEPTION_HANDLER,
    )
    write_file(
        f"{java_base}/exception/ResourceNotFoundException.java",
        templates.EXCEPTION_CLASS,
    )
    write_file(
        f"{java_base}/entity/{entity_name}.java",
        templates.get_entity(
            entity_name,
            entity_lower,
            entity_fields,
            generate_table_unique_constraints_annotation(attrs),
            has_default(attrs),
            not exceeds_constructor_param_limit(attrs),
        ),
    )
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
            templates.get_dto(class_name, fields),
        )

    generated_java_files = {
        f"mapper/{entity_name}Mapper.java": templates.get_mapper(entity_name),
        f"service/{entity_name}Service.java": templates.get_service(entity_name),
        f"service/impl/{entity_name}ServiceImpl.java": templates.get_service_impl(
            entity_name
        ),
        f"controller/{entity_name}Controller.java": templates.get_controller(
            entity_name, entity_lower, endpoints
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
        ),
    )
    write_file(
        f"{test_base}/integration/PostgreSQLIntegrationTest.java",
        templates.get_postgres_integration_test(entity_lower),
    )

    return base_dir
