"""Interfaz de línea de comandos del generador."""

import sys

from .generator import generate_project
from .parsing import DefinitionError, normalize_entity_name


def main(args=None):
    args = sys.argv[1:] if args is None else args
    if len(args) < 2:
        print("Uso: python generate_crud.py <Entidad> <attr:tipo,attr:tipo...>")
        print(
            'Ejemplo: python generate_crud.py Producto '
            '"id:int, nombre:string, precio:float"'
        )
        return 1

    try:
        entity_name = normalize_entity_name(args[0])
        attrs_str = " ".join(args[1:])
        base_dir = generate_project(entity_name, attrs_str)
    except DefinitionError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(
        f"Proyecto {base_dir} generado con éxito, "
        "incluyendo todas las capas y tests."
    )
    return 0
