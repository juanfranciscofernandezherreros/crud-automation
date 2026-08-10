"""Arquitecturas soportadas por el generador."""

from dataclasses import dataclass

from .parsing import DefinitionError


@dataclass(frozen=True)
class PortsArchitecture:
    name: str
    domain_package: str
    input_package: str
    output_package: str
    service_package: str
    controller_package: str
    dto_package: str
    web_mapper_package: str
    persistence_package: str
    exception_package: str


ARCHITECTURES = ("layered", "hexagonal", "clean")

PORTS_ARCHITECTURES = {
    "hexagonal": PortsArchitecture(
        name="hexagonal",
        domain_package="com.example.crud.domain.model",
        input_package="com.example.crud.application.port.in",
        output_package="com.example.crud.application.port.out",
        service_package="com.example.crud.application.service",
        controller_package="com.example.crud.adapter.in.web",
        dto_package="com.example.crud.adapter.in.web.dto",
        web_mapper_package="com.example.crud.adapter.in.web.mapper",
        persistence_package="com.example.crud.adapter.out.persistence",
        exception_package="com.example.crud.shared.exception",
    ),
    "clean": PortsArchitecture(
        name="clean",
        domain_package="com.example.crud.domain.entity",
        input_package="com.example.crud.application.usecase",
        output_package="com.example.crud.application.gateway",
        service_package="com.example.crud.application.service",
        controller_package="com.example.crud.interfaceadapter.controller",
        dto_package="com.example.crud.interfaceadapter.dto",
        web_mapper_package="com.example.crud.interfaceadapter.mapper",
        persistence_package="com.example.crud.framework.persistence",
        exception_package="com.example.crud.shared.exception",
    ),
}


def normalize_architecture(value):
    architecture = value.strip().lower()
    aliases = {"capas": "layered", "hex": "hexagonal", "limpia": "clean"}
    architecture = aliases.get(architecture, architecture)
    if architecture not in ARCHITECTURES:
        choices = ", ".join(ARCHITECTURES)
        raise DefinitionError(
            f"Arquitectura desconocida '{value}'. Opciones: {choices}."
        )
    return architecture
