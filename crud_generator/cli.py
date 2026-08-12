"""Interfaz de línea de comandos del generador."""

import sys

from .architectures import ARCHITECTURES, normalize_architecture
from .generator import generate_project, generate_project_from_json
from .parsing import DefinitionError, normalize_entity_name
from .stream_generator import generate_stream_project


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


def extract_json_path(args):
    args = list(args)
    json_path = None
    for option in ("--json", "-j"):
        if option in args:
            index = args.index(option)
            if index + 1 >= len(args):
                raise DefinitionError(f"Falta el valor de {option}.")
            json_path = args[index + 1]
            del args[index : index + 2]
            break
    return args, json_path


def extract_stream_path(args):
    args = list(args)
    stream_path = None
    for option in ("--stream", "-s"):
        if option in args:
            index = args.index(option)
            if index + 1 >= len(args):
                raise DefinitionError(f"Falta el valor de {option}.")
            stream_path = args[index + 1]
            del args[index : index + 2]
            break
    return args, stream_path


def extract_force(args):
    args = list(args)
    force = False
    for option in ("--force", "-f"):
        while option in args:
            args.remove(option)
            force = True
    return args, force


def main(args=None):
    args = sys.argv[1:] if args is None else args
    try:
        args, architecture = extract_architecture(args)
        args, json_path = extract_json_path(args)
        args, stream_path = extract_stream_path(args)
        args, force = extract_force(args)
    except DefinitionError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    if stream_path:
        try:
            base_dir = generate_stream_project(stream_path, overwrite=force)
        except DefinitionError as error:
            print(f"Error: {error}", file=sys.stderr)
            return 2
        print(
            f"Proyecto {base_dir} generado con éxito: topología Kafka Streams, "
            "test de topología y Dockerización."
        )
        return 0

    if json_path:
        try:
            base_dir = generate_project_from_json(json_path, architecture, overwrite=force)
        except DefinitionError as error:
            print(f"Error: {error}", file=sys.stderr)
            return 2
        print(
            f"Proyecto {base_dir} generado con éxito, "
            "incluyendo todas las capas, tests y docs/index.html."
        )
        return 0

    if len(args) < 2:
        print(
            "Uso: python generate_crud.py <Entidad> <attr:tipo,...> "
            "[--architecture layered|hexagonal|clean] [--force]"
        )
        print(
            "  o: python generate_crud.py --json <definicion.json> "
            "[--architecture layered|hexagonal|clean] [--force]"
        )
        print(
            "  o: python generate_crud.py --stream <definicion.json> [--force]"
        )
        print(
            'Ejemplo: python generate_crud.py Producto '
            '"id:int, nombre:string, precio:float"'
        )
        print(
            "--force regenera un directorio ya existente en vez de fallar; "
            "las migraciones ya aplicadas se conservan (ver docs/index.html)."
        )
        return 1

    try:
        architecture = architecture or choose_architecture()
        entity_name = normalize_entity_name(args[0])
        attrs_str = " ".join(args[1:])
        base_dir = generate_project(entity_name, attrs_str, architecture, overwrite=force)
    except DefinitionError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(
        f"Proyecto {base_dir} generado con éxito, "
        "incluyendo todas las capas, tests y docs/index.html."
    )
    return 0
