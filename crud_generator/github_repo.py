"""Publica un proyecto ya generado como un repositorio nuevo en GitHub.

Usa la CLI 'gh' (que el usuario autentica una vez con 'gh auth login') en
vez de manejar un token a mano: sin dependencias externas de Python (no
anade 'requests' al generador, que no tiene ninguna) y sin credenciales en
texto plano en el repositorio -- a diferencia del script original que este
modulo reemplaza, que llevaba un token de GitHub pegado en el fichero.
"""

import os
import subprocess

from .parsing import DefinitionError


def _run(args, cwd=None):
    try:
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    except FileNotFoundError as error:
        raise DefinitionError(
            f"No se encontro el ejecutable '{args[0]}'. Instala GitHub CLI "
            "(https://cli.github.com/) y Git, y asegurate de que estan en el PATH."
        ) from error

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise DefinitionError(f"'{' '.join(args)}' fallo: {detail}")
    return result.stdout.strip()


def push_to_github(project_dir, repo_name=None, private=False, description=None):
    """Crea el repo `repo_name` en GitHub (cuenta ya autenticada con `gh`) a
    partir del proyecto en `project_dir` (ya generado por --json/--stream/
    --batch/el DSL de texto) y lo sube. Devuelve la URL del repo creado.

    Si `project_dir` todavia no es un repositorio Git, lo inicializa y crea
    el primer commit; si ya lo es, sube los cambios pendientes tal cual.
    """
    if not os.path.isdir(project_dir):
        raise DefinitionError(f"El directorio '{project_dir}' no existe.")

    project_dir = os.path.abspath(project_dir)
    repo_name = repo_name or os.path.basename(project_dir)
    description = description or f"Proyecto generado con crud-automation ({repo_name})"

    if not os.path.isdir(os.path.join(project_dir, ".git")):
        _run(["git", "init", "-b", "main"], cwd=project_dir)

    _run(["git", "add", "-A"], cwd=project_dir)
    if _run(["git", "status", "--porcelain"], cwd=project_dir):
        _run(["git", "commit", "-m", f"Initial commit: {repo_name}"], cwd=project_dir)

    visibility = "--private" if private else "--public"
    _run(
        [
            "gh", "repo", "create", repo_name,
            visibility,
            "--description", description,
            "--source", project_dir,
            "--remote", "origin",
            "--push",
        ]
    )

    # Cada repo nuevo nace con las Actions en modo solo lectura
    # (default_workflow_permissions=read), lo que le niega a GITHUB_TOKEN el
    # permiso de escritura aunque el workflow lo pida (permissions: packages:
    # write) -- y con eso, cualquier workflow que publique en GHCR o comitee
    # de vuelta (como gitops.yml) falla con "denied: permission_denied".
    _run(
        [
            "gh", "api", "-X", "PUT", f"repos/{{owner}}/{repo_name}/actions/permissions/workflow",
            "-f", "default_workflow_permissions=write",
            "-F", "can_approve_pull_request_reviews=false",
        ],
        cwd=project_dir,
    )

    return _run(["gh", "repo", "view", repo_name, "--json", "url", "-q", ".url"])
