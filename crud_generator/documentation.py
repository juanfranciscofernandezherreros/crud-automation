"""Generacion de documentacion HTML autocontenida para cada proyecto."""

from html import escape

from .architectures import DEFAULT_BASE_PACKAGE
from .fields import format_default_sql_literal, generate_composite_unique_groups
from .parsing import DEFAULT_ENDPOINTS, pluralize


ARCHITECTURE_DETAILS = {
    "layered": {
        "label": "Arquitectura por capas",
        "description": (
            "Organiza el flujo HTTP, negocio y persistencia en capas explicitas "
            "con responsabilidades separadas."
        ),
        "nodes": (
            ("Controller", "API REST, DTO y validacion"),
            ("Service", "Transacciones y casos de negocio"),
            ("Repository", "Acceso a datos con Spring Data"),
            ("PostgreSQL", "Flyway, indices y restricciones"),
        ),
    },
    "hexagonal": {
        "label": "Arquitectura hexagonal",
        "description": (
            "El dominio y los casos de uso quedan aislados de HTTP, Spring y "
            "JPA mediante puertos y adaptadores."
        ),
        "nodes": (
            ("Adaptador web", "Controller, DTO y WebMapper"),
            ("Puerto de entrada", "Contrato del caso de uso"),
            ("Dominio", "Servicio Java puro y paginacion"),
            ("Adaptador JPA", "Puerto de salida y PostgreSQL"),
        ),
    },
    "clean": {
        "label": "Clean Architecture",
        "description": (
            "Las dependencias apuntan hacia entidades y casos de uso; frameworks "
            "y transporte permanecen en el exterior."
        ),
        "nodes": (
            ("Interface adapter", "Controller, DTO y mapper"),
            ("Use case", "Puerto de entrada y servicio puro"),
            ("Entity", "Modelo de dominio independiente"),
            ("Framework", "Gateway JPA y PostgreSQL"),
        ),
    },
}


def _project_directory(entity_lower, architecture):
    suffix = "" if architecture == "layered" else f"-{architecture}"
    return f"crud-{entity_lower}{suffix}"


def _rule_text(attr):
    validations = attr["validations"]
    rules = []
    for name, value in validations.items():
        rules.append(name if value is True else f"{name}={value}")
    if attr["is_audit"]:
        rules.append("auditoria")
    if attr["is_id"]:
        rules.append("clave primaria")
    return ", ".join(rules) or "sin reglas adicionales"


def _database_text(attr):
    if attr["is_id"]:
        return "SERIAL PRIMARY KEY"
    validations = attr["validations"]
    sql_type = attr["sql_type"]
    if attr["type"] == "string" and "max" in validations:
        sql_type = f"VARCHAR({validations['max']})"
    constraints = []
    if attr["name"] in {"creado_en", "created_at"}:
        constraints.extend(("NOT NULL", "DEFAULT CURRENT_TIMESTAMP"))
    elif validations.get("required") or validations.get("not_blank"):
        constraints.append("NOT NULL")
    if "default" in validations:
        constraints.append(f"DEFAULT {format_default_sql_literal(attr)}")
    if validations.get("unique"):
        constraints.append("UNIQUE")
    if validations.get("composite_unique"):
        constraints.append(f"UNIQUE CON ({validations['composite_unique']})")
    if any(key in validations for key in ("not_blank", "positive", "min", "max")):
        constraints.append("CHECK")
    if validations.get("index") and not validations.get("unique"):
        constraints.append("INDEX")
    return " ".join([sql_type, *constraints])


def _composite_unique_callout(attrs):
    groups = generate_composite_unique_groups(attrs)
    if not groups:
        return ""
    items = "".join(
        f"<li><code>{escape(group)}</code>: "
        f"{escape(', '.join(members))}</li>"
        for group, members in groups.items()
    )
    return (
        '<div class="callout"><strong>Claves compuestas:</strong> '
        f"<ul>{items}</ul></div>"
    )


