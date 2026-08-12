# Generador de CRUD Spring Boot

Automatizacion en Python que genera un CRUD con Spring Boot, PostgreSQL,
Flyway, MapStruct, Docker, seguridad, observabilidad y pruebas reales con
Testcontainers. El repositorio conserva solo el generador; `crud-*` son salidas
recreables y estan excluidas de Git.

## Requisitos

- Python 3.10 o superior, sin dependencias externas.
- Java 21 y Maven 3.9 para compilar los proyectos generados.
- Docker para ejecutar las pruebas PostgreSQL de Testcontainers.

## Uso

```powershell
python .\generate_crud.py Producto `
  "id:int, nombre:string:not_blank:max=120:index, precio:decimal:required:positive"
```

Sin `--architecture`, una terminal interactiva pregunta la arquitectura:

```text
Arquitectura:
  1. layered
  2. hexagonal
  3. clean
Selecciona una opcion [1]:
```

Para scripts y CI se indica explicitamente:

```powershell
python .\generate_crud.py Producto `
  "id:int, nombre:string:not_blank, precio:decimal:required:positive" `
  --architecture hexagonal
```

| Arquitectura | Organizacion principal | Directorio |
| --- | --- | --- |
| `layered` | Controller, service, repository y entity | `crud-producto/` |
| `hexagonal` | Dominio, puertos y adaptadores | `crud-producto-hexagonal/` |
| `clean` | Entidades, casos de uso, gateways, adapters y frameworks | `crud-producto-clean/` |

En hexagonal y clean, el servicio de aplicacion es Java puro: no contiene
anotaciones ni tipos de Spring. Las transacciones quedan en el adaptador de
persistencia y el wiring en `UseCaseConfiguration`.

## Definicion por JSON

Para esquemas grandes o generados por herramienta (muchos campos, o cuando el
propio `default` necesita `:` o `,`) es mas comodo describir la entidad en un
JSON en vez de en la cadena `nombre:tipo:regla`:

```powershell
python .\generate_crud.py --json .\fondoinversion.json --architecture hexagonal
```

```json
{
  "entity": "FondoInversion",
  "architecture": "hexagonal",
  "fields": [
    {"name": "id", "type": "int"},
    {"name": "isin", "type": "string", "max": 12, "not_blank": true, "unique": true, "index": true},
    {"name": "patrimonio", "type": "decimal", "precision": 18, "scale": 2, "required": true, "positive": true},
    {"name": "activo", "type": "boolean", "required": true, "default": true},
    {"name": "fecha_valor", "type": "datetime", "default": "2026-01-31T10:30:00"},
    {"name": "descripcion", "type": "text"}
  ]
}
```

Reglas:

- `entity` es obligatorio. `architecture` es opcional (por defecto `layered`);
  si tambien se pasa `--architecture` en la linea de comandos, la CLI gana.
- Cada campo es un objeto con `name` y `type`, mas cualquiera de las reglas
  del DSL de texto como clave: `required`, `not_blank`, `positive`, `unique`,
  `index` (booleanos), `min`, `max`, `precision`, `scale` (numeros),
  `composite_unique` (texto), `default` (cualquier tipo, ver abajo).
- A diferencia del DSL de texto, los valores de `default` **no tienen
  restriccion de caracteres**: pueden llevar `:` o `,` sin problema (por
  ejemplo `"default": "2026-01-31T10:30:00"` con hora completa, o un texto
  como `"default": "Madrid, España"`). Esto es posible porque el JSON nunca
  se reconstruye como una cadena delimitada por `:`/`,` antes de parsearse —
  se valida directamente sobre la estructura.
- Claves desconocidas en un campo, o a nivel raiz del JSON, son un error
  (mismo criterio "falla antes de escribir" que el DSL de texto).

El `docs/index.html` generado muestra el comando `--json` reproducible.

`crud_generator/schema/entity.schema.json` (JSON Schema Draft 7) documenta
formalmente este formato — util para autocompletado/validacion en el editor
referenciandolo con `"$schema": "../crud_generator/schema/entity.schema.json"`
en tu fichero de entidad. `python -m pytest tests/test_entity_schema.py` lo
valida contra los ejemplos de `examples/` cuando `jsonschema` esta instalado
(dependencia opcional solo para ese test; el generador en si no la necesita).

### Varias entidades relacionadas (`entities`)

Para relaciones `@ManyToOne` entre dos o mas entidades, usa `entities` en vez
de `entity`/`fields`. Funciona con las tres arquitecturas (`layered`,
`hexagonal`, `clean`):

```json
{
  "project": "ventas",
  "package": "com.miempresa.ventas",
  "entities": [
    {
      "entity": "Cliente",
      "fields": [
        {"name": "id", "type": "int"},
        {"name": "nombre", "type": "string", "not_blank": true, "required": true}
      ]
    },
    {
      "entity": "Pedido",
      "fields": [
        {"name": "id", "type": "int"},
        {"name": "cliente", "type": "reference", "references": "Cliente", "required": true, "index": true},
        {"name": "total", "type": "decimal", "precision": 12, "scale": 2, "required": true, "positive": true}
      ]
    }
  ]
}
```

Un campo `type: "reference"` con `references: "<OtraEntidad>"` genera, para
`cliente`:

- La columna `cliente_id INT [NOT NULL] REFERENCES clientes(id)` en la
  migracion Flyway (con `CREATE INDEX` si ademas se indica `index: true`).
- `@ManyToOne(fetch = FetchType.LAZY)` + `@JoinColumn` en la entidad JPA
  (`PedidoJpaEntity` en hexagonal/clean, `Pedido` en layered).
- Un campo `clienteId` (`Integer`) en cada DTO, no el objeto completo (evita
  ciclos de serializacion y sobre-carga de datos). En hexagonal/clean, el
  modelo de dominio (`Pedido`) tambien guarda `clienteId`, no el objeto: el
  dominio no tiene acceso a un repositorio para resolverlo.
- Resolucion contra el repositorio de `Cliente` justo antes de guardar:
  en layered, en `PedidoServiceImpl` (`create`/`update` siempre resuelven
  `clienteId`, 404 `ResourceNotFoundException` si no existe; `patch` solo lo
  toca si el DTO lo incluye); en hexagonal/clean, en
  `PedidoPersistenceAdapter.save()` (el unico punto de escritura del puerto,
  cubre create y update por igual).

`references` puede apuntar a otra entidad de la misma lista o a si misma
(relaciones reflexivas, p.ej. un arbol de categorias vía `padre`). Las
dependencias circulares entre dos entidades distintas (A referencia a B y B
a A) no estan soportadas y el generador lo rechaza explicitamente. El
directorio del proyecto usa `project` si se indica, o el nombre de la
primera entidad listada.

### Campos `enum`

```json
{"name": "estado", "type": "enum", "values": ["PENDIENTE", "PAGADO", "ENVIADO"], "required": true, "default": "PENDIENTE"}
```

`values` son las constantes del enum Java generado (`MAYUSCULAS_CON_GUION_BAJO`,
al menos dos). El generador escribe una clase `Estado.java` junto a la entidad
(`entity/` en layered, `domain/model/` en hexagonal/clean, para que quede en
el mismo paquete que el dominio y no haga falta importarla ahi), anota el
campo con `@Enumerated(EnumType.STRING)` en la entidad JPA y agrega
`CHECK (estado IN (...))` en Flyway. Funciona en las tres arquitecturas;
disponible solo vía JSON, no en el DSL de texto.

## Campos y reglas

El formato es `nombre:tipo[:regla]`, con campos separados por comas. Debe
existir un `id` y los nombres deben usar `lower_snake_case`.

| Tipo | Java | PostgreSQL |
| --- | --- | --- |
| `int` | `Integer` | `INT` |
| `string` | `String` | `VARCHAR(255)` (o `VARCHAR(max)` con la regla `max=N`) |
| `text` | `String` | `TEXT` (sin limite; `min=N`/`max=N` se validan con `CHECK char_length`) |
| `float` | `Float` | `DECIMAL(10, 2)` |
| `double` | `Double` | `DECIMAL(19, 4)` |
| `decimal` | `BigDecimal` | `DECIMAL(19, 4)`, o `DECIMAL(precision, scale)` con `precision=N:scale=N` |
| `boolean` | `Boolean` | `BOOLEAN` |
| `datetime` | `LocalDateTime` | `TIMESTAMP` |
| `date` | `LocalDate` | `DATE` |

Para dinero usa siempre `decimal`. `float` y `double` se mantienen para
magnitudes no monetarias y compatibilidad. Usa `text` en vez de `string`
cuando el contenido no tiene un limite de longitud natural (JSON, texto
libre, descripciones largas).

| Regla | Tipos | Java y Flyway |
| --- | --- | --- |
| `required` | Todos | `@NotNull` y `NOT NULL` |
| `not_blank` | `string`, `text` | `@NotBlank`, `NOT NULL` y `CHECK` |
| `positive` | Numericos | `@Positive` y `CHECK (> 0)` |
| `min=N` | String, text y numericos | `@Size`/`@DecimalMin` y `CHECK` |
| `max=N` | String, text y numericos | `@Size`/`@DecimalMax`, longitud SQL y `CHECK` |
| `unique` | Todos | Restriccion `UNIQUE` |
| `index` | Todos | Indice PostgreSQL |
| `default=valor` | Todos salvo `id` y campos de auditoria | Inicializador Java, `DEFAULT` en Flyway y `@DynamicInsert` |
| `composite_unique=grupo` | Todos | `UNIQUE` combinada entre los campos que comparten `grupo` |
| `precision=N:scale=N` | Solo `decimal` | `DECIMAL(N, N)` en Flyway (ambas reglas son obligatorias juntas) |

Un campo `unique` ya tiene el indice implicito de PostgreSQL, por lo que el
generador no crea un segundo indice aunque se indiquen ambas reglas.
`CreateDTO` y `UpdateDTO` aplican las reglas obligatorias. `PatchDTO` permite
omitir campos, pero valida los valores presentes. Los campos `creado_en`,
`created_at`, `actualizado_en` y `updated_at` se gestionan internamente.

Como `:` separa `nombre:tipo:regla` y `,` separa atributos, ningun valor de
regla (`default=...`, `composite_unique=...`) puede contener `:` ni `,`. Para
`default` en un campo `datetime` se omiten los `:` de la hora:
`campo:datetime:default=2026-01-31T153000` (equivale a las 15:30:00); si se
omite la hora se asume medianoche.

### Claves compuestas

`refitid:string:not_blank:composite_unique=documento,
refitidctrl:string:not_blank:composite_unique=documento` genera una unica
restriccion `UNIQUE (refitid, refitidctrl)` (Flyway y
`@Table(uniqueConstraints = ...)`), no una `UNIQUE` por columna. El
generador exige un `id` autonumerico ademas de estos campos, ya que JPA
siempre necesita una clave primaria simple; los campos del grupo quedan como
restriccion de negocio adicional. Cada grupo necesita al menos dos campos.

### Valores por defecto

`lstusr:string:not_blank:default=usr` inicializa el campo Java, agrega
`DEFAULT 'usr'` en la migracion Flyway y activa `@DynamicInsert` en la
entidad para que Hibernate omita esa columna del `INSERT` cuando el DTO la
recibe en `null`, dejando que PostgreSQL aplique el valor por defecto.

## Ejemplo avanzado

```powershell
python .\generate_crud.py OperacionFinanciera `
  "id:int, referencia:string:not_blank:min=8:max=64:unique, " `
  "descripcion:string:required:max=255:index, " `
  "importe:decimal:required:positive:min=0.01:max=999999.99, " `
  "unidades:int:required:positive:min=1:max=10000, " `
  "tasa:float:positive:max=100, activa:boolean:required, " `
  "fecha_valor:date:required, procesado_en:datetime:required, " `
  "creado_en:datetime, actualizado_en:datetime" `
  --architecture clean

