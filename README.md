# crud-automation

Generador en Python de microservicios Spring Boot a partir de una definición de entidad.

El paquete está publicado en PyPI como `crud-automation` y se ejecuta como módulo Python:

```bash
python -m crud_generator
```

> Requiere Python 3.10 o superior.

## Instalación

Desde PyPI:

```bash
python -m pip install --upgrade crud-automation
```

Para instalar una versión concreta:

```bash
python -m pip install crud-automation==0.1.2
```

Comprobar la instalación:

```bash
python -m pip show crud-automation
```

Si tu entorno utiliza un índice privado de paquetes y todavía no ha sincronizado la última versión de PyPI, puedes consultar PyPI directamente:

```bash
python -m pip index versions crud-automation --index-url https://pypi.org/simple
```

E instalar desde PyPI público:

```bash
python -m pip install --upgrade --index-url https://pypi.org/simple crud-automation
```

## Uso rápido

### PowerShell

```powershell
python -m crud_generator Producto `
  "id:int, nombre:string:not_blank:max=120:index, precio:decimal:required:positive"
```

### Linux / macOS

```bash
python -m crud_generator Producto \
  "id:int, nombre:string:not_blank:max=120:index, precio:decimal:required:positive"
```

El generador pedirá la arquitectura cuando sea necesario:

```text
Arquitectura:
  1. layered
  2. hexagonal
  3. clean
  4. minimal
```

También puedes indicarla explícitamente:

```bash
python -m crud_generator Producto \
  "id:int, nombre:string:not_blank:max=120:index, precio:decimal:required:positive" \
  --architecture hexagonal
```

Arquitecturas disponibles:

- `layered`
- `hexagonal`
- `clean`
- `minimal`

## Sintaxis de campos

La definición se escribe como una lista separada por comas:

```text
nombre:tipo:opcion:opcion
```

Ejemplo:

```text
id:int, nombre:string:not_blank:max=120:index, precio:decimal:required:positive
```

Ejemplo de ejecución:

```bash
python -m crud_generator Producto \
  "id:int, nombre:string:not_blank:max=120:index, precio:decimal:required:positive"
```

## Generación desde JSON

Puedes usar una definición JSON en lugar del DSL de línea de comandos:

```bash
python -m crud_generator --json examples/ventas.json
```

Con arquitectura explícita:

```bash
python -m crud_generator --json examples/empleados-clean.json --architecture clean
```

## Kafka Streams

Para generar un proyecto Kafka Streams:

```bash
python -m crud_generator --stream examples/sensores-stream.json
```

## Spring Batch

Para generar un proyecto Spring Batch:

```bash
python -m crud_generator --batch
```

O indicando el directorio de destino:

```bash
python -m crud_generator --batch spring-batch-coches
```

## Wizard interactivo

Para usar el asistente guiado:

```bash
python -m crud_generator --wizard
```

## Opciones útiles

### Sobrescribir un proyecto existente

```bash
python -m crud_generator Producto \
  "id:int, nombre:string" \
  --force
```

### Verificar el proyecto generado

Ejecuta `mvn verify` después de generar:

```bash
python -m crud_generator Producto \
  "id:int, nombre:string" \
  --verify
```

### Publicar el proyecto generado en GitHub

Requiere la CLI `gh` instalada y autenticada:

```bash
python -m crud_generator Producto \
  "id:int, nombre:string" \
  --github
```

Indicando nombre de repositorio:

```bash
python -m crud_generator Producto \
  "id:int, nombre:string" \
  --github mi-microservicio
```

Repositorio privado:

```bash
python -m crud_generator Producto \
  "id:int, nombre:string" \
  --github mi-microservicio \
  --private
```

### Recordar convenciones

Guarda las convenciones utilizadas para ejecuciones posteriores en el mismo directorio:

```bash
python -m crud_generator Producto \
  "id:int, nombre:string" \
  --architecture clean \
  --remember
```

## Ejemplos incluidos

El directorio `examples/` contiene definiciones JSON listas para probar, entre ellas:

- `ventas.json`
- `transferencia.json`
- `empleados-clean.json`
- `categorias-arbol.json`
- `tipos-y-validaciones.json`
- `sensores-stream.json`
- `sales-streams.json`

Ejemplo:

```bash
python -m crud_generator --json examples/ventas.json
```

## Desarrollo local

Clonar el repositorio:

```bash
git clone https://github.com/juanfranciscofernandezherreros/crud-automation.git
cd crud-automation
```

Instalar dependencias de desarrollo:

```bash
python -m pip install -e ".[dev]"
```

Ejecutar tests:

```bash
python -m pytest
```

## Publicación

Las releases se publican en PyPI mediante GitHub Actions y Trusted Publishing.

Proyecto en PyPI:

```text
https://pypi.org/project/crud-automation/
```

Repositorio:

```text
https://github.com/juanfranciscofernandezherreros/crud-automation
```

## Licencia

MIT.
