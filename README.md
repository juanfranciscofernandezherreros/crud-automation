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
ejecutar `docker compose up`.

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
  generator.py            Generacion layered
  ports_generator.py      Generacion hexagonal y clean
  documentation.py        Documentacion HTML dinamica
  parsing.py              Analisis y validacion de entradas
  fields.py               Campos Java, DTO y SQL
  templates.py            Plantillas compartidas y layered
  ports_templates.py      Plantillas de puertos y adaptadores
  types.py                Mapeos de tipos
  writer.py               Escritura en disco
tests/                    Pruebas de la automatizacion
```

Los proyectos generados pueden borrarse y regenerarse en cualquier momento:

```powershell
Get-ChildItem -Directory -Filter "crud-*" | Remove-Item -Recurse -Force
```
