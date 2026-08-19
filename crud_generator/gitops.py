"""Genera los manifiestos K8s + workflow GitOps que enganchan un proyecto
recien generado al ecosistema Argo CD, replicando a mano el patron que ya
se aplico en crud-transferencia-hexagonal, crud-dividendos-hexagonal, etc.

El generador (crud_generator.generator/ports_generator) no produce estos
ficheros: son infraestructura de despliegue, no del microservicio en si, y
dependen del nombre final del repositorio en GitHub. Se escriben aparte,
sobre un proyecto ya generado, justo antes de publicarlo.
"""

import os
import re

from .parsing import DefinitionError
from .writer import write_file

DEFAULT_OWNER = os.getenv("GITHUB_OWNER", "juanfranciscofernandezherreros")

_DB_NAME_RE = re.compile(r"POSTGRES_DB=(\S+)")


def get_k8s_manifests(repo_name, db_name):
    """Devuelve {ruta_relativa: contenido} para el directorio k8s/ del
    proyecto: namespace, secret, Postgres (Service + StatefulSet), el
    Service/Deployment de la app y el kustomization.yaml que los agrupa."""
    return {
        "namespace.yaml": f"""apiVersion: v1
kind: Namespace
metadata:
  name: {repo_name}
""",
        "secret.yaml": f"""apiVersion: v1
kind: Secret
metadata:
  name: {repo_name}-secrets
type: Opaque
stringData:
  POSTGRES_DB: {db_name}
  POSTGRES_USER: app_user
  POSTGRES_PASSWORD: change-me-local-only
  APP_SECURITY_USER: admin
  APP_SECURITY_PASSWORD: change-me-local-only
""",
        "postgres-service.yaml": """apiVersion: v1
kind: Service
metadata:
  name: postgres
spec:
  clusterIP: None
  selector:
    app.kubernetes.io/name: postgres
  ports:
    - name: postgres
      port: 5432
      targetPort: postgres
""",
        "postgres-statefulset.yaml": f"""apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: postgres
  template:
    metadata:
      labels:
        app.kubernetes.io/name: postgres
    spec:
      securityContext:
        fsGroup: 70
      containers:
        - name: postgres
          image: postgres:16-alpine
          imagePullPolicy: IfNotPresent
          ports:
            - name: postgres
              containerPort: 5432
          env:
            - name: POSTGRES_DB
              valueFrom:
                secretKeyRef:
                  name: {repo_name}-secrets
                  key: POSTGRES_DB
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: {repo_name}-secrets
                  key: POSTGRES_USER
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: {repo_name}-secrets
                  key: POSTGRES_PASSWORD
          readinessProbe:
            exec:
              command: ["sh", "-ec", "pg_isready -U \\"$POSTGRES_USER\\" -d \\"$POSTGRES_DB\\""]
            initialDelaySeconds: 5
            periodSeconds: 5
          livenessProbe:
            exec:
              command: ["sh", "-ec", "pg_isready -U \\"$POSTGRES_USER\\" -d \\"$POSTGRES_DB\\""]
            initialDelaySeconds: 20
            periodSeconds: 10
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 1Gi
""",
        "app-service.yaml": f"""apiVersion: v1
kind: Service
metadata:
  name: {repo_name}
spec:
  selector:
    app.kubernetes.io/name: {repo_name}
  ports:
    - name: http
      port: 8080
      targetPort: http
""",
        "deployment.yaml": f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {repo_name}
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: {repo_name}
  template:
    metadata:
      labels:
        app.kubernetes.io/name: {repo_name}
    spec:
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: app
          image: ghcr.io/{DEFAULT_OWNER}/{repo_name}:latest
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 8080
          env:
            - name: SPRING_DATASOURCE_URL
              value: jdbc:postgresql://postgres:5432/{db_name}
            - name: SPRING_DATASOURCE_USERNAME
              valueFrom:
                secretKeyRef:
                  name: {repo_name}-secrets
                  key: POSTGRES_USER
            - name: SPRING_DATASOURCE_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: {repo_name}-secrets
                  key: POSTGRES_PASSWORD
            - name: APP_SECURITY_USER
              valueFrom:
                secretKeyRef:
                  name: {repo_name}-secrets
                  key: APP_SECURITY_USER
            - name: APP_SECURITY_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: {repo_name}-secrets
                  key: APP_SECURITY_PASSWORD
            - name: TRACING_SAMPLING_PROBABILITY
              value: "0"
          startupProbe:
            httpGet:
              path: /actuator/health
              port: http
            failureThreshold: 30
            periodSeconds: 5
          readinessProbe:
            httpGet:
              path: /actuator/health
              port: http
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /actuator/health
              port: http
            periodSeconds: 20
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: "1"
              memory: 768Mi
          securityContext:
            runAsUser: 10001
            runAsGroup: 10001
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
""",
        "kustomization.yaml": f"""apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: {repo_name}

resources:
  - namespace.yaml
  - secret.yaml
  - postgres-service.yaml
  - postgres-statefulset.yaml
  - app-service.yaml
  - deployment.yaml

labels:
  - pairs:
      app.kubernetes.io/part-of: {repo_name}
""",
    }


def get_gitops_workflow():
    """Workflow que, en cada push a main, construye la imagen, la publica en
    GHCR y actualiza k8s/deployment.yaml con el sha recien publicado -- el
    mismo patron que ya usan crud-transferencia-hexagonal y el resto de
    repos onboardeados a mano."""
    return """name: GitOps image

on:
  push:
    branches: ["main"]
  workflow_dispatch:

permissions:
  contents: write
  packages: write

jobs:
  publish:
    if: github.actor != 'github-actions[bot]'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Iniciar sesion en GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Configurar Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Construir y publicar imagen
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          cache-from: type=gha
          cache-to: type=gha,mode=max
          tags: |
            ghcr.io/${{ github.repository }}:${{ github.sha }}
            ghcr.io/${{ github.repository }}:latest

      - name: Actualizar la referencia GitOps
        shell: bash
        run: |
          sed -i "s|image: ghcr.io/${GITHUB_REPOSITORY}:.*|image: ghcr.io/${GITHUB_REPOSITORY}:${GITHUB_SHA}|" k8s/deployment.yaml
          if git diff --quiet -- k8s/deployment.yaml; then
            exit 0
          fi
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add k8s/deployment.yaml
          git commit -m "chore(gitops): deploy ${GITHUB_SHA} [skip ci]"
          git push
"""


def extract_db_name(project_dir):
    """Lee el nombre de la base de datos del docker-compose.yml ya generado,
    en vez de re-derivarlo (entidad -> minusculas -> _db): asi el manifiesto
    de K8s queda garantizado en sync con lo que la app realmente espera."""
    compose_path = os.path.join(project_dir, "docker-compose.yml")
    try:
        with open(compose_path, encoding="utf-8") as file:
            content = file.read()
    except FileNotFoundError as error:
        raise DefinitionError(
            f"No se encontro '{compose_path}': hace falta para determinar el "
            "nombre de la base de datos antes de generar los manifiestos K8s."
        ) from error

    match = _DB_NAME_RE.search(content)
    if not match:
        raise DefinitionError(
            f"No se encontro 'POSTGRES_DB=' en '{compose_path}'."
        )
    return match.group(1)


def write_gitops_manifests(project_dir, repo_name):
    """Escribe k8s/*.yaml y .github/workflows/gitops.yml dentro de un
    proyecto ya generado, listos para el primer commit. Debe llamarse antes
    de publicar el repo (push_to_github hace 'git add -A' del directorio
    completo), y usa el mismo repo_name con el que se va a publicar."""
    db_name = extract_db_name(project_dir)

    for relative_path, content in get_k8s_manifests(repo_name, db_name).items():
        write_file(os.path.join(project_dir, "k8s", relative_path), content)

    write_file(
        os.path.join(project_dir, ".github", "workflows", "gitops.yml"),
        get_gitops_workflow(),
    )

    return db_name
