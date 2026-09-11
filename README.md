# crud-automation

Generador en Python de microservicios Spring Boot.

Requiere Python 3.10 o superior.

## Instalación

```powershell
python -m pip install --upgrade crud-automation
```

# Arquitectura mínima: Hola Mundo completo

La arquitectura `minimal` está pensada para crear un microservicio Spring Boot muy pequeño y listo para arrancar, probar, contenerizar y publicar en GitHub.

No genera CRUD, base de datos ni seguridad. Genera:

- Spring Boot 3.2.4.
- Java 21.
- Spring Web.
- Actuator.
- Un `SpringBootApplication` con `main`.
- Un endpoint REST de prueba.
- Test de integración.
- Dockerfile.
- `pom.xml` Maven.

## 1. Requisitos

Instala previamente:

- Python 3.10 o superior.
- Java 21.
- Maven.
- Git.
- GitHub CLI (`gh`).

Comprueba las herramientas:

```powershell
python --version
java -version
mvn -version
git --version
gh --version
```

Para poder crear el primer commit, Git debe tener configurado nombre y correo:

```powershell
git config --global user.name "TU NOMBRE"
git config --global user.email "TU_EMAIL@EJEMPLO.COM"
```

## 2. Crear un Personal Access Token de GitHub

No escribas nunca el token dentro del código, del README, de un fichero versionado ni de la URL del repositorio.

Para este flujo puedes usar un Personal Access Token y exponerlo temporalmente mediante la variable `GH_TOKEN`. GitHub CLI utiliza automáticamente esa variable para autenticarse.

Para un PAT clásico, usa permisos suficientes para crear y administrar el repositorio. Si vas a crear repositorios privados, el scope `repo` es la opción directa para este flujo.

En PowerShell:

```powershell
$env:GH_TOKEN = "ghp_REEMPLAZA_ESTO_POR_TU_TOKEN"
```

Comprueba la autenticación:

```powershell
gh auth status
```

La variable anterior existe solamente en esa sesión de PowerShell. No la añadas al proyecto ni la subas a Git.

También puedes autenticar `gh` de forma persistente leyendo un PAT clásico desde la entrada estándar:

```powershell
Get-Content .\token.txt | gh auth login --with-token
```

Si utilizas este método, borra después `token.txt` y nunca lo añadas al repositorio.

## 3. Generar el Hola Mundo mínimo

Ejecuta:

```powershell
python -m crud_generator HolaMundo --architecture minimal
```

Se genera:

```text
crud-holamundo-minimal/
├── README.md
└── app/
    ├── pom.xml
    ├── Dockerfile
    ├── .dockerignore
    └── src/
        ├── main/
        │   ├── java/com/example/crud/
        │   │   ├── HolaMundoApplication.java
        │   │   └── HolaMundoController.java
        │   └── resources/application.yml
        └── test/java/com/example/crud/
            └── HolaMundoControllerTest.java
```

El `main` de Spring Boot queda en:

```text
crud-holamundo-minimal/app/src/main/java/com/example/crud/HolaMundoApplication.java
```

## 4. Ejecutar los tests

Desde el directorio donde ejecutaste el generador:

```powershell
mvn -f .\crud-holamundo-minimal\app\pom.xml test
```

O entrando en la aplicación:

```powershell
cd .\crud-holamundo-minimal\app
mvn test
```

## 5. Arrancar Spring Boot

Desde la raíz generada:

```powershell
mvn -f .\crud-holamundo-minimal\app\pom.xml spring-boot:run
```

O:

```powershell
cd .\crud-holamundo-minimal\app
mvn spring-boot:run
```

También puedes abrir el proyecto en IntelliJ IDEA, Eclipse o VS Code y ejecutar directamente:

```text
HolaMundoApplication.main()
```

La aplicación arranca en el puerto `8080`.

Prueba el endpoint:

```powershell
curl.exe http://localhost:8080/holamundo
```

Respuesta esperada:

```json
{"message":"Hello from HolaMundo"}
```

Actuator también queda disponible:

```powershell
curl.exe http://localhost:8080/actuator/health
```

