"""Fragmentos de generación Java compartidos entre `templates.py` (layered) y
`ports_templates.py` (hexagonal/clean). Antes de este módulo, cada arquitectura
implementaba por su cuenta la entidad JPA, el DTO y la resolución de campos
`reference` contra su repositorio — casi carácter por carácter iguales, pero
con dos copias que había que recordar mantener sincronizadas. Ver
`informes/historial-commits.html` para el porqué (cualquier fix aplicado a una
arquitectura y olvidado en la otra es el mayor riesgo del generador)."""


def capitalize_first(camel_name):
    """'cliente' -> 'Cliente'. Usado para construir getters/setters
    (get{Suffix}/set{Suffix}) a partir de un camelCase de campo."""
    return camel_name[0].upper() + camel_name[1:]


def render_jpa_entity_class(
    package,
    class_name,
    entity_lower,
    fields,
    unique_constraints_annotation="",
    dynamic_insert=False,
    include_all_args_builder=True,
    enum_import_lines="",
    has_inverse_relations=False,
):
    """Cuerpo de una clase de entidad JPA. Usado tanto por la entidad "todo en
    uno" de layered (`templates.get_entity`, `class_name == entity_name`) como
    por la entidad de persistencia de hexagonal/clean
    (`ports_templates.get_persistence_entity`, `class_name ==
    f"{entity_name}JpaEntity"`)."""
    dynamic_insert_import = (
        "\nimport org.hibernate.annotations.DynamicInsert;" if dynamic_insert else ""
    )
    dynamic_insert_annotation = "\n@DynamicInsert" if dynamic_insert else ""
    constructor_annotations = (
        "@AllArgsConstructor\n@Builder\n" if include_all_args_builder else ""
    )
    list_import = "\nimport java.util.List;" if has_inverse_relations else ""
    enum_imports = f"{enum_import_lines}\n" if enum_import_lines else ""
    return f"""package {package};

import jakarta.persistence.*;
import lombok.*;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;{dynamic_insert_import}
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.math.BigDecimal;{list_import}
{enum_imports}
@Entity
@Table(name = "{entity_lower}s"{unique_constraints_annotation}){dynamic_insert_annotation}
@Getter
@Setter
@NoArgsConstructor
{constructor_annotations}@EntityListeners(AuditingEntityListener.class)
public class {class_name} {{
{fields}
}}
"""


def render_dto_class(package, class_name, fields, enum_import_lines=""):
    """Cuerpo de un DTO (`@Data`). Usado por `templates.get_dto` (layered,
    paquete fijo `com.example.crud.dto`) y `ports_templates.get_dto`
    (hexagonal/clean, paquete de `layout.dto_package`)."""
    enum_imports = f"{enum_import_lines}\n" if enum_import_lines else ""
    return f"""package {package};

import jakarta.validation.constraints.*;
import lombok.Data;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.math.BigDecimal;
{enum_imports}
@Data
public class {class_name} {{
{fields}
}}
"""


def render_reference_imports_block(
    reference_attrs, entity_package, repository_package,
    target_type_suffix="", repository_type_suffix="Repository",
):
    """Imports de la entidad y el repositorio referenciados por cada campo
    'reference'. En layered viven en paquetes distintos (`entity`/
    `repository`); en hexagonal/clean, ambos en `layout.persistence_package`
    — de ahí que `entity_package`/`repository_package` se pasen por
    separado en vez de asumir que son iguales."""
    reference_imports = "\n".join(
        f"import {entity_package}.{attr['references']}{target_type_suffix};\n"
        f"import {repository_package}.{attr['references']}{repository_type_suffix};"
        for attr in reference_attrs
    )
    return f"{reference_imports}\n" if reference_imports else ""


def render_reference_fields_block(reference_attrs, repository_type_suffix="Repository"):
    """Campos `private final XRepository xRepository;` inyectados para
    resolver cada 'reference' antes de guardar."""
    reference_fields = "\n".join(
        f"    private final {attr['references']}{repository_type_suffix} {attr['camel_name']}Repository;"
        for attr in reference_attrs
    )
    return f"\n{reference_fields}" if reference_fields else ""


