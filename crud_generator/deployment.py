"""Generación de configuración por entorno y despliegue opcional GitOps."""

from pathlib import Path

ENVIRONMENTS = ("local", "dev", "pre", "pro")


def normalize_environment(value):
    value = (value or "local").strip().lower()
    aliases = {"prod": "pro", "production": "pro", "staging": "pre"}
    value = aliases.get(value, value)
    if value not in ENVIRONMENTS:
        raise ValueError(
            f"Entorno no soportado: '{value}'. Usa: {', '.join(ENVIRONMENTS)}."
        )
    return value


def _write(path, content):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.rstrip() + "\n", encoding="utf-8")


def _application_profile(environment):
    return f"""spring:
  config:
    activate:
      on-profile: {environment}

app:
  environment: {environment}
"""


def _k8s_namespace(namespace):
    return f"""apiVersion: v1
kind: Namespace
metadata:
  name: {namespace}
"""


def _k8s_deployment(app_name, namespace):
    return f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {app_name}
  namespace: {namespace}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {app_name}
  template:
    metadata:
      labels:
        app: {app_name}
    spec:
      containers:
        - name: {app_name}
          image: ${{IMAGE_REPOSITORY}}/{app_name}:${{IMAGE_TAG}}
          ports:
            - containerPort: 8080
          env:
            - name: SPRING_PROFILES_ACTIVE
              value: ${{SPRING_PROFILE}}
          envFrom:
            - secretRef:
                name: {app_name}-secrets
          readinessProbe:
            httpGet:
              path: /actuator/health
              port: 8080
            initialDelaySeconds: 15
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /actuator/health
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 20
---
apiVersion: v1
kind: Service
metadata:
  name: {app_name}
  namespace: {namespace}
spec:
  selector:
    app: {app_name}
  ports:
    - port: 80
      targetPort: 8080
"""


def _kustomization(app_name, namespace, environment):
    return f"""apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: {namespace}
resources:
  - namespace.yaml
  - deployment.yaml
configMapGenerator:
  - name: {app_name}-environment
    literals:
      - SPRING_PROFILES_ACTIVE={environment}
"""


def _argocd_application(app_name, namespace, environment, gitops_repo):
    return f"""apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: {app_name}-{environment}
  namespace: argocd
spec:
  project: default
  source:
    repoURL: {gitops_repo}
    targetRevision: main
    path: deploy/k8s
  destination:
    server: https://kubernetes.default.svc
    namespace: {namespace}
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
"""


def configure_deployment(
    base_dir,
    app_name,
    environment="local",
    use_argocd=False,
    namespace=None,
    gitops_repo=None,
):
    """Añade perfiles de entorno y, si procede, Kubernetes/Argo CD al proyecto.

    ``local`` usa Docker Compose ya generado por el scaffold y no crea recursos
    Kubernetes. ``dev``, ``pre`` y ``pro`` generan manifiestos Kubernetes; Argo CD
    es opcional y requiere la URL del repositorio GitOps/aplicación.
    """
    environment = normalize_environment(environment)
    app_name = app_name.strip().lower()
    namespace = (namespace or f"{app_name}-{environment}").strip()

    resources = Path(base_dir) / "src" / "main" / "resources"
    for profile in ENVIRONMENTS:
        _write(resources / f"application-{profile}.yml", _application_profile(profile))

    _write(
        Path(base_dir) / ".env.environment",
        f"SPRING_PROFILES_ACTIVE={environment}\nAPP_ENVIRONMENT={environment}",
    )

    if environment == "local":
        _write(
            Path(base_dir) / "deploy" / "README.md",
            "# Despliegue local\n\n"
            "Este proyecto usa Docker Compose para el entorno `local`.\n\n"
            "```bash\nSPRING_PROFILES_ACTIVE=local docker compose up --build\n```",
        )
        return {
            "environment": environment,
            "kubernetes": False,
            "argocd": False,
            "namespace": None,
        }

    k8s_dir = Path(base_dir) / "deploy" / "k8s"
    _write(k8s_dir / "namespace.yaml", _k8s_namespace(namespace))
    _write(k8s_dir / "deployment.yaml", _k8s_deployment(app_name, namespace))
    _write(k8s_dir / "kustomization.yaml", _kustomization(app_name, namespace, environment))

    if use_argocd:
        if not gitops_repo:
            raise ValueError("Argo CD requiere indicar el repositorio GitOps.")
        _write(
            Path(base_dir) / "deploy" / "argocd" / "application.yaml",
            _argocd_application(app_name, namespace, environment, gitops_repo),
        )

    return {
        "environment": environment,
        "kubernetes": True,
        "argocd": bool(use_argocd),
        "namespace": namespace,
    }