def _field_rows(attrs):
    rows = []
    for attr in attrs:
        rows.append(
            "<tr>"
            f"<td><code>{escape(attr['name'])}</code></td>"
            f"<td>{escape(attr['java_type'])}</td>"
            f"<td>{escape(_rule_text(attr))}</td>"
            f"<td>{escape(_database_text(attr))}</td>"
            "</tr>"
        )
    rows.append(
        "<tr><td><code>version</code></td><td>Long</td>"
        "<td>concurrencia optimista</td><td>BIGINT NOT NULL DEFAULT 0</td></tr>"
    )
    return "\n".join(rows)


_JSON_SOURCE_PREFIX = "__JSON__:"


def _command(entity_name, attrs_str, architecture):
    if attrs_str.startswith(_JSON_SOURCE_PREFIX):
        json_path = attrs_str[len(_JSON_SOURCE_PREFIX):]
        return (
            f'python .\\generate_crud.py --json "{json_path}" `\n'
            f"  --architecture {architecture}"
        )
    definitions = [part.strip() for part in attrs_str.split(",")]
    lines = [f'python .\\generate_crud.py {entity_name} `']
    for index, definition in enumerate(definitions):
        comma = "," if index < len(definitions) - 1 else ""
        lines.append(f'  "{definition}{comma}" `')
    lines.append(f"  --architecture {architecture}")
    return "\n".join(lines)


def _architecture_nodes(architecture):
    return "\n".join(
        f'<article class="flow-node"><h3>{escape(title)}</h3><p>{escape(body)}</p></article>'
        for title, body in ARCHITECTURE_DETAILS[architecture]["nodes"]
    )


def _operation_rows(endpoint, endpoints):
    rows = []
    if "create" in endpoints:
        rows.append(
            f'<tr><td><span class="method post">POST</span></td><td><code>{endpoint}</code></td>'
            "<td>ADMIN</td><td>201, requiere Idempotency-Key</td></tr>"
        )
    if "list" in endpoints:
        rows.append(
            '<tr><td><span class="method get">GET</span></td>'
            f'<td><code>{endpoint}?page=0&amp;size=20&amp;sort=id</code></td>'
            "<td>USER / ADMIN</td><td>Pagina de resultados</td></tr>"
        )
    if "get" in endpoints:
        rows.append(
            '<tr><td><span class="method get">GET</span></td>'
            f'<td><code>{endpoint}/{{id}}</code></td>'
            "<td>USER / ADMIN</td><td>Recurso individual</td></tr>"
        )
    if "update" in endpoints:
        rows.append(
            '<tr><td><span class="method write">PUT</span></td>'
            f'<td><code>{endpoint}/{{id}}</code></td>'
            "<td>ADMIN</td><td>Actualizacion completa</td></tr>"
        )
    if "patch" in endpoints:
        rows.append(
            '<tr><td><span class="method write">PATCH</span></td>'
            f'<td><code>{endpoint}/{{id}}</code></td>'
            "<td>ADMIN</td><td>Actualizacion parcial</td></tr>"
        )
    if "delete" in endpoints:
        rows.append(
            '<tr><td><span class="method delete">DELETE</span></td>'
            f'<td><code>{endpoint}/{{id}}</code></td>'
            "<td>ADMIN</td><td>204 sin contenido</td></tr>"
        )
    return "".join(rows)


