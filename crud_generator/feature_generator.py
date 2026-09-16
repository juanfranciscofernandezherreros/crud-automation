"""Generador feature-based que materializa directamente las reglas Spring de AGENTS.md."""

import os

from . import documentation, feature_templates, migrations, templates
from .architectures import DEFAULT_BASE_PACKAGE
from .fields import (
    exceeds_constructor_param_limit,
    generate_dto_fields,
    generate_entity_fields,
    generate_enum_import_lines,
    generate_plain_fields,
    generate_specification_filter_cases,
    generate_table_unique_constraints_annotation,
    get_enum_types,
    has_default,
)
from .observability import write_observability_stack
from .parsing import DEFAULT_ENDPOINTS, DefinitionError, parse_attributes, pluralize
from .writer import write_file as _write_file


def _guard_existing_directory(base_dir, overwrite):
    if os.path.isdir(base_dir) and not overwrite:
        raise DefinitionError(
            f"El directorio '{base_dir}' ya existe. Vuelve a ejecutar con --force "
            "para regenerarlo."
        )


def _make_write_file(base_package):
    def write_file(path, content):
        if base_package != DEFAULT_BASE_PACKAGE:
            content = content.replace(DEFAULT_BASE_PACKAGE, base_package)
        _write_file(path, content)

    return write_file


def _java_path(base_dir, package, filename, test=False):
    source = "test" if test else "main"
    return f"{base_dir}/src/{source}/java/{package.replace('.', '/')}/{filename}"


def _write_scaffolding(write_file, base_dir, project_lower, base_package):
    write_file(f"{base_dir}/pom.xml", templates.get_pom_xml(project_lower))
    write_file(f"{base_dir}/Dockerfile", templates.DOCKERFILE)
    write_file(
        f"{base_dir}/docker-compose.yml",
        templates.get_docker_compose(project_lower),
    )
    write_file(f"{base_dir}/.env.example", templates.get_env_example())
    write_file(f"{base_dir}/.env", templates.get_env_default())
    write_file(f"{base_dir}/.gitignore", templates.GITIGNORE)
    write_file(
        f"{base_dir}/.github/workflows/ci.yml",
        templates.get_github_actions_workflow(project_lower),
    )

    resources = f"{base_dir}/src/main/resources"
    write_file(
        f"{resources}/application.yml",
        templates.get_application_yml(project_lower),
    )
    write_file(
        f"{resources}/logback-spring.xml",
        templates.get_logback_spring_xml(project_lower),
    )
    write_observability_stack(write_file, base_dir, project_lower, project_lower)

    write_file(
        _java_path(base_dir, base_package, "CrudApplication.java"),
        templates.APP_MAIN,
    )
    write_file(
        _java_path(base_dir, f"{base_package}.configuration", "JpaAuditingConfiguration.java"),
        templates.AUDITING_CONFIG,
    )
    write_file(
        _java_path(base_dir, f"{base_package}.configuration", "SecurityConfiguration.java"),
        templates.SECURITY_CONFIG,
    )
    write_file(
        _java_path(base_dir, f"{base_package}.configuration", "RateLimitFilter.java"),
        templates.RATE_LIMIT_FILTER,
    )
    write_file(
        _java_path(base_dir, f"{base_package}.exception", "GlobalExceptionHandler.java"),
        templates.get_exception_handler(),
    )
    write_file(
        _java_path(base_dir, f"{base_package}.exception", "ResourceNotFoundException.java"),
        templates.EXCEPTION_CLASS,
    )


