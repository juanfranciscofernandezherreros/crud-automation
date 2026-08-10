"""Orquestación de la generación de un proyecto CRUD."""

from .architectures import PORTS_ARCHITECTURES, normalize_architecture
from .fields import (
    generate_dto_fields,
    generate_entity_fields,
    generate_invalid_test_dto_assignments,
    generate_sql_fields,
    generate_test_dto_assignments,
    has_required_input,
)
from .parsing import normalize_entity_name, parse_attributes
from . import templates
from .writer import write_file


def generate_project(entity_name, attrs_str, architecture="layered"):
    entity_name = normalize_entity_name(entity_name)
    architecture = normalize_architecture(architecture)
    if architecture in PORTS_ARCHITECTURES:
        from .ports_generator import generate_ports_project

        return generate_ports_project(
            entity_name, attrs_str, PORTS_ARCHITECTURES[architecture]
        )
    return generate_layered_project(entity_name, attrs_str)


def generate_layered_project(entity_name, attrs_str):
    entity_lower = entity_name.lower()
    attrs = parse_attributes(attrs_str)
    base_dir = f"crud-{entity_lower}"
    java_base = f"{base_dir}/src/main/java/com/example/crud"
    res_base = f"{base_dir}/src/main/resources"
    test_base = f"{base_dir}/src/test/java/com/example/crud"

    entity_fields = generate_entity_fields(attrs)
    sql_fields = generate_sql_fields(attrs)

    write_file(f"{base_dir}/pom.xml", templates.get_pom_xml(entity_lower))
    write_file(f"{base_dir}/Dockerfile", templates.DOCKERFILE)
    write_file(
        f"{base_dir}/docker-compose.yml",
        templates.get_docker_compose(entity_lower),
    )
    write_file(
        f"{res_base}/application.yml", templates.get_application_yml(entity_lower)
    )
    write_file(
        f"{res_base}/db/migration/V1__Create_Table_{entity_name}.sql",
        templates.get_sql_migration(entity_lower, sql_fields),
    )

    write_file(f"{java_base}/CrudApplication.java", templates.APP_MAIN)
    write_file(
        f"{java_base}/configuration/JpaAuditingConfiguration.java",
        templates.AUDITING_CONFIG,
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
        templates.get_entity(entity_name, entity_lower, entity_fields),
    )
    write_file(
        f"{java_base}/repository/{entity_name}Repository.java",
        templates.get_repository(entity_name),
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
        ("ResponseDTO", generate_dto_fields(attrs)),
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
            entity_name, entity_lower
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
        ),
    )

    return base_dir
