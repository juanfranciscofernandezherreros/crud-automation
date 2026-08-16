"""Regenera el ApplicationSet con repos publicos crud-* preparados para K8s."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

OWNER = os.getenv("GITHUB_OWNER", "juanfranciscofernandezherreros")
TOKEN = os.getenv("GITHUB_TOKEN", "")
OUTPUT = Path(__file__).resolve().parents[1] / "argocd" / "applicationset.yaml"


def api_get(path: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "crud-automation-applicationset",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    request = Request(f"https://api.github.com{path}", headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def has_kustomization(repo: str, branch: str) -> bool:
    path = f"/repos/{OWNER}/{repo}/contents/k8s/kustomization.yaml?ref={branch}"
    try:
        api_get(path)
        return True
    except HTTPError as exc:
        if exc.code == 404:
            return False
        raise


def discover() -> list[tuple[str, str]]:
    repos = api_get(f"/users/{OWNER}/repos?per_page=100&type=public&sort=full_name")
    selected = []
    for repo in repos:
        name = repo["name"]
        if (
            name.startswith("crud-")
            and not repo["archived"]
            and has_kustomization(name, repo["default_branch"])
        ):
            selected.append((name, repo["default_branch"]))
    return sorted(selected)


def render(repos: list[tuple[str, str]]) -> str:
    elements = "\n".join(
        f"          - repo: {name}\n            branch: {branch}"
        for name, branch in repos
    )
    return f"""apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: crud-repositories
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]
  generators:
    - list:
        elements:
{elements}
  template:
    metadata:
      name: "{{{{.repo}}}}"
      labels:
        app.kubernetes.io/managed-by: crud-repositories
    spec:
      project: default
      source:
        repoURL: "https://github.com/{OWNER}/{{{{.repo}}}}.git"
        targetRevision: "{{{{.branch}}}}"
        path: k8s
      destination:
        server: https://kubernetes.default.svc
        namespace: "{{{{.repo}}}}"
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true
          - PruneLast=true
          - ApplyOutOfSyncOnly=true
"""


def main() -> None:
    repos = discover()
    if not repos:
        raise SystemExit("No se encontraron repositorios crud-* con k8s/kustomization.yaml")
    OUTPUT.write_text(render(repos), encoding="utf-8", newline="\n")
    print(f"ApplicationSet actualizado con {len(repos)} repositorios")


if __name__ == "__main__":
    main()

