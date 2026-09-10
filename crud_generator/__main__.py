"""Punto de entrada instalable para el generador CRUD.

Permite ejecutar el paquete con ``python -m crud_generator`` y sirve como
entry point unico para los comandos instalados por pip.
"""

import sys

from .database_profiles import extract_database_argument, install_database_profile
from .sqlserver_test_profile import install_sqlserver_test_profile


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

    # Importar despues de instalar el perfil garantiza que parsing/fields
    # capturen el mapa de tipos SQL correcto desde el principio.
    from .cli import main as cli_main

    return cli_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
