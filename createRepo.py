#!/usr/bin/env python3
"""Publica un proyecto ya generado como repositorio nuevo en GitHub.

Version generica: a diferencia del script original, no lleva un token de
GitHub ni un nombre de repositorio grabados en el fichero. Usa la CLI 'gh'
(autenticada una vez con 'gh auth login') para crear el repo y subir el
proyecto. Delega en crud_generator.github_repo, el mismo modulo que usa
'python generate_crud.py ... --github' para publicar automaticamente lo que
acaba de generar.

Usage:
    python createRepo.py <directorio_proyecto> [nombre_repo] [--private]

    directorio_proyecto   Carpeta del proyecto ya generado (por ejemplo,
                           crud-producto/ o spring-batch-coches/).
    nombre_repo            Nombre del repositorio en GitHub (por defecto,
                           el nombre de directorio_proyecto).
    --private              Crea el repositorio privado en vez de publico.
"""

import argparse
import sys

from crud_generator.github_repo import push_to_github
from crud_generator.parsing import DefinitionError


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project_dir", help="directorio del proyecto ya generado")
    parser.add_argument("repo_name", nargs="?", default=None, help="nombre del repo en GitHub (por defecto, el del directorio)")
    parser.add_argument("--private", action="store_true", help="crea el repositorio privado")
    args = parser.parse_args()

    try:
        url = push_to_github(args.project_dir, repo_name=args.repo_name, private=args.private)
    except DefinitionError as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)

    print(f"Repositorio publicado en GitHub: {url}")


if __name__ == "__main__":
    main()
