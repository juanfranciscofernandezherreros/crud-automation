"""Generador modular de proyectos CRUD con Spring Boot."""

from .generator import generate_project
from .parsing import DefinitionError, normalize_entity_name, parse_attributes

__all__ = [
    "DefinitionError",
    "generate_project",
    "normalize_entity_name",
    "parse_attributes",
]
