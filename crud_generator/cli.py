"""Interfaz de línea de comandos del generador."""

import sys

from .architectures import ARCHITECTURES, normalize_architecture
from .generator import generate_project
from .parsing import DefinitionError, normalize_entity_name


def choose_architecture():
    if not sys.stdin.isatty():
        return "layered"

    print("Arquitectura:")
    for index, architecture in enumerate(ARCHITECTURES, start=1):
        print(f"  {index}. {architecture}")
    selected = input("Selecciona una opción [1]: ").strip()
    if not selected:
        return "layered"
    if selected.isdigit() and 1 <= int(selected) <= len(ARCHITECTURES):
        return ARCHITECTURES[int(selected) - 1]
    return normalize_architecture(selected)


def extract_architecture(args):
    args = list(args)
    architecture = None
    for option in ("--architecture", "-a"):
        if option in args:
            index = args.index(option)
            if index + 1 >= len(args):
                raise DefinitionError(f"Falta el valor de {option}.")
            architecture = normalize_architecture(args[index + 1])
            del args[index : index + 2]
            break
    return args, architecture


def main(args=None):
    args = sys.argv[1:] if args is None else args
    try:
        args, architecture = extract_architecture(args)
    except DefinitionError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    if len(args) < 2:
        print(
            "Uso: python generate_crud.py <Entidad> <attr:tipo,...> "
            "[--architecture layered|hexagonal|clean]"
        )
        print(
            'Ejemplo: python generate_crud.py Producto '
            '"id:int, nombre:string, precio:float"'
        )
        return 1

    try:
        architecture = architecture or choose_architecture()
        entity_name = normalize_entity_name(args[0])
        attrs_str = " ".join(args[1:])
        base_dir = generate_project(entity_name, attrs_str, architecture)
    except DefinitionError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(
        f"Proyecto {base_dir} generado con éxito, "
        "incluyendo todas las capas y tests."
    )
    return 0
