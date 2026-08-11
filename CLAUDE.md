# Reglas del repositorio: crud-automation

## Límite de 255 parámetros de constructor (JVM)

**Error encontrado:** al generar una entidad con muchos campos (se disparó con
una entidad real de 273 campos, un esquema de reporting tipo EMIR/SFTR),
`@AllArgsConstructor` + `@Builder` de Lombok producen un constructor con un
parámetro por campo. Contando `id` y `version`, eso dio 275 parámetros. La
JVM (JVMS §4.11) limita cualquier método o constructor a 255 parámetros,
contando la referencia implícita al objeto (`this`). La compilación falla
con `too many parameters` antes de ejecutar nada. Ningún caso de prueba
anterior lo había disparado porque las entidades de ejemplo del repositorio
tenían entre 3 y 10 campos.

**Mejora aplicada:** `crud_generator/fields.py` expone
`exceeds_constructor_param_limit(attrs)` (umbral 254, dejando margen para
`id` + `version`). `generator.py` y `ports_generator.py` la consultan antes
de renderizar la entidad; si se supera, `templates.py` y
`ports_templates.py` (`get_entity`, `get_domain`, `get_persistence_entity`)
omiten `@AllArgsConstructor` y `@Builder`, dejando `@NoArgsConstructor` +
`@Getter`/`@Setter` — suficiente para JPA y para que MapStruct mapee
DTO→entidad por setters cuando no hay builder disponible. Cubierto por
`tests/test_templates.py`. Detalle completo en
[`informes/hallazgos-generador.html`](informes/hallazgos-generador.html).

**Regla para este repositorio:** cualquier cambio en `templates.py` o
`ports_templates.py` que añada una anotación Lombok que genere un
constructor con todos los campos (`@AllArgsConstructor`, `@Builder`,
`@Value`, `@RequiredArgsConstructor` sobre campos no-final marcados
manualmente, etc.) debe pasar por `exceeds_constructor_param_limit(attrs)`
igual que las plantillas de entidad actuales, y verificarse generando y
compilando (`mvn -DskipTests compile`) un proyecto con más de 254 campos
antes de darse por válido — no basta con probarlo contra una entidad de
ejemplo pequeña. Este generador se usa contra esquemas reales que pueden
tener cientos de columnas; el conjunto de pruebas de aceptación
(`tests/test_generated_projects.py`) debe conservar al menos un caso que
ejercite `composite_unique`, `default`, `text` y `decimal` con
`precision`/`scale` a la vez, ya que esas cuatro reglas nacieron de la misma
necesidad (reproducir fielmente esquemas de columnas reales, no solo tipos
de ejemplo).
