#!/usr/bin/env python3
"""Orquesta un ciclo completo: genera un CRUD y publica el proyecto en GitHub.

Encadena, como dos procesos separados, los dos scripts que ya existen en
este repositorio:

  1. generate_crud.py <Entidad> <attrs> --architecture <arch>  -> genera el
     proyecto en crud-<entidad>[-<arquitectura>]/.
  2. createRepo.py <directorio_generado> [nombre_repo] [--private]  -> lo
     publica como repositorio nuevo en GitHub (via la CLI 'gh', ya
     autenticada).

No reimplementa nada de crud_generator: si un paso falla, el paso
siguiente no se ejecuta y el código de salida refleja cuál de los dos
falló, igual que si se hubieran corrido a mano en dos comandos.

Usage:
    python orchestrate_crud.py <Entidad> "<attrs>" --architecture hexagonal
    python orchestrate_crud.py <Entidad> "<attrs>" --architecture hexagonal --skip-github
    python orchestrate_crud.py <Entidad> "<attrs>" --repo-name mi-repo --private
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT_LINE = re.compile(r"^Proyecto (\S+) generado con éxito", re.MULTILINE)


def run_step(args, label):
    """Ejecuta un paso como subproceso, mostrando su salida en vivo y
    devolviendo (returncode, stdout_completo) para poder inspeccionarlo
    despues (p.ej. extraer el directorio generado)."""
    print(f"\n==> {label}: {' '.join(args)}")
    process = subprocess.run(
        [sys.executable, *args], cwd=ROOT, text=True, capture_output=True,
    )
    if process.stdout:
        print(process.stdout, end="")
    if process.stderr:
        print(process.stderr, end="", file=sys.stderr)
    return process.returncode, process.stdout


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("entity", help="nombre de la entidad (p.ej. OperacionFinanciera)")
    parser.add_argument("attrs", help="definición de atributos, formato DSL de generate_crud.py")
    parser.add_argument(
        "--architecture", "-a", default="layered",
        choices=["layered", "hexagonal", "clean"],
        help="arquitectura del proyecto generado (por defecto: layered)",
    )
    parser.add_argument("--force", action="store_true", help="regenera un directorio ya existente")
    parser.add_argument("--verify", action="store_true", help="ejecuta 'mvn verify' tras generar")
    parser.add_argument(
        "--repo-name", default=None,
        help="nombre del repositorio en GitHub (por defecto, el del directorio generado)",
    )
    parser.add_argument("--private", action="store_true", help="crea el repositorio de GitHub como privado")
    parser.add_argument(
        "--skip-github", action="store_true",
        help="genera el proyecto pero no ejecuta createRepo.py",
    )
    args = parser.parse_args()

    generate_args = ["generate_crud.py", args.entity, args.attrs, "--architecture", args.architecture]
    if args.force:
        generate_args.append("--force")
    if args.verify:
        generate_args.append("--verify")

    returncode, stdout = run_step(generate_args, "Paso 1/2: generate_crud.py")
    if returncode != 0:
        print(f"\nAbortado: generate_crud.py terminó con código {returncode}.", file=sys.stderr)
        return returncode

    match = PROJECT_LINE.search(stdout)
    if not match:
        print(
            "\nAbortado: no se pudo determinar el directorio generado a partir "
            "de la salida de generate_crud.py.",
            file=sys.stderr,
        )
        return 1
    project_dir = match.group(1)

    if args.skip_github:
        print(f"\nListo. Proyecto generado en {project_dir}/ (--skip-github: no se publica en GitHub).")
        return 0

    publish_args = ["createRepo.py", project_dir]
    if args.repo_name:
        publish_args.append(args.repo_name)
    if args.private:
        publish_args.append("--private")

    returncode, _ = run_step(publish_args, "Paso 2/2: createRepo.py")
    if returncode != 0:
        print(f"\ngenerate_crud.py terminó bien, pero createRepo.py falló con código {returncode}.", file=sys.stderr)
        return returncode

    print(f"\nListo: {project_dir}/ generado y publicado en GitHub.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
