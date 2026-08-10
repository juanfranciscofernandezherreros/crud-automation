# Generador de CRUD Spring Boot

Automatización en Python que genera la estructura completa de un CRUD con
Spring Boot, PostgreSQL, Flyway, MapStruct, Docker y pruebas.

Este repositorio contiene únicamente el generador. Los proyectos `crud-*`
creados al ejecutarlo son artefactos de salida y no forman parte del código
fuente versionado.

## Requisitos

- Python 3.10 o superior.
- No requiere dependencias externas de Python.
- Java 21 y Maven 3.9 para compilar y probar los proyectos generados.

## Uso

```powershell
python .\generate_crud.py Producto "id:int, nombre:string, precio:float"
```

El comando crea el proyecto en `crud-producto/`.

## Arquitectura

Cuando se ejecuta desde una terminal interactiva, el generador pregunta qué
arquitectura debe utilizar:

```text
Arquitectura:
  1. layered
  2. hexagonal
  3. clean
Selecciona una opción [1]:
```

También puede indicarse explícitamente, lo que evita preguntas en scripts y CI:

```powershell
python .\generate_crud.py Producto `
  "id:int, nombre:string:not_blank" `
  --architecture hexagonal
```

| Arquitectura | Organización principal |
| --- | --- |
| `layered` | Controller, service, repository y entity |
| `hexagonal` | Dominio, puertos de entrada/salida y adaptadores |
| `clean` | Entidades, casos de uso, gateways, interface adapters y frameworks |

`layered` conserva el directorio `crud-<entidad>/`. Las otras opciones generan
`crud-<entidad>-hexagonal/` o `crud-<entidad>-clean/` para evitar sobrescribir
proyectos de arquitecturas diferentes.

La definición de campos usa el formato `nombre:tipo`, separando los campos
con comas. Debe existir exactamente un campo llamado `id` y los nombres de
atributo deben escribirse en `lower_snake_case`.

Las validaciones se añaden después del tipo, separadas por `:`:

```powershell
python .\generate_crud.py Producto "id:int, nombre:string:not_blank:max=120, precio:double:required:positive"
```

Tipos admitidos:

| Tipo | Java | PostgreSQL |
| --- | --- | --- |
| `int` | `Integer` | `INT` |
| `string` | `String` | `VARCHAR(255)` |
| `float` | `Float` | `DECIMAL(10, 2)` |
| `double` | `Double` | `DECIMAL(19, 4)` |
| `boolean` | `Boolean` | `BOOLEAN` |
| `datetime` | `LocalDateTime` | `TIMESTAMP` |
| `date` | `LocalDate` | `DATE` |

Validaciones admitidas:

| Regla | Tipos | Anotación generada |
| --- | --- | --- |
| `required` | Todos | `@NotNull` |
| `not_blank` | `string` | `@NotBlank` |
| `positive` | `int`, `float`, `double` | `@Positive` |
| `min=N` | `string` y numéricos | `@Size(min=N)` o `@DecimalMin` |
| `max=N` | `string` y numéricos | `@Size(max=N)` o `@DecimalMax` |

`CreateDTO` y `UpdateDTO` aplican las reglas obligatorias. `PatchDTO` permite
omitir cualquier campo, pero valida los valores que sí se envían. Los campos
de auditoría se gestionan internamente y no aparecen en los DTO de entrada.

Ejemplo con auditoría:

```powershell
python .\generate_crud.py Pedido "id:int, numero:string:not_blank:max=40, creado_en:datetime, actualizado_en:datetime"
```

## Ejemplo avanzado

Este ejemplo combina todos los tipos, reglas obligatorias, límites de texto y
numéricos, fechas de negocio y campos de auditoría:

```powershell
python .\generate_crud.py OperacionFinanciera `
  "id:int, referencia:string:not_blank:min=8:max=64, " `
  "descripcion:string:required:max=255, " `
  "importe:double:required:positive:min=0.01:max=999999.99, " `
  "unidades:int:required:positive:min=1:max=10000, " `
  "tasa:float:positive:max=100, activa:boolean:required, " `
  "fecha_valor:date:required, procesado_en:datetime:required, " `
  "creado_en:datetime, actualizado_en:datetime" `
  --architecture clean

mvn -f .\crud-operacionfinanciera-clean\pom.xml verify
```

El proyecto resultante incluye validaciones distintas para creación,
actualización completa y parche parcial, pruebas HTTP de entradas válidas e
inválidas, migración Flyway, Docker y un JAR ejecutable.

## Validación

El generador detiene la ejecución antes de escribir archivos cuando encuentra:

- Una entidad con un nombre no válido.
- Atributos sin el formato `nombre:tipo`.
- Nombres que no siguen `lower_snake_case`.
- Atributos duplicados.
- Tipos desconocidos.
- Validaciones desconocidas o incompatibles con el tipo.
- Límites no numéricos, negativos para strings o con `min` mayor que `max`.
- Una definición sin el campo `id`.

Los errores de uso devuelven código de salida `1` y las definiciones inválidas
devuelven código `2`.

## Estructura

```text
generate_crud.py          Punto de entrada compatible
crud_generator/
  cli.py                  Interfaz de línea de comandos
  generator.py            Orquestación de la generación
  parsing.py              Análisis y validación de entradas
  fields.py               Construcción de campos Java, DTO y SQL
  templates.py            Plantillas de archivos generados
  types.py                Mapeos de tipos
  writer.py               Escritura en disco
tests/                    Pruebas de la automatización Python
```

## Pruebas

```powershell
python -m unittest discover -s tests -v
```

Las pruebas unitarias validan las entradas y el comportamiento del CLI. La
suite de aceptación genera varios proyectos en directorios temporales y ejecuta
`mvn verify` para comprobar que el código Java compila, sus tests Spring pasan y
el JAR final se construye correctamente. Si Maven no está instalado, esa prueba
se omite.

También puedes comprobar manualmente un proyecto recién generado:

```powershell
mvn -f .\crud-producto\pom.xml verify
```

## Salida

Cada ejecución genera un directorio `crud-<entidad>/` con el proyecto Spring
Boot. Estos directorios están excluidos por `.gitignore`; pueden borrarse y
regenerarse en cualquier momento. El repositorio conserva únicamente el
generador Python, sus pruebas y la documentación.

Para eliminar todos los proyectos generados localmente:

```powershell
Get-ChildItem -Directory -Filter "crud-*" | Remove-Item -Recurse -Force
```

La prueba de aceptación realiza esta limpieza automáticamente porque genera
los proyectos en un directorio temporal.
