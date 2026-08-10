"""Generación de arquitecturas hexagonal y clean."""

from . import ports_templates, templates
from .fields import (
    generate_domain_update_statements,
    generate_dto_fields,
    generate_entity_fields,
    generate_invalid_test_dto_assignments,
    generate_plain_fields,
    generate_sql_fields,
    generate_sql_indexes,
    generate_test_dto_assignments,
    has_required_input,
)
from .parsing import parse_attributes
from .writer import write_file


def package_path(package):
    return package.replace(".", "/")


def java_path(java_root, package, filename):
    return f"{java_root}/{package_path(package)}/{filename}"


def generate_ports_project(entity_name, attrs_str, layout):
    entity_lower = entity_name.lower()
    attrs = parse_attributes(attrs_str)
    base_dir = f"crud-{entity_lower}-{layout.name}"
    main_java = f"{base_dir}/src/main/java"
    test_java = f"{base_dir}/src/test/java"
    resources = f"{base_dir}/src/main/resources"

    write_file(f"{base_dir}/pom.xml", templates.get_pom_xml(entity_lower))
    write_file(f"{base_dir}/Dockerfile", templates.DOCKERFILE)
    write_file(
        f"{base_dir}/docker-compose.yml",
        templates.get_docker_compose(entity_lower),
    )
    write_file(
        f"{resources}/application.yml", templates.get_application_yml(entity_lower)
    )
    write_file(
        f"{resources}/db/migration/V1__Create_Table_{entity_name}.sql",
        templates.get_sql_migration(
            entity_lower,
            generate_sql_fields(attrs),
            generate_sql_indexes(attrs, f"{entity_lower}s"),
        ),
    )
    write_file(
        java_path(main_java, "com.example.crud", "CrudApplication.java"),
        templates.APP_MAIN,
    )
    write_file(
        java_path(
            main_java,
            "com.example.crud.configuration",
            "JpaAuditingConfiguration.java",
        ),
        templates.AUDITING_CONFIG,
    )
    write_file(
        java_path(
            main_java,
            "com.example.crud.configuration",
            "SecurityConfiguration.java",
        ),
        templates.SECURITY_CONFIG,
    )
    write_file(
        java_path(
            main_java,
            "com.example.crud.configuration",
            "RateLimitFilter.java",
        ),
        templates.RATE_LIMIT_FILTER,
    )
    write_file(
        java_path(
            main_java,
            "com.example.crud.configuration",
            "IdempotencyService.java",
        ),
        templates.IDEMPOTENCY_SERVICE,
    )

    write_file(
        java_path(main_java, layout.domain_package, f"{entity_name}.java"),
        ports_templates.get_domain(
            entity_name, layout.domain_package, generate_plain_fields(attrs)
        ),
    )
    write_file(
        java_path(main_java, layout.domain_package, "PageQuery.java"),
        ports_templates.get_page_query(layout.domain_package),
    )
    write_file(
        java_path(main_java, layout.domain_package, "PageResult.java"),
        ports_templates.get_page_result(layout.domain_package),
    )
    write_file(
        java_path(
            main_java,
            "com.example.crud.configuration",
            "UseCaseConfiguration.java",
        ),
        ports_templates.get_use_case_configuration(entity_name, layout),
    )
    write_file(
        java_path(
            main_java, layout.input_package, f"{entity_name}UseCase.java"
        ),
        ports_templates.get_input_port(entity_name, layout),
    )
    write_file(
        java_path(
            main_java,
            layout.output_package,
            f"{entity_name}PersistencePort.java",
        ),
        ports_templates.get_output_port(entity_name, layout),
    )
    write_file(
        java_path(main_java, layout.service_package, f"{entity_name}Service.java"),
        ports_templates.get_service(
            entity_name,
            layout,
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
            ports_templates.get_dto(class_name, layout.dto_package, fields),
        )

    generated_files = {
        (layout.web_mapper_package, f"{entity_name}WebMapper.java"):
            ports_templates.get_web_mapper(entity_name, layout),
        (layout.controller_package, f"{entity_name}Controller.java"):
            ports_templates.get_controller(entity_name, entity_lower, layout),
        (layout.persistence_package, f"{entity_name}JpaEntity.java"):
            ports_templates.get_persistence_entity(
                entity_name,
                entity_lower,
                layout.persistence_package,
                generate_entity_fields(attrs),
            ),
        (layout.persistence_package, f"{entity_name}PersistenceMapper.java"):
            ports_templates.get_persistence_mapper(entity_name, layout),
        (layout.persistence_package, f"{entity_name}JpaRepository.java"):
            ports_templates.get_repository(entity_name, layout),
        (layout.persistence_package, f"{entity_name}PersistenceAdapter.java"):
            ports_templates.get_persistence_adapter(entity_name, layout),
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
        ),
    )
    write_file(
        java_path(
            test_java,
            "com.example.crud.integration",
            "PostgreSQLIntegrationTest.java",
        ),
        templates.get_postgres_integration_test(entity_lower),
    )
    return base_dir
