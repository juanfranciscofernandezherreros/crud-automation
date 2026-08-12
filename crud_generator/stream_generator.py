"""Orquestación de la generación de un proyecto Kafka Streams (--stream)."""

import os

from . import stream_templates
from .parsing import DefinitionError
from .stream_schema import load_stream_definition
from .writer import write_file


def _guard_existing_directory(base_dir, overwrite):
    if os.path.isdir(base_dir) and not overwrite:
        raise DefinitionError(
            f"El directorio '{base_dir}' ya existe. Vuelve a ejecutar con --force "
            "para regenerarlo."
        )


def generate_stream_project(json_path, overwrite=False):
    definition = load_stream_definition(json_path)
    project = definition["project"]
    package = definition["package"]
    project_class_prefix = "".join(
        part.capitalize() for part in project.split("-")
    )
    definition["project_class_prefix"] = project_class_prefix

    base_dir = f"crud-{project}"
    _guard_existing_directory(base_dir, overwrite)

    package_path = package.replace(".", "/")
    java_base = f"{base_dir}/src/main/java/{package_path}"
    test_base = f"{base_dir}/src/test/java/{package_path}"
    resources = f"{base_dir}/src/main/resources"
    state_store_name = f"{project}-totals-store"

    write_file(f"{base_dir}/pom.xml", stream_templates.get_pom_xml(project))
    write_file(f"{base_dir}/Dockerfile", stream_templates.DOCKERFILE)
    write_file(
        f"{base_dir}/docker-compose.yml", stream_templates.get_docker_compose(project)
    )
    write_file(f"{base_dir}/.gitignore", stream_templates.GITIGNORE)
    write_file(
        f"{resources}/application.yml", stream_templates.get_application_yml(project)
    )

    write_file(
        f"{java_base}/{project_class_prefix}Application.java",
        stream_templates.get_application(package, project_class_prefix),
    )
    write_file(
        f"{java_base}/config/KafkaStreamsConfig.java",
        stream_templates.get_kafka_streams_config(
            package, project, project_class_prefix,
            definition["input_topic"], definition["output_topic"],
        ),
    )
    write_file(
        f"{java_base}/model/{definition['input_event']}.java",
        stream_templates.get_model(
            package, definition["input_event"], definition["input_fields"],
            with_json_property=True,
        ),
    )
    is_passthrough = definition["group_by_field"] is None
    if is_passthrough:
        output_fields = definition["input_fields"]
    else:
        output_fields = definition["input_fields"] + [
            {
                "name": definition["aggregate_as"],
                "camel_name": definition["aggregate_as"].split("_")[0]
                + "".join(p.capitalize() for p in definition["aggregate_as"].split("_")[1:]),
                "type": "double",
                "java_type": "Double",
            }
        ]
    write_file(
        f"{java_base}/model/{definition['output_event']}.java",
        stream_templates.get_model(
            package, definition["output_event"], output_fields, with_json_property=False
        ),
    )
    write_file(
        f"{java_base}/topology/{project_class_prefix}Topology.java",
        stream_templates.get_topology(definition, state_store_name),
    )
    write_file(
        f"{test_base}/topology/{project_class_prefix}TopologyTest.java",
        stream_templates.get_topology_test(definition, state_store_name),
    )

    return base_dir
