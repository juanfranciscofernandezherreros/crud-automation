# Reglas del repositorio: crud-automation

## Informe HTML de cada commit

Cuando se cree un commit en este repositorio (siempre que el usuario lo pida
explícitamente — la política global de no commitear/pushear sin permiso
sigue aplicando), justo después añade una entrada nueva al final de
`informes/historial-commits.html` describiendo ese commit, sin modificar las
entradas anteriores. Reusa el formato ya usado en ese fichero:

```html
<div class="commit [fix]">
  <div class="meta"><span class="hash">abc1234</span><span class="date">AAAA-MM-DD</span><span class="tag feat|fix|chore|docs">etiqueta</span></div>
  <h2>Título corto (alineado con el mensaje del commit)</h2>
  <p>Qué cambió y, sobre todo, por qué — el motivo real, no una repetición de la lista de ficheros tocados.</p>
  <div class="stat">N ficheros · <b>+X / -Y</b> líneas</div>
</div>
```

- `hash`: los 7 primeros caracteres del commit real (`git rev-parse --short HEAD` tras commitear).
- `date`: `git show -s --format=%cd --date=short HEAD`.
- `tag`: `feat` (funcionalidad nueva), `fix` (corrección de bug), `chore`
  (tareas internas) o `docs` (documentación). Añade la clase `commit fix` al
  `<div>` contenedor solo si es una corrección de bug real.
- `stat`: sale de `git show --stat HEAD` (ficheros y líneas +/-).
- La entrada va al final de `<main>`, antes del `<div class="callout">` si lo
  hay.
- El commit ya existe cuando se escribe el informe (se necesita su hash
  real), así que el informe se añade en un commit de seguimiento aparte cuyo
  mensaje **debe empezar exactamente por** `docs: informe de` (p. ej.
  `docs: informe del commit <hash>`, `docs: informe de los commits <a> y
  <b>`) — nunca reescribiendo con `--amend` el commit que describe.
- Si el usuario no pide crear un commit, esta regla no se dispara.

Esta regla está verificada, no solo documentada: `.githooks/pre-push`
bloquea el `git push` si algún commit del rango a enviar (que no sea él
mismo un `docs: informe de...`) no tiene su hash en
`informes/historial-commits.html`. Se activa una vez por clon con
`git config core.hooksPath .githooks` (no se aplica solo con tener el
fichero en el repositorio).
