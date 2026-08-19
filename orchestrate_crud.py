#!/usr/bin/env python3
"""Orquesta un ciclo completo: genera un CRUD, lo publica en GitHub y lo
engancha a Argo CD.

Encadena tres pasos:

  1. generate_crud.py <Entidad> <attrs> --architecture <arch>  -> genera el
     proyecto en crud-<entidad>[-<arquitectura>]/, y le añade k8s/*.yaml +
     .github/workflows/gitops.yml (crud_generator.gitops) antes de
     publicarlo, para que el primer commit ya incluya el despliegue.
  2. createRepo.py <directorio_generado> [nombre_repo] [--private]  -> lo
     publica como repositorio nuevo en GitHub (via la CLI 'gh', ya
     autenticada).
  3. scripts/update_applicationset.py  -> vuelve a descubrir los repos
     crud-* públicos con k8s/kustomization.yaml (ya incluye el recién
     publicado) y, si argocd/applicationset.yaml cambió, lo comitea y
     empuja a este mismo repositorio -- el mismo paso que ya hace el
     workflow programado "Actualizar ApplicationSet".

Si un paso falla, el siguiente no se ejecuta y el código de salida refleja
cuál de los pasos falló, igual que si se hubieran corrido a mano.

Usage:
    python orchestrate_crud.py <Entidad> "<attrs>" --architecture hexagonal
    python orchestrate_crud.py <Entidad> "<attrs>" --architecture hexagonal --skip-github
    python orchestrate_crud.py <Entidad> "<attrs>" --repo-name mi-repo --private
    python orchestrate_crud.py <Entidad> "<attrs>" --skip-argocd
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

from crud_generator.gitops import write_gitops_manifests

ROOT = Path(__file__).resolve().parent
PROJECT_LINE = re.compile(r"^Proyecto (\S+) generado con éxito", re.MULTILINE)

# Sin esto, los prints de este script (bufferizados) pueden aparecer despues
# de la salida de subprocesos que no se capturan (git add/commit en
# update_argocd), que escriben sin buffer directamente al mismo stdout.
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


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
        help="genera el proyecto pero no ejecuta createRepo.py ni el paso de Argo CD",
    )
    parser.add_argument(
        "--skip-argocd", action="store_true",
        help="genera y publica en GitHub, pero no engancha el repo a Argo CD",
    )
    args = parser.parse_args()

    generate_args = ["generate_crud.py", args.entity, args.attrs, "--architecture", args.architecture]
    if args.force:
        generate_args.append("--force")
    if args.verify:
        generate_args.append("--verify")

    returncode, stdout = run_step(generate_args, "Paso 1/3: generate_crud.py")
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

    repo_name = args.repo_name or project_dir
    print(f"\n==> Añadiendo manifiestos K8s + workflow GitOps para '{repo_name}'")
    write_gitops_manifests(ROOT / project_dir, repo_name)

    publish_args = ["createRepo.py", project_dir, repo_name]
    if args.private:
        publish_args.append("--private")

    returncode, _ = run_step(publish_args, "Paso 2/3: createRepo.py")
    if returncode != 0:
        print(f"\ngenerate_crud.py terminó bien, pero createRepo.py falló con código {returncode}.", file=sys.stderr)
        return returncode

    if args.skip_argocd:
        print(f"\nListo: {project_dir}/ generado y publicado en GitHub (--skip-argocd: no se actualiza Argo CD).")
        return 0

    if args.private:
        print(
            "\nAviso: repo privado, no se actualiza Argo CD -- "
            "scripts/update_applicationset.py solo descubre repos públicos. "
            "Usa --skip-argocd para silenciar este aviso.",
            file=sys.stderr,
        )
        return 0

    returncode = update_argocd()
    if returncode != 0:
        print(
            f"\ngenerate_crud.py y createRepo.py terminaron bien, pero el paso de Argo CD "
            f"falló con código {returncode}. El repositorio ya está publicado en GitHub; "
            "puedes reintentar el paso 3 a mano con 'python scripts/update_applicationset.py'.",
            file=sys.stderr,
        )
        return returncode

    print(f"\nListo: {project_dir}/ generado, publicado en GitHub y enganchado a Argo CD.")
    return 0


def update_argocd():
    """Paso 3/3: vuelve a descubrir los repos crud-* públicos con
    k8s/kustomization.yaml (ya incluye el que se acaba de publicar) y, si
    argocd/applicationset.yaml cambió, lo comitea y empuja en este mismo
    repositorio -- igual que el workflow programado "Actualizar
    ApplicationSet" (.github/workflows/update-applicationset.yml)."""
    env = os.environ.copy()
    gh_token = subprocess.run(
        ["gh", "auth", "token"], cwd=ROOT, text=True, capture_output=True,
    )
    if gh_token.returncode == 0:
        env["GITHUB_TOKEN"] = gh_token.stdout.strip()

    print("\n==> Paso 3/3: scripts/update_applicationset.py")
    discover = subprocess.run(
        [sys.executable, "scripts/update_applicationset.py"],
        cwd=ROOT, text=True, capture_output=True, env=env,
    )
    if discover.stdout:
        print(discover.stdout, end="")
    if discover.stderr:
        print(discover.stderr, end="", file=sys.stderr)
    if discover.returncode != 0:
        return discover.returncode

    diff = subprocess.run(
        ["git", "diff", "--quiet", "--", "argocd/applicationset.yaml"], cwd=ROOT,
    )
    if diff.returncode == 0:
        print("argocd/applicationset.yaml ya estaba al día, nada que comitear.")
        return 0

    subprocess.run(["git", "add", "argocd/applicationset.yaml"], cwd=ROOT, check=True)
    subprocess.run(
        ["git", "commit", "-m", "chore(argocd): refresh crud repositories"],
        cwd=ROOT, check=True,
    )
    push = subprocess.run(["git", "push"], cwd=ROOT, text=True, capture_output=True)
    if push.stdout:
        print(push.stdout, end="")
    if push.stderr:
        print(push.stderr, end="", file=sys.stderr)
    return push.returncode


if __name__ == "__main__":
    raise SystemExit(main())