def get_documentation_html(
    entity_name, entity_lower, architecture, attrs, attrs_str,
    base_package=None, endpoints=None,
):
    """Devuelve la documentacion tecnica completa y lista para abrir."""
    base_package = base_package or DEFAULT_BASE_PACKAGE
    endpoints = endpoints or list(DEFAULT_ENDPOINTS)
    details = ARCHITECTURE_DETAILS[architecture]
    project_dir = _project_directory(entity_lower, architecture)
    endpoint = f"/api/{pluralize(entity_lower)}"
    database = f"{entity_lower}_db"
    command = escape(_command(entity_name, attrs_str, architecture))
    field_rows = _field_rows(attrs)
    composite_unique_callout = _composite_unique_callout(attrs)
    nodes = _architecture_nodes(architecture)
    operation_rows = _operation_rows(endpoint, endpoints)
    package_callout = (
        f'<div class="callout"><strong>Paquete base:</strong> <code>{escape(base_package)}</code></div>'
        if base_package != DEFAULT_BASE_PACKAGE
        else ""
    )
    entity = escape(entity_name)
    architecture_label = escape(details["label"])
    architecture_description = escape(details["description"])

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Documentacion tecnica de {entity}.">
  <title>{entity} | {architecture_label}</title>
  <style>
    :root {{
      --ink:#17211c; --muted:#58645e; --paper:#f7f8f5; --surface:#fff;
      --line:#d9dfda; --green:#176b4b; --green-dark:#0f4934;
      --amber:#b66b13; --blue:#276690; --danger:#a33a32; --code:#111915;
      --radius:6px; --shadow:0 8px 24px rgba(23,33,28,.08);
    }}
    * {{ box-sizing:border-box; }}
    html {{ scroll-behavior:smooth; }}
    body {{ margin:0; color:var(--ink); background:var(--paper); font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; line-height:1.55; }}
    a {{ color:inherit; }} button {{ font:inherit; }}
    .topbar {{ position:sticky; top:0; z-index:20; display:flex; align-items:center; justify-content:space-between; min-height:58px; padding:0 28px; color:#fff; background:var(--ink); border-bottom:3px solid var(--amber); }}
    .brand {{ font-weight:760; }} .topbar nav {{ display:flex; gap:20px; }}
    .topbar a {{ color:#e7eee9; text-decoration:none; font-size:14px; }}
    .hero {{ min-height:390px; display:grid; align-content:center; padding:54px max(28px,calc((100vw - 1180px)/2)); color:#fff; background:#103a2b; border-bottom:1px solid #234e3d; }}
    .hero-copy {{ max-width:880px; }} .eyebrow {{ display:inline-block; margin-bottom:14px; color:#f2c77e; font-size:13px; font-weight:750; text-transform:uppercase; }}
    h1,h2,h3 {{ margin-top:0; line-height:1.16; }} h1 {{ margin-bottom:18px; font-size:64px; font-weight:800; overflow-wrap:anywhere; }}
    .hero p {{ max-width:780px; margin:0; color:#d8e5dd; font-size:19px; }}
    .hero-meta {{ display:flex; flex-wrap:wrap; gap:18px; margin-top:30px; }}
    .metric {{ padding-left:12px; border-left:3px solid var(--amber); }} .metric strong {{ display:block; font-size:17px; }} .metric span {{ color:#bfd0c5; font-size:13px; }}
    .layout {{ display:grid; grid-template-columns:235px minmax(0,1fr); gap:42px; width:min(1180px,calc(100% - 48px)); margin:0 auto; padding:48px 0 80px; }}
    .toc {{ position:sticky; top:86px; align-self:start; padding-right:20px; border-right:1px solid var(--line); }}
    .toc strong {{ display:block; margin-bottom:10px; font-size:13px; text-transform:uppercase; }}
    .toc a {{ display:block; padding:6px 0; color:var(--muted); text-decoration:none; font-size:14px; }} .toc a:hover {{ color:var(--green); }}
    main {{ min-width:0; }} section {{ padding:10px 0 48px; border-bottom:1px solid var(--line); }} section+section {{ padding-top:48px; }} section:last-child {{ border:0; }}
    h2 {{ margin-bottom:12px; font-size:29px; }} h3 {{ margin-bottom:8px; font-size:18px; }} .lead {{ max-width:790px; color:var(--muted); font-size:17px; }}
    .section-mark {{ color:var(--green); }} .callout {{ margin:22px 0; padding:16px 18px; background:#edf6f1; border-left:4px solid var(--green); border-radius:0 var(--radius) var(--radius) 0; }}
    .warning {{ background:#fff7e9; border-color:var(--amber); }}
    .code-wrap {{ position:relative; margin-top:20px; }} pre {{ overflow-x:auto; margin:0; padding:22px; color:#e8eee9; background:var(--code); border:1px solid #2e3933; border-radius:var(--radius); font:13px/1.65 "Cascadia Code",Consolas,monospace; white-space:pre; }}
    .copy {{ position:absolute; top:10px; right:10px; min-width:116px; padding:7px 11px; color:#fff; background:#314039; border:1px solid #53645b; border-radius:4px; cursor:pointer; font-size:12px; }} .copy:hover {{ background:#405149; }}
    .flow {{ display:grid; grid-template-columns:repeat(4,minmax(130px,1fr)); gap:22px; margin:28px 0; }}
    .flow-node {{ position:relative; min-height:132px; padding:18px; background:var(--surface); border:1px solid var(--line); border-top:4px solid var(--green); border-radius:var(--radius); box-shadow:var(--shadow); }}
    .flow-node:not(:last-child)::after {{ content:""; position:absolute; top:50%; right:-16px; width:9px; height:9px; border-top:2px solid var(--amber); border-right:2px solid var(--amber); transform:translateY(-50%) rotate(45deg); }}
    .flow-node:nth-child(2) {{ border-top-color:var(--blue); }} .flow-node:nth-child(3) {{ border-top-color:var(--amber); }} .flow-node:nth-child(4) {{ border-top-color:var(--danger); }} .flow-node p {{ margin:0; color:var(--muted); font-size:14px; }}
    .grid-2,.grid-3 {{ display:grid; gap:18px; margin-top:22px; }} .grid-2 {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} .grid-3 {{ grid-template-columns:repeat(3,minmax(0,1fr)); }}
    .panel {{ padding:20px; background:var(--surface); border:1px solid var(--line); border-radius:var(--radius); }} .panel p {{ margin:0; color:var(--muted); font-size:14px; }}
    .label {{ display:inline-block; margin-bottom:10px; color:var(--green-dark); font:700 12px/1.2 "Cascadia Code",Consolas,monospace; text-transform:uppercase; }}
    .table-wrap {{ overflow-x:auto; margin-top:22px; border:1px solid var(--line); }} table {{ width:100%; border-collapse:collapse; background:var(--surface); font-size:14px; }}
    th,td {{ padding:12px 14px; text-align:left; border-bottom:1px solid var(--line); }} th {{ color:#fff; background:var(--green-dark); font-size:12px; text-transform:uppercase; }} tr:last-child td {{ border-bottom:0; }} td code,p code,.callout code {{ color:var(--green-dark); font-family:"Cascadia Code",Consolas,monospace; font-weight:650; }}
    .method {{ font:750 12px/1 monospace; }} .get {{ color:var(--blue); }} .post {{ color:var(--green); }} .write {{ color:var(--amber); }} .delete {{ color:var(--danger); }}
    .steps {{ margin:24px 0 0; padding:0; list-style:none; counter-reset:step; }} .steps li {{ position:relative; min-height:54px; padding:0 0 22px 50px; counter-increment:step; }}
    .steps li::before {{ content:counter(step); position:absolute; left:0; top:-2px; display:grid; place-items:center; width:32px; height:32px; color:#fff; background:var(--green); border-radius:50%; font-weight:750; }}
    footer {{ padding:28px; color:#cad5ce; background:var(--ink); text-align:center; font-size:13px; }}
    @media(max-width:900px) {{ .topbar nav,.toc {{ display:none; }} .layout {{ grid-template-columns:1fr; width:min(100% - 32px,760px); }} .flow {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} .flow-node::after {{ display:none; }} .grid-3 {{ grid-template-columns:1fr 1fr; }} }}
    @media(max-width:580px) {{ .topbar {{ padding:0 16px; }} .hero {{ min-height:430px; padding:42px 20px; }} h1 {{ font-size:40px; }} .hero p {{ font-size:17px; }} .layout {{ width:min(100% - 24px,760px); padding-top:28px; }} .flow,.grid-2,.grid-3 {{ grid-template-columns:1fr; }} .flow-node {{ min-height:auto; }} pre {{ padding:18px 14px; font-size:12px; }} .copy {{ position:static; width:100%; margin-bottom:7px; }} }}
  </style>
</head>
<body>
  <header class="topbar"><div class="brand">{entity}</div><nav aria-label="Navegacion principal"><a href="#generacion">Generacion</a><a href="#modelo">Modelo</a><a href="#arquitectura">Arquitectura</a><a href="#api">API</a><a href="#pruebas">Pruebas</a></nav></header>
  <header class="hero"><div class="hero-copy"><span class="eyebrow">Microservicio Spring Boot 3 / Java 21</span><h1>{entity}</h1><p>{architecture_description}</p><div class="hero-meta"><div class="metric"><strong>{architecture_label}</strong><span>Organizacion del codigo</span></div><div class="metric"><strong>PostgreSQL 16</strong><span>Flyway y Testcontainers</span></div><div class="metric"><strong>Seguridad</strong><span>Roles y rate limiting</span></div><div class="metric"><strong>OpenTelemetry</strong><span>Metricas y trazas</span></div></div></div></header>
  <div class="layout">
    <aside class="toc"><strong>Contenido</strong><a href="#generacion">1. Generacion</a><a href="#modelo">2. Modelo</a><a href="#arquitectura">3. Arquitectura</a><a href="#api">4. API REST</a><a href="#produccion">5. Produccion</a><a href="#ejecucion">6. Ejecucion</a><a href="#pruebas">7. Pruebas</a></aside>
    <main>
      <section id="generacion"><span class="eyebrow section-mark">01 / Generacion</span><h2>Comando reproducible</h2><p class="lead">Este comando vuelve a generar el mismo proyecto, con sus tipos, validaciones y arquitectura.</p><div class="code-wrap"><button class="copy" data-copy="generator-command">Copiar comando</button><pre id="generator-command"><code>{command}</code></pre></div><div class="callout"><strong>Salida:</strong> <code>{escape(project_dir)}/</code>, proyecto Maven independiente y ejecutable.</div></section>
      <section id="modelo"><span class="eyebrow section-mark">02 / Modelo</span><h2>Campos e invariantes</h2><p class="lead">Bean Validation protege la API y Flyway traslada las reglas compatibles a PostgreSQL.</p><div class="table-wrap"><table><thead><tr><th>Campo</th><th>Java</th><th>Reglas</th><th>PostgreSQL</th></tr></thead><tbody>{field_rows}</tbody></table></div>{composite_unique_callout}</section>
      <section id="arquitectura"><span class="eyebrow section-mark">03 / Arquitectura</span><h2>{architecture_label}</h2><p class="lead">{architecture_description}</p><div class="flow">{nodes}</div><div class="grid-3"><article class="panel"><span class="label">Paginacion</span><h3>Consultas acotadas</h3><p>20 elementos por defecto y 100 como maximo.</p></article><article class="panel"><span class="label">Concurrencia</span><h3>Version optimista</h3><p>JPA usa <code>@Version</code> y devuelve conflictos HTTP 409.</p></article><article class="panel"><span class="label">Persistencia</span><h3>Esquema validado</h3><p>Hibernate valida el esquema creado por Flyway.</p></article></div></section>
      <section id="api"><span class="eyebrow section-mark">04 / API REST</span><h2>Operaciones disponibles</h2><div class="table-wrap"><table><thead><tr><th>Metodo</th><th>Ruta</th><th>Rol</th><th>Resultado</th></tr></thead><tbody>{operation_rows}</tbody></table></div>{package_callout}</section>
      <section id="produccion"><span class="eyebrow section-mark">05 / Produccion</span><h2>Controles operativos</h2><div class="grid-2"><article class="panel"><span class="label">Seguridad</span><h3>Autorizacion por roles</h3><p>HTTP Basic stateless, lectura USER/ADMIN y escritura ADMIN.</p></article><article class="panel"><span class="label">Idempotencia</span><h3>Altas sin duplicados</h3><p>PostgreSQL conserva la clave y serializa solicitudes concurrentes.</p></article><article class="panel"><span class="label">Disponibilidad</span><h3>Rate limiting</h3><p>Limite por minuto e IP configurable por entorno.</p></article><article class="panel"><span class="label">Observabilidad</span><h3>Metricas y trazas</h3><p>Actuator, Prometheus, traceId, spanId y exportacion OTLP.</p></article></div></section>
      <section id="ejecucion"><span class="eyebrow section-mark">06 / Ejecucion</span><h2>Configuracion local</h2><div class="code-wrap"><button class="copy" data-copy="run-command">Copiar variables</button><pre id="run-command"><code>$env:SPRING_DATASOURCE_URL = "jdbc:postgresql://localhost:5432/{database}"
$env:SPRING_DATASOURCE_USERNAME = "app_user"
$env:SPRING_DATASOURCE_PASSWORD = "cambiar-en-produccion"
$env:APP_SECURITY_USER = "admin"
$env:APP_SECURITY_PASSWORD = "otra-clave-segura"

mvn -f .\\{escape(project_dir)}\\pom.xml spring-boot:run</code></pre></div><div class="callout warning"><strong>Importante:</strong> usa un gestor de secretos para las credenciales reales.</div><h3>Con Docker</h3><p class="lead">Copia <code>.env.example</code> a <code>.env</code> y ajusta los valores; <code>docker compose</code> lo carga automaticamente. Sin ese fichero, <code>docker compose up</code> falla con <code>required variable POSTGRES_USER is missing a value</code>, porque las cuatro variables son obligatorias en <code>docker-compose.yml</code>.</p><div class="code-wrap"><button class="copy" data-copy="docker-command">Copiar comando</button><pre id="docker-command"><code>copy .env.example .env
docker compose up -d --build</code></pre></div></section>
      <section id="pruebas"><span class="eyebrow section-mark">07 / Pruebas</span><h2>Verificacion completa</h2><ol class="steps"><li><strong>Tests unitarios.</strong> Validan el servicio y sus reglas aisladas.</li><li><strong>Tests MVC.</strong> Comprueban JSON, validacion, seguridad y estados HTTP.</li><li><strong>PostgreSQL real.</strong> Testcontainers inicia PostgreSQL 16 y ejecuta Flyway.</li><li><strong>Idempotencia.</strong> Verifica que una clave repetida solo crea una vez.</li><li><strong>Empaquetado.</strong> Maven construye el JAR ejecutable.</li></ol><div class="code-wrap"><button class="copy" data-copy="verify-command">Copiar verificacion</button><pre id="verify-command"><code>mvn -f .\\{escape(project_dir)}\\pom.xml verify</code></pre></div></section>
    </main>
  </div>
  <footer>Documentacion tecnica generada automaticamente | {entity}</footer>
  <script>
    document.querySelectorAll("[data-copy]").forEach((button) => {{
      button.addEventListener("click", async () => {{
        const target = document.getElementById(button.dataset.copy);
        try {{
          await navigator.clipboard.writeText(target.innerText);
          const label = button.textContent; button.textContent = "Copiado";
          setTimeout(() => {{ button.textContent = label; }}, 1400);
        }} catch {{
          const range = document.createRange(); range.selectNodeContents(target);
          const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
        }}
      }});
    }});
  </script>
</body>
</html>
"""