mvn -f .\crud-operacionfinanciera-clean\pom.xml verify
```

## Pruebas Cucumber (BDD) y reporte Allure

Cada entidad recibe `src/test/resources/features/{entidad}.feature` (listar,
alta valida + consulta, alta sin campos obligatorios, consulta inexistente —
en Gherkin en castellano) y su clase de pasos `{Entidad}Steps.java`, que
llaman a la API real por HTTP (RestAssured) contra la app arrancada en un
puerto aleatorio con un Postgres real de Testcontainers, no una base de datos
simulada. Si la entidad tiene un campo `reference`, el escenario de alta
valida se omite (exigiria crear antes la entidad referenciada).

Estos escenarios **no** se ejecutan con `mvn verify`: `RunCucumberTest`
(la clase que Surefire reconoceria por defecto, al terminar en `Test`) esta
excluida explicitamente, porque Testcontainers necesita Docker respondiendo
de verdad, no solo "instalado" — en Windows con Docker Desktop es habitual
que la negociacion de version de API falle sobre el named pipe aunque
`docker` funcione bien por CLI. Ejecutalos aparte, en un entorno con Docker
fiable (Linux, WSL2, CI):

```powershell
mvn test -Pcucumber -Dtest=RunCucumberTest
```

El plugin `allure-cucumber7-jvm` vuelca los resultados en
`target/allure-results/`; genera el HTML navegable con:

```powershell
mvn allure:serve
```

## Documentacion HTML generada

Cada proyecto incluye `docs/index.html`, una documentacion tecnica autonoma y
responsive que se puede abrir directamente en el navegador. El contenido se
calcula en cada ejecucion a partir de la entidad, arquitectura y definicion de
campos utilizada; no es un documento generico copiado sin adaptar.

Incluye el comando reproducible, tabla de tipos y reglas, restricciones de
PostgreSQL, flujo arquitectonico, endpoints, roles, paginacion, idempotencia,
concurrencia optimista, observabilidad, variables de entorno y pruebas. Los
botones permiten copiar los comandos de generacion, ejecucion y verificacion.

Por ejemplo, despues de generar `FondoInversion` con arquitectura hexagonal:

```powershell
Start-Process .\crud-fondoinversion-hexagonal\docs\index.html
```

## Produccion

- Los listados estan paginados: 20 elementos por defecto y 100 como maximo.
  Hexagonal y clean usan `PageQuery` y `PageResult` propios en el dominio.
- El listado admite filtros por igualdad usando cualquier campo de la entidad
  como query param, combinables entre si y con la paginacion:
  `GET /api/productos?nombre=Teclado&activo=true&page=0&size=20`. Se traduce
  a un `Specification` de Spring Data (JPA Criteria) construido en generacion,
  con un `case` por campo que convierte el `String` del query param al tipo
  Java real (`Integer`, `BigDecimal`, `LocalDate`, `LocalDateTime`, `Boolean`,
  `String`); los query params que no coinciden con ningun campo se ignoran.
  Un valor de filtro con formato invalido (`?precio=no-es-un-numero`) responde
  `400` con un mensaje claro en vez de un `500`. Una propiedad de `sort`
  inexistente (`?sort=string`, el placeholder que sugiere Swagger UI por
  defecto) tambien responde `400` en vez de `500`.
- Entidades y modelos incluyen `version`; JPA usa `@Version` para concurrencia
  optimista y Flyway crea la columna correspondiente.
- `POST` exige `Idempotency-Key`. PostgreSQL bloquea concurrentemente la clave
  y guarda el identificador resultante en `idempotency_keys`.
- HTTP Basic permite lectura a `USER` y `ADMIN`, y escritura solo a `ADMIN`.
  La aplicacion es stateless.
- Actuator requiere `ADMIN`, salvo el resumen de `/actuator/health`. Se exponen
  health, info y Prometheus, sin detalles completos para usuarios anonimos.
- Un filtro limita peticiones por minuto e IP.
- Micrometer incluye `traceId` y `spanId` en logs y exporta trazas mediante OTLP.
- No existen usuarios ni contrasenas predeterminados.

Variables minimas para arrancar:

```powershell
$env:SPRING_DATASOURCE_USERNAME = "app_user"
$env:SPRING_DATASOURCE_PASSWORD = "una-clave-segura"
$env:APP_SECURITY_USER = "admin"
$env:APP_SECURITY_PASSWORD = "otra-clave-segura"
$env:RATE_LIMIT_PER_MINUTE = "120"
$env:OTEL_EXPORTER_OTLP_ENDPOINT = "http://localhost:4318/v1/traces"
```

Alta idempotente:

```powershell
curl.exe -u admin:otra-clave-segura `
  -H "Content-Type: application/json" `
  -H "Idempotency-Key: operacion-2026-0001" `
  -d '{"referencia":"REF-00001","importe":10.50}' `
  http://localhost:8080/api/operacionfinancieras
