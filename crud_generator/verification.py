"""Verificación automática (mvn verify) de un proyecto ya generado.

Cierra la primera mitad del ciclo "genera -> verifica -> corrige": ejecuta
la build real y diagnostica el resultado. Deliberadamente NO parchea el
código generado por su cuenta -- solo reporta con la mayor claridad posible
qué pasó, para que la corrección (si hace falta) la decida un humano. Un
generador que reescribe su propia salida en base a heurísticas de un log de
Maven es más riesgo que ayuda; ver CLAUDE.md/README para el porqué de este
límite deliberado.
"""

import re
import shutil
import subprocess
from pathlib import Path

SUREFIRE_SUMMARY_PATTERN = re.compile(
    r"Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)"
)

# Patrones de fallo ya vistos generando y verificando proyectos reales en
# esta sesión: (fragmento de log, pista en español). Se busca por orden, la
# primera coincidencia gana.
_KNOWN_FAILURES = [
    (
        "Could not find a valid Docker environment",
        "Los tests de Testcontainers (PostgreSQL, Cucumber) necesitan Docker "
        "real. Si el resto de la build fue bien, esto NO es un fallo -- es el "
        "comportamiento documentado sin Docker disponible.",
    ),
    (
        "No tests matching pattern",
        "Surefire no encontró la clase de test esperada (revisa -Dtest=... y "
        "que el fichero se haya generado donde tocaba).",
    ),
    (
        "Non-resolvable parent POM",
        "No se pudo resolver una dependencia del pom.xml: revisa la conexión "
        "de red o el repositorio Maven local/remoto configurado.",
    ),
    (
        "COMPILATION ERROR",
        "Fallo de compilación Java: revisa el mensaje del compilador más "
        "abajo en el log completo.",
    ),
]


def _find_maven():
    return shutil.which("mvn.cmd") or shutil.which("mvn")


def _summarize_tests(base_dir):
    reports_dir = Path(base_dir) / "target" / "surefire-reports"
    if not reports_dir.is_dir():
        return None

    totals = {"run": 0, "failures": 0, "errors": 0, "skipped": 0}
    found = False
    for report in reports_dir.glob("*.txt"):
        text = report.read_text(encoding="utf-8", errors="ignore")
        match = SUREFIRE_SUMMARY_PATTERN.search(text)
        if not match:
            continue
        found = True
        run, failures, errors, skipped = (int(value) for value in match.groups())
        totals["run"] += run
        totals["failures"] += failures
        totals["errors"] += errors
        totals["skipped"] += skipped
    return totals if found else None


def _classify_failure(log):
    for needle, hint in _KNOWN_FAILURES:
        if needle in log:
            return hint
    return None


def verify_project(base_dir, goal="verify"):
    """Ejecuta 'mvn <goal>' sobre el proyecto ya generado en base_dir.

    Devuelve un dict:
      ran: False si Maven no está instalado (se omite, no es un error).
      success: True/False (solo si ran es True).
      returncode, log: la salida completa de Maven (solo si ran es True).
      hint: pista en español si el fallo coincide con un patrón conocido.
      tests: resumen agregado de target/surefire-reports/*.txt, si existe.
    """
    mvn = _find_maven()
    if not mvn:
        return {
            "ran": False,
            "summary": "Maven no está instalado: se omite la verificación.",
        }

    result = subprocess.run(
        [mvn, "-q", "-B", goal],
        cwd=base_dir,
        capture_output=True,
        text=True,
    )
    log = (result.stdout or "") + (result.stderr or "")
    success = result.returncode == 0

    return {
        "ran": True,
        "success": success,
        "returncode": result.returncode,
        "log": log,
        "hint": None if success else _classify_failure(log),
        "tests": _summarize_tests(base_dir),
    }