## 6. Crear el repositorio GitHub automáticamente con el access token

Con `GH_TOKEN` configurado, `crud-automation` puede hacer todo el proceso automáticamente.

Ejemplo creando un repositorio público llamado `hola-mundo-springboot`:

```powershell
$env:GH_TOKEN = "ghp_REEMPLAZA_ESTO_POR_TU_TOKEN"

python -m crud_generator HolaMundo `
  --architecture minimal `
  --github hola-mundo-springboot
```

El generador hace automáticamente:

1. Genera `crud-holamundo-minimal/`.
2. Ejecuta `git init -b main` si todavía no existe `.git`.
3. Ejecuta `git add -A`.
4. Crea el commit inicial.
5. Ejecuta `gh repo create`.
6. Crea el remoto `origin`.
7. Hace `push` de `main` a GitHub.
8. Configura el repositorio para que GitHub Actions pueda tener permisos de escritura.
9. Devuelve la URL del repositorio creado.

Para crear el repositorio privado:

```powershell
python -m crud_generator HolaMundo `
  --architecture minimal `
  --github hola-mundo-springboot `
  --private
```

Comprueba después el remoto:

```powershell
cd .\crud-holamundo-minimal
git remote -v
```

Y abre el repositorio:

```powershell
gh repo view hola-mundo-springboot --web
```

## 7. Flujo completo recomendado

En una terminal PowerShell nueva:

```powershell
# Token solo para esta sesión
$env:GH_TOKEN = "ghp_REEMPLAZA_ESTO_POR_TU_TOKEN"

# Comprobar autenticación
gh auth status

# Generar el proyecto
python -m crud_generator HolaMundo --architecture minimal

# Ejecutar tests
mvn -f .\crud-holamundo-minimal\app\pom.xml test

# Arrancar Spring Boot
mvn -f .\crud-holamundo-minimal\app\pom.xml spring-boot:run
```

En otra terminal puedes comprobar el endpoint:

```powershell
curl.exe http://localhost:8080/holamundo
```

Cuando hayas parado Spring Boot con `Ctrl+C`, puedes publicar el proyecto generado utilizando el mismo token:

```powershell
cd .\crud-holamundo-minimal

git init -b main
git add -A
git commit -m "Initial commit"

gh repo create hola-mundo-springboot `
  --public `
  --source . `
  --remote origin `
  --push
```

O puedes hacer generación + creación del repositorio + primer push directamente en un único comando:

```powershell
python -m crud_generator HolaMundo `
  --architecture minimal `
  --github hola-mundo-springboot
```

## 8. Docker

Construye la imagen:

```powershell
docker build -t hola-mundo:local .\crud-holamundo-minimal\app
```

Arráncala:

```powershell
docker run --rm -p 8080:8080 hola-mundo:local
```

Comprueba:

```powershell
curl.exe http://localhost:8080/holamundo
```

# Otras arquitecturas

## CRUD layered

```powershell
python -m crud_generator Producto `
  "id:int, nombre:string:not_blank:max=120:index, precio:decimal:required:positive" `
  --architecture layered
```

## CRUD hexagonal

```powershell
python -m crud_generator Producto `
  "id:int, nombre:string:not_blank:max=120:index, precio:decimal:required:positive" `
  --architecture hexagonal
```

## CRUD clean

```powershell
python -m crud_generator Producto `
  "id:int, nombre:string:not_blank:max=120:index, precio:decimal:required:positive" `
  --architecture clean
```

Si no indicas `--architecture`, el generador muestra un selector interactivo cuando se ejecuta desde una terminal interactiva.

# Seguridad del token

- Nunca hagas `git add` de un fichero que contenga el PAT.
- Nunca pongas el PAT directamente en una URL Git.
- No pegues el token en el código fuente.
- Prefiere `GH_TOKEN` para automatización con GitHub CLI.
- Revoca inmediatamente un token que haya sido expuesto accidentalmente.

Para borrar el token de la sesión actual de PowerShell:

```powershell
Remove-Item Env:GH_TOKEN
```

## Licencia

MIT
