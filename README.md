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

## Campos y reglas

El formato es `nombre:tipo[:regla]`, con campos separados por comas. Debe
existir un `id` y los nombres deben usar `lower_snake_case`.

| Tipo | Java | PostgreSQL |
| --- | --- | --- |
| `int` | `Integer` | `INT` |
| `string` | `String` | `VARCHAR(255)` |
| `float` | `Float` | `DECIMAL(10, 2)` |
| `double` | `Double` | `DECIMAL(19, 4)` |
| `decimal` | `BigDecimal` | `DECIMAL(19, 4)` |
| `boolean` | `Boolean` | `BOOLEAN` |
| `datetime` | `LocalDateTime` | `TIMESTAMP` |
| `date` | `LocalDate` | `DATE` |

Para dinero usa siempre `decimal`. `float` y `double` se mantienen para
magnitudes no monetarias y compatibilidad.

| Regla | Tipos | Java y Flyway |
| --- | --- | --- |
| `required` | Todos | `@NotNull` y `NOT NULL` |
| `not_blank` | `string` | `@NotBlank`, `NOT NULL` y `CHECK` |
| `positive` | Numericos | `@Positive` y `CHECK (> 0)` |
| `min=N` | String y numericos | `@Size`/`@DecimalMin` y `CHECK` |
| `max=N` | String y numericos | `@Size`/`@DecimalMax`, longitud SQL y `CHECK` |
| `unique` | Todos | Restriccion `UNIQUE` |
| `index` | Todos | Indice PostgreSQL |

Un campo `unique` ya tiene el indice implicito de PostgreSQL, por lo que el
generador no crea un segundo indice aunque se indiquen ambas reglas.
`CreateDTO` y `UpdateDTO` aplican las reglas obligatorias. `PatchDTO` permite
omitir campos, pero valida los valores presentes. Los campos `creado_en`,
`created_at`, `actualizado_en` y `updated_at` se gestionan internamente.

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
