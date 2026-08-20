"""Punto de entrada compatible para el generador CRUD."""

import sys

from crud_generator.database_profiles import (
    extract_database_argument,
    install_database_profile,
)
from crud_generator.sqlserver_test_profile import install_sqlserver_test_profile


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

    # Se importa despues de instalar el perfil para que parsing/fields capturen
    # el mapa de tipos SQL correcto desde el principio.
    from crud_generator.cli import main as cli_main

    return cli_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
