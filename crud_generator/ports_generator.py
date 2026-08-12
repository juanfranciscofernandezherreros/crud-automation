"""Generación de arquitecturas hexagonal y clean."""

import os

from . import documentation, migrations, ports_templates, templates
from .architectures import DEFAULT_BASE_PACKAGE
from .observability import write_observability_stack
from .fields import (
    exceeds_constructor_param_limit,
    generate_domain_update_statements,
    generate_dto_fields,
    generate_entity_fields,
    generate_enum_import_lines,
    generate_invalid_test_dto_assignments,
    generate_plain_fields,
    generate_specification_filter_cases,
    generate_table_unique_constraints_annotation,
    generate_test_dto_assignments,
    get_enum_types,
    has_default,
    has_required_input,
)
from .parsing import DEFAULT_ENDPOINTS, DefinitionError, parse_attributes
from .writer import write_file as _write_file


def _guard_existing_directory(base_dir, overwrite):
    if os.path.isdir(base_dir) and not overwrite:
        raise DefinitionError(
            f"El directorio '{base_dir}' ya existe. Vuelve a ejecutar con --force "
            "para regenerarlo (los ficheros que ya no formen parte de la entidad "
            "no se borran, y las migraciones ya aplicadas se conservan; ver "
            "'migraciones incrementales' en la documentacion generada)."
        )


def package_path(package):
    return package.replace(".", "/")


def java_path(java_root, package, filename):
    return f"{java_root}/{package_path(package)}/{filename}"


def _make_write_file(base_package):
    def write_file(path, content):
        if base_package != DEFAULT_BASE_PACKAGE:
            content = content.replace(DEFAULT_BASE_PACKAGE, base_package)
        _write_file(path, content)

    return write_file


def generate_ports_project(entity_name, attrs_str, layout, overwrite=False):
    attrs = parse_attributes(attrs_str)
    return generate_ports_project_from_attrs(
        entity_name, attrs, layout, attrs_str, overwrite=overwrite
    )


def _write_ports_scaffolding(write_file, base_dir, project_lower, base_package, main_java, resources):
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
    write_file(
        f"{resources}/application.yml", templates.get_application_yml(project_lower)
    )
    write_file(
        f"{resources}/logback-spring.xml",
        templates.get_logback_spring_xml(project_lower),
    )
    write_observability_stack(write_file, base_dir, project_lower, project_lower)

    write_file(
        java_path(main_java, "com.example.crud", "CrudApplication.java"),
        templates.APP_MAIN,
    )
    write_file(
        java_path(
            main_java, "com.example.crud.configuration", "JpaAuditingConfiguration.java"
        ),
        templates.AUDITING_CONFIG,
    )
    write_file(
        java_path(
            main_java, "com.example.crud.configuration", "SecurityConfiguration.java"
        ),
        templates.SECURITY_CONFIG,
    )
    write_file(
        java_path(main_java, "com.example.crud.configuration", "RateLimitFilter.java"),
        templates.RATE_LIMIT_FILTER,
    )
    write_file(
        java_path(
            main_java, "com.example.crud.configuration", "IdempotencyService.java"
        ),
        templates.IDEMPOTENCY_SERVICE,
    )


