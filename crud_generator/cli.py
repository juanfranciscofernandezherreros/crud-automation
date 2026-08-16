"""Interfaz de línea de comandos del generador."""

import sys

from .architectures import ARCHITECTURES, normalize_architecture
from .generate_service import generate_batch_project
from .generator import generate_project, generate_project_from_json
from .github_repo import push_to_github
from .parsing import DefinitionError, normalize_entity_name
from .stream_generator import generate_stream_project
from .verification import verify_project


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


def extract_batch(args):
    args = list(args)
    batch = False
    target = None
    for option in ("--batch", "-b"):
        if option in args:
            index = args.index(option)
            batch = True
            if index + 1 < len(args) and not args[index + 1].startswith("-"):
                target = args[index + 1]
                del args[index : index + 2]
            else:
                del args[index]
            break
    return args, batch, target


def extract_github(args):
    args = list(args)
    push_github = False
    repo_name = None
    for option in ("--github", "-g"):
        if option in args:
            index = args.index(option)
            push_github = True
            if index + 1 < len(args) and not args[index + 1].startswith("-"):
                repo_name = args[index + 1]
                del args[index : index + 2]
            else:
                del args[index]
            break
    return args, push_github, repo_name


def extract_private(args):
    args = list(args)
    private = False
    while "--private" in args:
        args.remove("--private")
        private = True
    return args, private


def extract_force(args):
    args = list(args)
    force = False
    for option in ("--force", "-f"):
        while option in args:
            args.remove(option)
            force = True
    return args, force


def extract_verify(args):
    args = list(args)
    verify = False
    while "--verify" in args:
        args.remove("--verify")
        verify = True
    return args, verify


def _verify_if_requested(base_dir, verify):
    """Tras generar un proyecto, ejecuta 'mvn verify' si se pidió --verify.
    No modifica el proyecto generado -- diagnostica, no corrige (ver
    verification.py). Un fallo aquí no borra lo ya generado: solo cambia el
    código de salida a 3, distinto del 2 de una definición inválida."""
    if not verify:
        return 0
    result = verify_project(base_dir)
    if not result["ran"]:
        print(result["summary"])
        return 0
    if result["success"]:
        tests = result["tests"]
        if tests:
            print(
                f"Verificación OK (mvn verify): {tests['run']} tests, "
                f"{tests['failures']} fallos, {tests['errors']} errores, "
                f"{tests['skipped']} omitidos."
            )
        else:
            print("Verificación OK (mvn verify).")
        return 0
    print(f"Verificación FALLIDA (mvn verify), código {result['returncode']}.", file=sys.stderr)
    if result["hint"]:
        print(f"Pista: {result['hint']}", file=sys.stderr)
    tail = "\n".join(result["log"].strip().splitlines()[-25:])
    if tail:
        print("Últimas líneas del log:", file=sys.stderr)
        print(tail, file=sys.stderr)
    return 3


def _publish_if_requested(base_dir, push_github, repo_name, private):
    """Tras generar un proyecto, lo sube a GitHub si se pidió --github.
    Un fallo aquí (gh no instalado, sin auth, nombre de repo ya usado...)
    no borra lo ya generado: solo cambia el código de salida a 2."""
    if not push_github:
        return 0
    try:
        url = push_to_github(base_dir, repo_name=repo_name, private=private)
    except DefinitionError as error:
        print(f"Error subiendo a GitHub: {error}", file=sys.stderr)
        return 2
    print(f"Repositorio publicado en GitHub: {url}")
    return 0


def _post_generate(base_dir, verify, push_github, repo_name, private):
    """Tras generar: primero verifica (si se pidió), luego publica -- nunca
    se publica un proyecto que acaba de fallar su propia verificación."""
    exit_code = _verify_if_requested(base_dir, verify)
    if exit_code != 0:
        return exit_code
    return _publish_if_requested(base_dir, push_github, repo_name, private)


def main(args=None):
    args = sys.argv[1:] if args is None else args
    try:
        args, architecture = extract_architecture(args)
        args, json_path = extract_json_path(args)
        args, stream_path = extract_stream_path(args)
        args, batch, batch_target = extract_batch(args)
        args, push_github, github_repo_name = extract_github(args)
        args, private = extract_private(args)
        args, force = extract_force(args)
        args, verify = extract_verify(args)
    except DefinitionError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    if batch:
        try:
            base_dir = generate_batch_project(batch_target, overwrite=force)
        except DefinitionError as error:
            print(f"Error: {error}", file=sys.stderr)
            return 2
        print(
            f"Proyecto {base_dir} generado con éxito: microservicio Spring Batch "
            "que consulta 'coches' y escribe el resultado en CSV, con Docker/Compose y CI."
        )
        return _post_generate(base_dir, verify, push_github, github_repo_name, private)

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
        return _post_generate(base_dir, verify, push_github, github_repo_name, private)

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
        return _post_generate(base_dir, verify, push_github, github_repo_name, private)

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
            "  o: python generate_crud.py --batch [directorio_destino] [--force]"
        )
        print(
            'Ejemplo: python generate_crud.py Producto '
            '"id:int, nombre:string, precio:float"'
        )
        print(
            "--force regenera un directorio ya existente en vez de fallar; "
            "las migraciones ya aplicadas se conservan (ver docs/index.html)."
        )
        print(
            "--github [nombre_repo] sube el proyecto generado como repo nuevo "
            "en GitHub (usa la CLI 'gh', ya autenticada); --private lo crea privado."
        )
        print(
            "--verify ejecuta 'mvn verify' sobre el proyecto recién generado y "
            "reporta el resultado (no publica a GitHub si falla)."
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
    return _post_generate(base_dir, verify, push_github, github_repo_name, private)