```

`docker-compose.yml` tambien obliga a definir `POSTGRES_USER`,
`POSTGRES_PASSWORD`, `APP_SECURITY_USER` y `APP_SECURITY_PASSWORD` antes de
ejecutar `docker compose up`. Cada proyecto generado incluye un
`.env.example` con esas cuatro variables; cópialo a `.env` (docker compose lo
carga automáticamente) y ajusta los valores:

```powershell
copy .env.example .env
docker compose up -d --build
```

Sin ese fichero `docker compose up` falla con
`required variable POSTGRES_USER is missing a value`. `.env` está en el
`.gitignore` que se genera junto al proyecto, para no versionar credenciales.

Cada proyecto incluye ademas:

- **CI** (`.github/workflows/ci.yml`): ejecuta `mvn verify` (incluye los
  tests de Testcontainers) en cada push/PR contra `main`/`master`, con cache
  de Maven y los reportes de Surefire/Failsafe como artefacto.
- **Observabilidad completa**: junto a `/actuator/prometheus` (ya expuesto),
  `docker-compose.yml` añade `prometheus`, `loki` y `grafana`. La app envía
  cada log a Loki (`logback-spring.xml` + `loki-logback-appender`, label
  `service_name={entidad}-service`) ademas de a consola. Grafana viene
  aprovisionado (`observability/`) con datasources de Prometheus/Loki y un
  dashboard (`{entidad}-overview.json`) con peticiones/seg, tasa de error
  5xx, latencia p95 y logs recientes — abre `http://localhost:3000` con las
  credenciales de `APP_SECURITY_USER`/`APP_SECURITY_PASSWORD`.

