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

DEFAULT_BASE_PACKAGE = "com.example.crud"


def build_ports_architectures(base_package=DEFAULT_BASE_PACKAGE):
    """Layouts de paquetes para hexagonal/clean, anclados a base_package."""
    return {
        "hexagonal": PortsArchitecture(
            name="hexagonal",
            domain_package=f"{base_package}.domain.model",
            input_package=f"{base_package}.application.port.in",
            output_package=f"{base_package}.application.port.out",
            service_package=f"{base_package}.application.service",
            controller_package=f"{base_package}.adapter.in.web",
            dto_package=f"{base_package}.adapter.in.web.dto",
            web_mapper_package=f"{base_package}.adapter.in.web.mapper",
            persistence_package=f"{base_package}.adapter.out.persistence",
            exception_package=f"{base_package}.shared.exception",
        ),
        "clean": PortsArchitecture(
            name="clean",
            domain_package=f"{base_package}.domain.entity",
            input_package=f"{base_package}.application.usecase",
            output_package=f"{base_package}.application.gateway",
            service_package=f"{base_package}.application.service",
            controller_package=f"{base_package}.interfaceadapter.controller",
            dto_package=f"{base_package}.interfaceadapter.dto",
            web_mapper_package=f"{base_package}.interfaceadapter.mapper",
            persistence_package=f"{base_package}.framework.persistence",
            exception_package=f"{base_package}.shared.exception",
        ),
    }


PORTS_ARCHITECTURES = build_ports_architectures()


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