def _write_ports_entity(
    write_file, main_java, test_java, resources, base_package, entity_name, attrs, layout, endpoints
):
    """Todos los ficheros propios de UNA entidad: migracion, dominio, entidad
    JPA (+enums), puertos, service, DTOs, mappers, adaptador de persistencia,
    controller y sus tests. Los campos 'reference' generan @ManyToOne en la
    entidad JPA (el dominio solo guarda el '{campo}Id', ver
    fields.generate_plain_fields) y se resuelven en el adaptador de
    persistencia contra el repositorio JPA de la entidad referenciada."""
    entity_lower = entity_name.lower()
    table_name = f"{entity_lower}s"

    migrations.write_migration(
        resources, entity_name, entity_lower, table_name, attrs, write_file,
        templates.get_sql_migration,
    )

    include_all_args_builder = not exceeds_constructor_param_limit(attrs)
    write_file(
        java_path(main_java, layout.domain_package, f"{entity_name}.java"),
        ports_templates.get_domain(
            entity_name, layout.domain_package, generate_plain_fields(attrs),
            include_all_args_builder,
        ),
    )
    for enum_class, enum_values in get_enum_types(attrs).items():
        write_file(
            java_path(main_java, layout.domain_package, f"{enum_class}.java"),
            templates.get_enum_class(enum_class, enum_values, layout.domain_package),
        )
    enum_import_lines = generate_enum_import_lines(attrs, layout.domain_package)

    write_file(
        java_path(main_java, layout.domain_package, "PageQuery.java"),
        ports_templates.get_page_query(layout.domain_package),
    )
    write_file(
        java_path(main_java, layout.domain_package, "PageResult.java"),
        ports_templates.get_page_result(layout.domain_package),
    )
    write_file(
        java_path(main_java, "com.example.crud.configuration", "UseCaseConfiguration.java"),
        ports_templates.get_use_case_configuration(entity_name, layout),
    )
    write_file(
        java_path(main_java, layout.input_package, f"{entity_name}UseCase.java"),
        ports_templates.get_input_port(entity_name, layout),
    )
    write_file(
        java_path(main_java, layout.output_package, f"{entity_name}PersistencePort.java"),
        ports_templates.get_output_port(entity_name, layout),
    )
    write_file(
        java_path(main_java, layout.service_package, f"{entity_name}Service.java"),
        ports_templates.get_service(
            entity_name, layout,
            generate_domain_update_statements(attrs),
            generate_domain_update_statements(attrs, patch=True),
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
            java_path(main_java, layout.dto_package, f"{class_name}.java"),
            ports_templates.get_dto(class_name, layout.dto_package, fields, enum_import_lines),
        )

    reference_attrs = [attr for attr in attrs if attr["type"] == "reference"]
    generated_files = {
        (layout.web_mapper_package, f"{entity_name}WebMapper.java"):
            ports_templates.get_web_mapper(entity_name, layout),
        (layout.controller_package, f"{entity_name}Controller.java"):
            ports_templates.get_controller(entity_name, entity_lower, layout, endpoints),
        (layout.persistence_package, f"{entity_name}JpaEntity.java"):
            ports_templates.get_persistence_entity(
                entity_name,
                entity_lower,
                layout.persistence_package,
                generate_entity_fields(attrs, reference_type_suffix="JpaEntity"),
                generate_table_unique_constraints_annotation(attrs),
                has_default(attrs),
                include_all_args_builder,
                enum_import_lines,
            ),
        (layout.persistence_package, f"{entity_name}PersistenceMapper.java"):
            ports_templates.get_persistence_mapper(entity_name, layout, reference_attrs),
        (layout.persistence_package, f"{entity_name}JpaRepository.java"):
            ports_templates.get_repository(entity_name, layout),
        (layout.persistence_package, f"{entity_name}JpaSpecifications.java"):
            ports_templates.get_jpa_specification(
                entity_name, layout, generate_specification_filter_cases(attrs)
            ),
        (layout.persistence_package, f"{entity_name}PersistenceAdapter.java"):
            ports_templates.get_persistence_adapter(entity_name, layout, reference_attrs),
        (layout.exception_package, "ResourceNotFoundException.java"):
            ports_templates.get_exception_class(layout),
        (layout.exception_package, "GlobalExceptionHandler.java"):
            ports_templates.get_exception_handler(layout),
    }
    for (package, filename), content in generated_files.items():
        write_file(java_path(main_java, package, filename), content)

    write_file(
        java_path(test_java, layout.service_package, f"{entity_name}ServiceTest.java"),
        ports_templates.get_service_test(entity_name, layout),
    )
    write_file(
        java_path(
            test_java, layout.controller_package, f"{entity_name}ControllerTest.java"
        ),
        ports_templates.get_controller_test(
            entity_name,
            entity_lower,
            layout,
            generate_test_dto_assignments(attrs),
            has_required_input(attrs),
            generate_invalid_test_dto_assignments(attrs),
            endpoints,
            enum_import_lines,
        ),
    )


def generate_ports_project_from_attrs(
    entity_name,
    attrs,
    layout,
    attrs_str,
    base_package=None,
    endpoints=None,
    overwrite=False,
):
    base_package = base_package or DEFAULT_BASE_PACKAGE
    endpoints = endpoints or list(DEFAULT_ENDPOINTS)
    write_file = _make_write_file(base_package)

    entity_lower = entity_name.lower()
    base_dir = f"crud-{entity_lower}-{layout.name}"
    _guard_existing_directory(base_dir, overwrite)
    main_java = f"{base_dir}/src/main/java"
    test_java = f"{base_dir}/src/test/java"
    resources = f"{base_dir}/src/main/resources"

    _write_ports_scaffolding(write_file, base_dir, entity_lower, base_package, main_java, resources)
    write_file(
        f"{base_dir}/docs/index.html",
        documentation.get_documentation_html(
            entity_name, entity_lower, layout.name, attrs, attrs_str,
            base_package, endpoints,
        ),
    )
    _write_ports_entity(
        write_file, main_java, test_java, resources, base_package,
        entity_name, attrs, layout, endpoints,
    )
    write_file(
        java_path(test_java, "com.example.crud.integration", "PostgreSQLIntegrationTest.java"),
        templates.get_postgres_integration_test(entity_lower),
    )
    return base_dir


def generate_multi_entity_ports_project(
    project_name, entities, layout, attrs_str, base_package=None, endpoints=None, overwrite=False
):
    """entities: [(entity_name, attrs), ...] ya en orden topologico (ver
    json_schema.load_entities_schema): una entidad referenciada por otra se
    genera (y migra) antes que quien la referencia."""
    base_package = base_package or DEFAULT_BASE_PACKAGE
    endpoints = endpoints or list(DEFAULT_ENDPOINTS)
    write_file = _make_write_file(base_package)

    project_lower = project_name.lower()
    base_dir = f"crud-{project_lower}-{layout.name}"
    _guard_existing_directory(base_dir, overwrite)
    main_java = f"{base_dir}/src/main/java"
    test_java = f"{base_dir}/src/test/java"
    resources = f"{base_dir}/src/main/resources"

    _write_ports_scaffolding(write_file, base_dir, project_lower, base_package, main_java, resources)

    doc_links = []
    for entity_name, attrs in entities:
        entity_lower = entity_name.lower()
        write_file(
            f"{base_dir}/docs/{entity_lower}.html",
            documentation.get_documentation_html(
                entity_name, entity_lower, layout.name, attrs, attrs_str,
                base_package, endpoints,
            ),
        )
        doc_links.append(f'<li><a href="{entity_lower}.html">{entity_name}</a></li>')
        _write_ports_entity(
            write_file, main_java, test_java, resources, base_package,
            entity_name, attrs, layout, endpoints,
        )

    write_file(
        f"{base_dir}/docs/index.html",
        "<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\">"
        f"<title>{project_name}</title></head><body>"
        f"<h1>{project_name}</h1><p>Entidades generadas en este proyecto:</p>"
        f"<ul>{''.join(doc_links)}</ul></body></html>",
    )

    first_entity_lower = entities[0][0].lower()
    write_file(
        java_path(test_java, "com.example.crud.integration", "PostgreSQLIntegrationTest.java"),
        templates.get_postgres_integration_test(first_entity_lower),
    )
    return base_dir