### Regenerar un proyecto existente (`--force`)

Por defecto, generar sobre un directorio que ya existe falla (para no pisar
cambios manuales sin avisar):

```powershell
python .\generate_crud.py --json .\fondoinversion.json --force
```

Con `--force`, los ficheros de codigo/config se sobrescriben, pero las
migraciones Flyway **no**: si `V1__Create_Table_*.sql` ya existe, el
generador anade `V{n}__Update_Table_*.sql` solo con las columnas nuevas (no
detecta columnas eliminadas ni cambios de tipo — eso exige revisión manual).
Una columna nueva marcada `required`/`not_blank` sin `default` se crea como
`NULL` en esa migracion incremental (Postgres rechaza `NOT NULL` sin valor en
una tabla con filas) con un aviso en el propio SQL; hay que rellenarla y
forzar `NOT NULL` en una migracion posterior. En un proyecto multi-entidad,
la numeracion de version (`V1`, `V2`, ...) es unica para todo el proyecto
aunque varias entidades compartan `db/migration/`.

## Validacion

El generador falla antes de escribir cuando encuentra nombres invalidos,
atributos duplicados, tipos o reglas desconocidos, reglas incompatibles,
limites incoherentes o ausencia de `id`. Los errores de uso devuelven codigo 1
y las definiciones invalidas codigo 2.

