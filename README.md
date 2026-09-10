# crud-automation

Generador en Python de microservicios Spring Boot.

Requiere Python 3.10 o superior.

## Instalación

```bash
python -m pip install --upgrade crud-automation
```

## Ejecución

### CRUD layered

```powershell
python -m crud_generator Producto `
  "id:int, nombre:string:not_blank:max=120:index, precio:decimal:required:positive" `
  --architecture layered
```

### CRUD hexagonal

```powershell
python -m crud_generator Producto `
  "id:int, nombre:string:not_blank:max=120:index, precio:decimal:required:positive" `
  --architecture hexagonal
```

### CRUD clean

```powershell
python -m crud_generator Producto `
  "id:int, nombre:string:not_blank:max=120:index, precio:decimal:required:positive" `
  --architecture clean
```

## Modo mínimo

`minimal` no genera un CRUD. Crea un esqueleto Spring Boot + Docker sin base de datos, seguridad ni observabilidad.

```powershell
python -m crud_generator Producto --architecture minimal
```

Si no indicas `--architecture`, el generador muestra un selector interactivo.

## Licencia

MIT
