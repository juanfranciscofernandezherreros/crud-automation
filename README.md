# Generador de CRUD Spring Boot

Automatización en Python que genera la estructura completa de un CRUD con
Spring Boot, PostgreSQL, Flyway, MapStruct, Docker y pruebas.

Este repositorio contiene únicamente el generador. Los proyectos `crud-*`
creados al ejecutarlo son artefactos de salida y no forman parte del código
fuente versionado.

## Requisitos

- Python 3.10 o superior.
- No requiere dependencias externas de Python.

## Uso

```powershell
python .\generate_crud.py Producto "id:int, nombre:string, precio:float"
```

El comando crea el proyecto en `crud-producto/`.

La definición de campos usa el formato `nombre:tipo`, separando los campos
con comas. Debe existir exactamente un campo llamado `id` y los nombres de
atributo deben escribirse en `lower_snake_case`.

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

Ejemplo con auditoría:

```powershell
python .\generate_crud.py Pedido "id:int, numero:string, creado_en:datetime, actualizado_en:datetime"
```

## Validación

El generador detiene la ejecución antes de escribir archivos cuando encuentra:

- Una entidad con un nombre no válido.
- Atributos sin el formato `nombre:tipo`.
- Nombres que no siguen `lower_snake_case`.
- Atributos duplicados.
- Tipos desconocidos.
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

Las pruebas validan el análisis de atributos, los errores de entrada, la
normalización de entidades y el comportamiento del CLI sin generar proyectos
reales en el repositorio.

## Salida

Cada ejecución genera un directorio `crud-<entidad>/` con el proyecto Spring
Boot. Estos directorios están excluidos por `.gitignore`; pueden borrarse y
regenerarse en cualquier momento.
