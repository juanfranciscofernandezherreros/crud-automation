"""Punto de entrada instalable para el generador CRUD.

Permite ejecutar el paquete con ``python -m crud_generator`` y sirve como
entry point unico para los comandos instalados por pip.
"""

import sys

from .database_profiles import extract_database_argument, install_database_profile
from .sqlserver_test_profile import install_sqlserver_test_profile


def _run_feature_mode(args):
    """Genera un microservicio con la arquitectura feature-based de AGENTS.md.

    Se mantiene como modo explicito para no romper de golpe a consumidores de
    las arquitecturas layered/hexagonal/clean existentes.
    """
    from .cli import (
        _post_generate,
        extract_force,
        extract_github,
        extract_private,
        extract_verify,
    )
    from .conventions import load_conventions
    from .feature_generator import generate_feature_project
    from .parsing import DefinitionError, normalize_entity_name

    args = [arg for arg in args if arg != "--feature"]
    try:
        args, push_github, github_repo_name = extract_github(args)
        args, private = extract_private(args)
        args, force = extract_force(args)
        args, verify = extract_verify(args)
    except DefinitionError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    if len(args) < 2:
        print(
            "Uso feature: python -m crud_generator <Entidad> <attr:tipo,...> "
            "--feature [--force] [--verify] [--github [repo]]"
        )
        return 1

    conventions = load_conventions()
    base_package = conventions.get("package")

    try:
        entity_name = normalize_entity_name(args[0])
        attrs_str = " ".join(args[1:])
        base_dir = generate_feature_project(
            entity_name,
            attrs_str,
            base_package=base_package,
            overwrite=force,
        )
    except DefinitionError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(
        f"Proyecto {base_dir} generado con arquitectura feature-based: "
        "model/entity separados, service interface+impl, dos mappers y paquetes por feature."
    )
    return _post_generate(base_dir, verify, push_github, github_repo_name, private)


def main(args=None):
    args = sys.argv[1:] if args is None else list(args)
    try:
        args, database = extract_database_argument(args)
        install_database_profile(database)
        if database == "sqlserver":
            install_sqlserver_test_profile()
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    if "--feature" in args:
        return _run_feature_mode(args)

    # Importar despues de instalar el perfil garantiza que parsing/fields
    # capturen el mapa de tipos SQL correcto desde el principio.
    from .cli import main as cli_main

    return cli_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
