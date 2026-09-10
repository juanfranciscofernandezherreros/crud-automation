# crud-automation

Generador en Python de microservicios Spring Boot.

Requiere Python 3.10 o superior.

## Instalación

```bash
python -m pip install --upgrade crud-automation
```

Comprobar versión instalada:

```bash
python -m pip show crud-automation
```

## Ejecución mínima

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

El generador pedirá la arquitectura:

```text
1. layered
2. hexagonal
3. clean
4. minimal
```

También puedes indicarla directamente:

```bash
python -m crud_generator Producto "id:int, nombre:string" --architecture layered
```

## Otros modos

Desde JSON:

```bash
python -m crud_generator --json examples/ventas.json
```

Wizard interactivo:

```bash
python -m crud_generator --wizard
```

Forzar regeneración:

```bash
python -m crud_generator Producto "id:int, nombre:string" --force
```

## PyPI

https://pypi.org/project/crud-automation/

## Licencia

MIT