def render_reference_resolvers_block(reference_attrs, target_type_suffix=""):
    """Métodos privados `resolve{Suffix}(Integer id)` que consultan el
    repositorio de la entidad referenciada y lanzan `ResourceNotFoundException`
    si no existe. `target_type_suffix` es "" en layered (`Cliente`) y
    "JpaEntity" en hexagonal/clean (`ClienteJpaEntity`)."""
    resolvers = "\n\n".join(
        f"    private {attr['references']}{target_type_suffix} "
        f"resolve{capitalize_first(attr['camel_name'])}(Integer {attr['camel_name']}Id) {{\n"
        f"        if ({attr['camel_name']}Id == null) {{\n"
        "            return null;\n"
        "        }\n"
        f"        return {attr['camel_name']}Repository.findById({attr['camel_name']}Id)\n"
        f'                .orElseThrow(() -> new ResourceNotFoundException('
        f'"{attr["references"]} no encontrado: " + {attr["camel_name"]}Id));\n'
        "    }"
        for attr in reference_attrs
    )
    return f"\n\n{resolvers}" if resolvers else ""


def render_reference_resolution_calls(reference_attrs, target_var, source_var, indent="        "):
    """Una línea por 'reference': `target.setX(resolveX(source.getXId()));`.
    Usado tal cual por hexagonal/clean (un único punto de resolución, en
    `save()`) y por layered en `create`/`update` (con `source_var` distinto
    por caso: `createDTO`/`updateDTO`); `patch` en layered necesita además un
    null-check por campo y se queda fuera de este helper."""
    return "\n".join(
        f"{indent}{target_var}.set{capitalize_first(attr['camel_name'])}("
        f"resolve{capitalize_first(attr['camel_name'])}({source_var}.get{capitalize_first(attr['camel_name'])}Id()));"
        for attr in reference_attrs
    )


def render_global_exception_handler(package):
    """`@RestControllerAdvice` compartido: antes de este helper, layered
    repetía el bloque `Map<String,Object> error = ...; error.put(...)` en
    cada uno de los 6 handlers (sin la clave "error" del reason-phrase en
    ningún sitio salvo aqui), y hexagonal/clean ya lo habia factorizado en un
    metodo privado `error(status, message, fields)` pero SIN esa misma clave
    y con un texto de validacion distinto — las dos arquitecturas llevaban
    tiempo respondiendo con una forma de error ligeramente distinta para la
    misma API, justo el tipo de deriva que este modulo existe para evitar.
    Se unifica en la version factorizada (mas corta) incluyendo la clave
    "error" y el texto de validacion mas descriptivo de layered."""
    return f"""package {package};

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.orm.ObjectOptimisticLockingFailureException;
import org.springframework.data.mapping.PropertyReferenceException;

import java.time.LocalDateTime;
import java.time.format.DateTimeParseException;
import java.util.HashMap;
import java.util.Map;

@RestControllerAdvice
public class GlobalExceptionHandler {{

    @ExceptionHandler(PropertyReferenceException.class)
    public ResponseEntity<Map<String, Object>> handleInvalidSortProperty(PropertyReferenceException ex) {{
        return error(HttpStatus.BAD_REQUEST,
                "Propiedad de ordenación no válida: " + ex.getPropertyName(), Map.of());
    }}

    @ExceptionHandler({{NumberFormatException.class, DateTimeParseException.class}})
    public ResponseEntity<Map<String, Object>> handleInvalidFilterValue(RuntimeException ex) {{
        return error(HttpStatus.BAD_REQUEST, "Valor de filtro no válido: " + ex.getMessage(), Map.of());
    }}

    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<Map<String, Object>> handleNotFound(ResourceNotFoundException ex) {{
        return error(HttpStatus.NOT_FOUND, ex.getMessage(), Map.of());
    }}

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<Map<String, Object>> handleBadRequest(IllegalArgumentException ex) {{
        return error(HttpStatus.BAD_REQUEST, ex.getMessage(), Map.of());
    }}

    @ExceptionHandler({{ObjectOptimisticLockingFailureException.class,
            DataIntegrityViolationException.class}})
    public ResponseEntity<Map<String, Object>> handleConflict(RuntimeException ex) {{
        return error(HttpStatus.CONFLICT, "Conflicto de concurrencia o integridad", Map.of());
    }}

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Map<String, Object>> handleValidationExceptions(MethodArgumentNotValidException ex) {{
        Map<String, String> fieldErrors = new HashMap<>();
        ex.getBindingResult().getAllErrors().forEach(fieldError -> fieldErrors.put(
                ((FieldError) fieldError).getField(), fieldError.getDefaultMessage()));
        return error(HttpStatus.BAD_REQUEST, "Error de validación en los campos", fieldErrors);
    }}

    private ResponseEntity<Map<String, Object>> error(
            HttpStatus status, String message, Map<String, String> fieldErrors) {{
        Map<String, Object> body = new HashMap<>();
        body.put("timestamp", LocalDateTime.now());
        body.put("status", status.value());
        body.put("error", status.getReasonPhrase());
        body.put("message", message);
        body.put("validationErrors", fieldErrors);
        return new ResponseEntity<>(body, status);
    }}
}}
"""
