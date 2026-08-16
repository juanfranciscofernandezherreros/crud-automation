# Generador de CRUD Spring Boot

Automatizacion en Python que genera un CRUD con Spring Boot, PostgreSQL,
Flyway, MapStruct, Docker, seguridad, observabilidad y pruebas reales con
Testcontainers. El repositorio conserva solo el generador; `crud-*` son salidas
recreables y estan excluidas de Git.

## Requisitos

- Python 3.10 o superior. El generador en sí (`generate_crud.py`) no tiene
  dependencias externas; para desarrollarlo y correr su suite de tests hace
  falta `pip install -r requirements-dev.txt` (pytest + jsonschema).
- Java 21 y Maven 3.9 para compilar los proyectos generados.
- Docker para ejecutar las pruebas PostgreSQL de Testcontainers.
- Opcional pero recomendado: `git config core.hooksPath .githooks` una vez
  por clon, para activar el hook `pre-push` que exige informe en
  `informes/historial-commits.html` por cada commit (regla en `CLAUDE.md`).
- Opcional, solo para `--github`/`createRepo.py`: [GitHub CLI](https://cli.github.com/)
  instalada y autenticada (`gh auth login`).

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

## Asistente guiado (`--wizard`)

En vez de construir los flags/JSON a mano, `--wizard` hace las preguntas una
por una en una terminal interactiva y genera al final:

```powershell
python .\generate_crud.py --wizard
```

Pregunta, en orden: entidad, campos (mismo formato `nombre:tipo:regla` del
DSL de texto, reintentando si hay un error de validación), arquitectura,
subconjunto de endpoints, si hace falta algún endpoint personalizado
(`custom_endpoints`, con sus campos de request/response), paquete base, si
sobrescribir un directorio ya existente, y al final si ejecutar
`--verify`, publicar con `--github` (nombre de repo y público/privado) y
guardar la respuesta de arquitectura/paquete/endpoints con `--remember`.
Antes de esas últimas preguntas, informa de la infraestructura que las
plantillas ya traen fija (PostgreSQL, GitHub Actions, HTTP Basic + roles,
Prometheus/Loki/Grafana) — no es configurable desde el asistente, pero
conviene saberlo antes de generar si no encaja con tu stack real.

Necesita una terminal interactiva; en scripts o CI usa los flags normales
(`--json`/`--architecture`/...).

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

`examples/tipos-y-validaciones.json` reune en una sola entidad los nueve
tipos de campo (`int`, `string`, `text`, `float`, `double`, `decimal`,
`boolean`, `date`, `datetime`) y las reglas mas comunes a la vez —
`composite_unique` con dos campos, `default`, `precision`/`scale` — el
mismo combo que motivo `informes/hallazgos-generador.html`.
`examples/empleados-clean.json` es el mismo formato de una sola entidad
pero en arquitectura `clean`.

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
(relaciones reflexivas, p.ej. un arbol de categorias vía `padre` — ver
`examples/categorias-arbol.json`). Las dependencias circulares entre dos
entidades distintas (A referencia a B y B a A) no estan soportadas y el
generador lo rechaza explicitamente. El directorio del proyecto usa
`project` si se indica, o el nombre de la primera entidad listada.

El lado "uno" de la relación (`Cliente`, al que apunta `Pedido.cliente`)
recibe automáticamente:

- `@OneToMany(mappedBy = "cliente", fetch = FetchType.LAZY) private List<Pedido> pedidos;`
  en su entidad JPA (`ClienteJpaEntity` en hexagonal/clean, apuntando a
  `PedidoJpaEntity`), para que el grafo de persistencia sea correcto y
  navegable. No se expone en el dominio ni en los DTOs de `Cliente` — el
  dominio no puede poblarlo sin acceso a un repositorio, e incrustar la
  colección en la respuesta arriesga *N+1* y payloads sin límite.
- Un filtro nuevo en `GET /api/pedidos?clienteId=<id>` (mismo mecanismo
  genérico ya existente para cualquier campo), que compara contra el `id`
  de la asociación JPA sin necesidad de un `join` explícito. Esta es la vía
  soportada para consultar "los pedidos de un cliente".

Solo se genera `@ManyToOne`/`@OneToMany` (uno-a-muchos); no hay
`@ManyToMany`.

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

### Endpoints personalizados (`custom_endpoints`)

El CRUD generado se limita a seis verbos fijos (`list`/`get`/`create`/`update`/
`patch`/`delete`). Para un endpoint de negocio propio —algo que no encaja en
ese molde, como "finalizar un partido" o "reasignar una tarea"— declara su
forma en `custom_endpoints` y el generador scaffolds el DTO, el controller y
un stub de servicio; la lógica de negocio la escribes tú, porque el generador
no puede inventarla:

```json
{
  "entity": "Tarea",
  "fields": [...],
  "custom_endpoints": [
    {
      "name": "completar",
      "method": "POST",
      "path": "/{id}/completar",
      "response": [
        {"name": "completada", "type": "boolean"},
        {"name": "completada_en", "type": "datetime"}
      ]
    },
    {
      "name": "reasignar",
      "method": "PATCH",
      "path": "/{id}/reasignar",
      "request": [{"name": "nuevo_responsable", "type": "string"}],
      "response": [{"name": "responsable_actual", "type": "string"}]
    }
  ]
}
```

- `name`: lower_snake_case, nombra el método Java (`camelCase`) y las clases
  DTO (`PascalCase`).
- `method`: `GET`/`POST`/`PUT`/`PATCH`/`DELETE`.
- `path`: empieza por `/`, se añade tras `/api/{entity}s`. El único path
  variable soportado es el segmento literal `{id}` (`@PathVariable Integer id`,
  igual que `get`/`update`/`patch`/`delete`).
- `request`/`response`: listas opcionales de `{"name", "type"}` — mismo
  vocabulario de tipos que los campos de entidad, pero **sin reglas de
  validación** (no `required`/`unique`/etc.). Sin `request` no hay
  `@RequestBody`; sin `response` el endpoint devuelve `ResponseEntity<Void>`
  (204 al completar).

Lo que genera cada endpoint: `{Entity}{Nombre}RequestDTO`/`ResponseDTO` (solo
las que tengan campos), un método en el controller, la firma correspondiente
en el `Service` (layered) / `UseCase` (hexagonal, clean), y una implementación
que lanza `UnsupportedOperationException` — que un `@ExceptionHandler` global
traduce a `501 Not Implemented` con el mensaje de la excepción. El proyecto
generado compila y arranca tal cual; sustituye ese `throw` por la lógica real
cuando la tengas.

Fuera de alcance a propósito: sin reglas de validación en los campos de
`request`/`response`, sin path variables más allá de `{id}`, y sin tests
autogenerados para estos endpoints (Cucumber/`ControllerTest` solo cubren el
CRUD fijo) — verifícalos a mano, igual que el resto de tu lógica de negocio.
Disponible solo vía JSON (single-entity o por entidad dentro de `entities`),
no en el DSL de texto. `examples/tareas-endpoint-personalizado.json` es el
ejemplo de arriba, verificado con `mvn verify` en `hexagonal` y compilación en
`layered`/`clean`.

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

## Generacion de proyectos Kafka Streams (`--stream`)

Ademas de proyectos CRUD, el generador puede crear un microservicio Spring
Boot + Spring Kafka + Kafka Streams a partir de una definicion JSON:

```powershell
python .\generate_crud.py --stream .\examples\sales-streams.json
```

No es un DSL general para topologias arbitrarias: generaliza un patron
concreto y ya probado — filtrar un topic de entrada por un umbral numerico
opcional, reagrupar por una clave, sumar con estado (KTable en RocksDB) y
unir el stream original con esa tabla para producir un evento enriquecido
con el total acumulado. Windowing, branch, joins entre streams o multiples
agregaciones quedan fuera de este patron.

```json
{
  "project": "sales-streams",
  "package": "com.example.sales",
  "input": {
    "topic": "orders-topic1",
    "event": "Order",
    "fields": [
      {"name": "order_id", "type": "string"},
      {"name": "customer_id", "type": "string"},
      {"name": "amount", "type": "double"}
    ]
  },
  "output": {"topic": "total-sales-topic1", "event": "OrderWithTotal"},
  "processing": {
    "group_by_field": "customer_id",
    "aggregate_field": "amount",
    "aggregate_as": "total_amount",
    "filter_field": "amount",
    "filter_operator": ">",
    "filter_value": 10
  }
}
```

Reglas:

- `project` y `package` siguen las mismas convenciones que en la definicion
  CRUD (`project` en minusculas/guiones, `package` en minusculas separadas
  por puntos).
- `input.fields`/`processing.group_by_field` describen el evento de entrada;
  `processing.group_by_field` debe ser `string` (se usa como clave de Kafka
  tras reagrupar, con `"UNKNOWN"` si el valor es null).
- `processing.aggregate_field` debe ser `double` (tipo del acumulador y del
  Serde del store en esta primera version).
- `processing.filter_field`/`filter_operator`/`filter_value` son opcionales
  (juntos, o ninguno): sin ellos no se filtra nada antes de agregar.
  `filter_operator` acepta `>`, `>=`, `<`, `<=`, `==`, `!=`.
- `output.event` debe ser distinto de `input.event`; el modelo de salida se
  genera con todos los campos de entrada mas el campo agregado
  (`processing.aggregate_as`).

`examples/sales-streams.json` es el ejemplo de arriba (agregación + filtro).
`examples/sensores-stream.json` es el mismo patrón de agregación pero sin
`filter_field`/`filter_operator`/`filter_value` — el caso que obligó a que
la topología descarte tombstones siempre, no solo cuando hay filtro
configurado (ver `informes/historial-commits.html`).

El proyecto generado (`crud-<project>/`) incluye `pom.xml`, `Dockerfile`,
`docker-compose.yml` (con un broker Kafka de un solo nodo), la topologia
(`@Configuration` con el `KStream` cableado) y un test de topologia con
`TopologyTestDriver` que cubre agregacion, claves independientes por
grupo, clave `UNKNOWN`, tombstones y (si hay filtro) el caso filtrado.
`--force` regenera el directorio igual que en el modo CRUD. Los tombstones
(valor `null`, p.ej. un borrado logico en el topic origen) siempre se
descartan antes de tocar ningun campo, con o sin filtro configurado.

### Sin agregacion: passthrough de un topic a otro

`processing` es opcional en su totalidad. Sin ella (o sin
`group_by_field`/`aggregate_field`/`aggregate_as`, que van juntos o
ninguno), el stream generado no agrega nada: lee el topic de entrada y
reescribe cada evento, campo a campo y sin cambios, en el topic de salida
— sin estado, sin KTable, sin join. `filter_field`/`filter_operator`/
`filter_value` siguen siendo independientes y se pueden combinar igual con
o sin agregacion.

```json
{
  "project": "crypto-relay",
  "package": "com.example.crypto",
  "input": {
    "topic": "crypto-prices-in",
    "event": "CryptoPrice",
    "fields": [
      {"name": "symbol", "type": "string"},
      {"name": "price_usd", "type": "double"},
      {"name": "volume", "type": "double"}
    ]
  },
  "output": {"topic": "crypto-prices-out", "event": "CryptoPriceRelayed"}
}
```

Este ejemplo es `examples/crypto-relay.json`, probado con Docker real
enviando 50 eventos de criptomonedas a `crypto-prices-in` (ver
`informes/historial-commits.html`).

## Generacion de un microservicio Spring Batch (`--batch`)

Ademas de CRUD y Kafka Streams, el generador puede crear un microservicio
Spring Batch minimo y autocontenido (`spring-batch-coches`): un job con un
unico step de chunk que consulta la tabla `coches` (H2 en memoria, sembrada
con datos de muestra vía `schema.sql`/`data.sql`), normaliza la matricula a
mayusculas y escribe el resultado en `output/coches.csv`.

```powershell
python .\generate_crud.py --batch
python .\generate_crud.py --batch .\mi-directorio --force
```

A diferencia de `--json`/`--stream`, `--batch` no toma una definicion: es
una plantilla de arranque (build Maven, job Spring Batch con reader JDBC +
processor + writer CSV, Docker, CI, tests, README) pensada para sustituir
la consulta, el modelo `Coche` y el writer por tu propio dominio cuando el
job tenga que procesar datos reales. El directorio destino es opcional (por
defecto `spring-batch-coches`, relativo al directorio actual); `--force`
sobrescribe un directorio ya existente, igual que en los demas modos.

## Verificación automática (`--verify`)

Cualquier modo de generación acepta `--verify` para ejecutar `mvn verify`
sobre el proyecto justo después de generarlo, y reportar el resultado:

```powershell
python .\generate_crud.py Producto "id:int, nombre:string" --verify
```

```text
Proyecto crud-producto generado con éxito, incluyendo todas las capas, tests y docs/index.html.
Verificación OK (mvn verify): 12 tests, 0 fallos, 0 errores, 3 omitidos.
```

Si Maven no está instalado, se omite con un aviso (no es un error). Si la
build falla, el código de salida es **3** (distinto del 2 de una definición
inválida) y se imprime, en `stderr`: una pista si el fallo coincide con un
patrón ya conocido (por ejemplo, "sin Docker no corren los tests de
Testcontainers, eso es esperado"), y si no, las últimas líneas del log de
Maven. `--verify` **no** modifica el código generado — diagnostica, no
corrige; una build rota es una señal para revisar la definición o la
plantilla, no algo que el generador deba parchear a ciegas.

Combinado con `--github`, la verificación va primero: si falla, no se
publica nada.

```powershell
python .\generate_crud.py --json fondoinversion.json --verify --github
```

## Convenciones recordadas (`--remember`)

En modo DSL de texto, la arquitectura, el paquete base y el subconjunto de
endpoints se pueden fijar una vez y reutilizar en cada generación posterior
dentro del mismo directorio, en vez de repetirlos cada vez:

```powershell
python .\generate_crud.py Producto "id:int, nombre:string" --architecture hexagonal --remember
```

Escribe `crud-automation.conventions.json` en el directorio actual:

```json
{ "architecture": "hexagonal" }
```

La siguiente generación **en modo DSL de texto**, en ese mismo directorio,
ya usa `hexagonal` por defecto sin necesidad de `--architecture`; un
`--architecture` explícito en esa ejecución sigue ganando. `--json` no lee
este fichero: ya tiene una fuente de verdad más específica para
`architecture`/`package`/`endpoints`, el propio fichero JSON, y dejar que
una convención antigua se colara con la misma prioridad que `--architecture`
en CLI pisaría un `"architecture"` puesto a propósito en un JSON concreto.
`--stream`/`--batch` tampoco lo usan — no tienen concepto de arquitectura.

`--remember` **nunca** guarda `--verify` ni `--github`: son acciones reales
(ejecutar una build, publicar un repositorio) y deben pedirse explícitamente
en cada ejecución, no activarse solas porque un fichero antiguo lo decía.

## Publicar en GitHub (`--github`)

Cualquier modo de generación (DSL de texto, `--json`, `--stream`, `--batch`)
acepta `--github [nombre_repo]` para, justo después de generar el proyecto,
subirlo como repositorio nuevo en GitHub:

```powershell
python .\generate_crud.py Producto "id:int, nombre:string" --github
python .\generate_crud.py --batch --github spring-batch-coches-demo --private
```

No usa un token pegado en ningún fichero: se apoya en la CLI `gh`, que el
usuario autentica una vez con `gh auth login`. Si el directorio generado no
es aún un repositorio Git, `--github` lo inicializa y crea el primer commit;
si ya lo es (por ejemplo, tras regenerar con `--force`), sube los cambios
pendientes tal cual. `nombre_repo` es opcional (por defecto, el nombre del
directorio generado); `--private` crea el repositorio privado en vez de
público.

Para publicar un proyecto generado en una ejecución anterior (sin
regenerarlo), usa `createRepo.py` directamente:

```powershell
python .\createRepo.py .\crud-producto
python .\createRepo.py .\spring-batch-coches mi-repo --private
```

`createRepo.py` es un wrapper fino sobre `crud_generator/github_repo.py` —
el mismo módulo que usa `--github` — así que ambos caminos crean el repo de
la misma forma.

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
pip install -r requirements-dev.txt
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

`.github/workflows/ci.yml` ejecuta esta misma suite (`python -m pytest -q`) en
cada push/PR a `master`, con Python, JDK 21 y Docker ya disponibles en el
runner de GitHub Actions: el generador se prueba a si mismo en CI igual que
la plantilla de CI que produce para cada proyecto generado.

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
  stream_schema.py        Carga y validacion del JSON de --stream
  stream_generator.py     Orquestacion de la generacion del proyecto Kafka Streams
  stream_templates.py     Plantillas del proyecto Kafka Streams
  generate_service.py     Genera el microservicio Spring Batch coches -> CSV (--batch)
  github_repo.py          Publica un proyecto generado en GitHub via 'gh' (--github)
  verification.py         Ejecuta y diagnostica 'mvn verify' tras generar (--verify)
  conventions.py          Memoria local de arquitectura/paquete/endpoints (--remember)
  wizard.py               Asistente interactivo guiado por preguntas (--wizard)
  schema/entity.schema.json  JSON Schema del formato de entrada
createRepo.py              Wrapper CLI generico de github_repo.py (uso standalone)
tests/                    Pruebas de la automatizacion
examples/                 Ficheros JSON de ejemplo, uno por funcionalidad:
  fondoinversion.json       entidad simple, hexagonal, endpoints parciales
  transferencia.json        entidad simple, hexagonal, text/boolean/decimal
  tipos-y-validaciones.json entidad simple, layered, los 9 tipos + composite_unique
  empleados-clean.json      entidad simple, arquitectura clean
  ventas.json                multi-entidad, reference + enum, layered
  categorias-arbol.json      multi-entidad, reference reflexiva (arbol)
  tareas-endpoint-personalizado.json  entidad simple, hexagonal, custom_endpoints
  sales-streams.json         --stream, agregacion + filtro
  sensores-stream.json       --stream, agregacion sin filtro
  crypto-relay.json          --stream, passthrough (sin agregacion)
```

Los proyectos generados pueden borrarse y regenerarse en cualquier momento:

```powershell
Get-ChildItem -Directory -Filter "crud-*" | Remove-Item -Recurse -Force
```
