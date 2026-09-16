"""Punto de entrada instalable para el generador CRUD.

Permite ejecutar el paquete con ``python -m crud_generator`` y sirve como
entry point unico para los comandos instalados por pip.
"""

import sys

from .database_profiles import extract_database_argument, install_database_profile
from .sqlserver_test_profile import install_sqlserver_test_profile


def _extract_agent_options(args):
    """Extrae las opciones de postprocesado sin acoplarlas al CLI principal."""
    args = list(args)
    apply_rules = False
    agent_command = None

    while "--apply-agent-rules" in args:
        args.remove("--apply-agent-rules")
        apply_rules = True

    if "--agent-command" in args:
        index = args.index("--agent-command")
        if index + 1 >= len(args):
            raise ValueError("Falta el valor de --agent-command.")
        agent_command = args[index + 1]
        del args[index : index + 2]

    return args, apply_rules, agent_command


def main(args=None):
    args = sys.argv[1:] if args is None else list(args)
    try:
        args, apply_agent_rules_requested, agent_command = _extract_agent_options(args)
        args, database = extract_database_argument(args)
        install_database_profile(database)
        if database == "sqlserver":
            install_sqlserver_test_profile()
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    # Importar despues de instalar el perfil garantiza que parsing/fields
    # capturen el mapa de tipos SQL correcto desde el principio.
    from . import cli

    if apply_agent_rules_requested:
        from .agent_rules import apply_agent_rules
        from .parsing import DefinitionError

        original_post_generate = cli._post_generate

        def post_generate_with_agent(base_dir, verify, push_github, repo_name, private):
            try:
                apply_agent_rules(base_dir, command=agent_command)
            except DefinitionError as error:
                print(f"Error aplicando reglas del agente: {error}", file=sys.stderr)
                return 2

            print("Reglas del agente aplicadas al código generado.")
            return original_post_generate(base_dir, verify, push_github, repo_name, private)

        cli._post_generate = post_generate_with_agent

    return cli.main(args)


if __name__ == "__main__":
    raise SystemExit(main())