def _write_feature(
    write_file,
    base_dir,
    base_package,
    entity_name,
    attrs,
    endpoints,
):
    entity_lower = entity_name.lower()
    feature_package = f"{base_package}.{entity_lower}"
    resources = f"{base_dir}/src/main/resources"
    table_name = pluralize(entity_lower)

    migrations.write_migration(
        resources,
        entity_name,
        entity_lower,
        table_name,
        attrs,
        write_file,
        templates.get_sql_migration,
    )

    include_all_args_builder = not exceeds_constructor_param_limit(attrs)
    model_package = f"{feature_package}.model"
    entity_package = f"{feature_package}.entity"
    dto_package = f"{feature_package}.dto"

    write_file(
        _java_path(base_dir, model_package, f"{entity_name}.java"),
        feature_templates.get_model(
            entity_name,
            model_package,
            generate_plain_fields(attrs),
            include_all_args_builder,
        ),
    )

    for enum_class, enum_values in get_enum_types(attrs).items():
        write_file(
            _java_path(base_dir, model_package, f"{enum_class}.java"),
            templates.get_enum_class(enum_class, enum_values, model_package),
        )

    model_enum_imports = generate_enum_import_lines(attrs, model_package)
    entity_enum_imports = generate_enum_import_lines(attrs, model_package)

    write_file(
        _java_path(base_dir, entity_package, f"{entity_name}Entity.java"),
        feature_templates.get_entity(
            entity_name,
            entity_lower,
            entity_package,
            generate_entity_fields(attrs, reference_type_suffix="Entity"),
            generate_table_unique_constraints_annotation(attrs),
            has_default(attrs),
            include_all_args_builder,
            entity_enum_imports,
        ),
    )

    dto_definitions = [
        (
            "CreateDTO",
            generate_dto_fields(
                attrs,
                ignore_id=True,
                ignore_audit=True,
                validation_mode="write",
            ),
        ),
        (
            "UpdateDTO",
            generate_dto_fields(
                attrs,
                ignore_id=True,
                ignore_audit=True,
                validation_mode="write",
            ),
        ),
        (
            "PatchDTO",
            generate_dto_fields(
                attrs,
                ignore_id=True,
                ignore_audit=True,
                validation_mode="patch",
            ),
        ),
        ("ResponseDTO", f"{generate_dto_fields(attrs)}\n    private Long version;"),
    ]
    for suffix, fields in dto_definitions:
        class_name = f"{entity_name}{suffix}"
        write_file(
            _java_path(base_dir, dto_package, f"{class_name}.java"),
            feature_templates.get_dto(
                class_name,
                dto_package,
                fields,
                model_enum_imports,
            ),
        )

    reference_attrs = [attr for attr in attrs if attr["type"] == "reference"]

    generated = {
        (f"{feature_package}.repository", f"{entity_name}Repository.java"):
            feature_templates.get_repository(entity_name, feature_package),
        (f"{feature_package}.repository", f"{entity_name}Specifications.java"):
            feature_templates.get_specification(
                entity_name,
                feature_package,
                generate_specification_filter_cases(attrs),
            ),
        (f"{feature_package}.mapper", f"{entity_name}Mapper.java"):
            feature_templates.get_web_mapper(entity_name, feature_package),
        (f"{feature_package}.mapper", f"{entity_name}EntityMapper.java"):
            feature_templates.get_entity_mapper(
                entity_name,
                feature_package,
                reference_attrs,
            ),
        (f"{feature_package}.service", f"{entity_name}Service.java"):
            feature_templates.get_service_interface(entity_name, feature_package),
        (f"{feature_package}.service", f"{entity_name}ServiceImpl.java"):
            feature_templates.get_service_impl(
                entity_name,
                feature_package,
                base_package,
                reference_attrs,
            ),
        (f"{feature_package}.controller", f"{entity_name}Controller.java"):
            feature_templates.get_controller(entity_name, entity_lower, feature_package),
    }
    for (package, filename), content in generated.items():
        write_file(_java_path(base_dir, package, filename), content)

    write_file(
        _java_path(
            base_dir,
            f"{feature_package}.service",
            f"{entity_name}ServiceTest.java",
            test=True,
        ),
        feature_templates.get_service_test(entity_name, feature_package),
    )


def generate_feature_project(
    entity_name,
    attrs_str,
    base_package=None,
    endpoints=None,
    overwrite=False,
):
    attrs = parse_attributes(attrs_str)
    return generate_feature_project_from_attrs(
        entity_name,
        attrs,
        attrs_str,
        base_package=base_package,
        endpoints=endpoints,
        overwrite=overwrite,
    )


def generate_feature_project_from_attrs(
    entity_name,
    attrs,
    attrs_str,
    base_package=None,
    endpoints=None,
    overwrite=False,
):
    base_package = base_package or DEFAULT_BASE_PACKAGE
    endpoints = endpoints or list(DEFAULT_ENDPOINTS)
    write_file = _make_write_file(base_package)

    entity_lower = entity_name.lower()
    base_dir = f"crud-{entity_lower}-feature"
    _guard_existing_directory(base_dir, overwrite)

    _write_scaffolding(write_file, base_dir, entity_lower, base_package)
    _write_feature(
        write_file,
        base_dir,
        base_package,
        entity_name,
        attrs,
        endpoints,
    )

    write_file(
        f"{base_dir}/docs/index.html",
        documentation.get_documentation_html(
            entity_name,
            entity_lower,
            "layered",
            attrs,
            attrs_str,
            base_package,
            endpoints,
        ),
    )

    return base_dir