```powershell
python -m pytest -q
```

La aceptacion genera proyectos layered, hexagonal y clean en directorios
temporales y ejecuta `mvn verify` en cada uno. Cada proyecto incluye tests
unitarios y MVC, mas un `@SpringBootTest` con PostgreSQL 16 real que valida
Flyway, seguridad e idempotencia. Testcontainers lo ejecuta cuando Docker esta
disponible y lo omite explicitamente cuando no lo esta. Si Maven no esta
instalado, se omite la aceptacion Java.

La cache Maven de aceptacion se guarda en `.m2/repository` dentro del workspace.
Se puede cambiar con `CRUD_GENERATOR_MAVEN_REPO`.

## Estructura

```text
generate_crud.py          Punto de entrada compatible
crud_generator/
  cli.py                  Interfaz de linea de comandos
  architectures.py        Definicion de layouts
  generator.py            Generacion layered (una o varias entidades)
  ports_generator.py      Generacion hexagonal y clean
  json_schema.py          Carga y validacion cruzada del JSON (single/multi-entidad)
  migrations.py           Migraciones Flyway, incrementales al regenerar
  observability.py        Escritura del stack Prometheus/Loki/Grafana
  documentation.py        Documentacion HTML dinamica
  parsing.py              Analisis y validacion de entradas (incluye enum/reference)
  fields.py               Campos Java, DTO y SQL
  templates.py            Plantillas compartidas y layered
  ports_templates.py      Plantillas de puertos y adaptadores
  types.py                Mapeos de tipos
  writer.py               Escritura en disco
  schema/entity.schema.json  JSON Schema del formato de entrada
tests/                    Pruebas de la automatizacion
examples/                 Ficheros JSON de ejemplo (entidad simple y multi-entidad)
```

Los proyectos generados pueden borrarse y regenerarse en cualquier momento:

```powershell
Get-ChildItem -Directory -Filter "crud-*" | Remove-Item -Recurse -Force
```
