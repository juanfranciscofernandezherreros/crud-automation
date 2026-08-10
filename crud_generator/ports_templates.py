"""Plantillas para arquitecturas basadas en dominio, puertos y adaptadores."""


def get_domain(entity_name, package, fields):
    return f"""package {package};

import lombok.*;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class {entity_name} {{
{fields}
}}
"""


def get_persistence_entity(entity_name, entity_lower, package, fields):
    return f"""package {package};

import jakarta.persistence.*;
import lombok.*;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "{entity_lower}s")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@EntityListeners(AuditingEntityListener.class)
public class {entity_name}JpaEntity {{
{fields}
}}
"""


def get_dto(class_name, package, fields):
    return f"""package {package};

import jakarta.validation.constraints.*;
import lombok.Data;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
public class {class_name} {{
{fields}
}}
"""


def get_input_port(entity_name, layout):
    return f"""package {layout.input_package};

import {layout.domain_package}.{entity_name};
import java.util.List;

public interface {entity_name}UseCase {{
    {entity_name} create({entity_name} entity);
    List<{entity_name}> findAll();
    {entity_name} findById(Integer id);
    {entity_name} update(Integer id, {entity_name} replacement);
    {entity_name} patch(Integer id, {entity_name} changes);
    void delete(Integer id);
}}
"""


def get_output_port(entity_name, layout):
    return f"""package {layout.output_package};

import {layout.domain_package}.{entity_name};
import java.util.List;
import java.util.Optional;

public interface {entity_name}PersistencePort {{
    {entity_name} save({entity_name} entity);
    List<{entity_name}> findAll();
    Optional<{entity_name}> findById(Integer id);
    void delete({entity_name} entity);
}}
"""


def get_service(entity_name, layout, update_statements, patch_statements):
    return f"""package {layout.service_package};

import {layout.domain_package}.{entity_name};
import {layout.input_package}.{entity_name}UseCase;
import {layout.output_package}.{entity_name}PersistencePort;
import {layout.exception_package}.ResourceNotFoundException;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;

@Service
@RequiredArgsConstructor
public class {entity_name}Service implements {entity_name}UseCase {{

    private final {entity_name}PersistencePort persistencePort;

    @Override
    @Transactional
    public {entity_name} create({entity_name} entity) {{
        return persistencePort.save(entity);
    }}

    @Override
    @Transactional(readOnly = true)
    public List<{entity_name}> findAll() {{
        return persistencePort.findAll();
    }}

    @Override
    @Transactional(readOnly = true)
    public {entity_name} findById(Integer id) {{
        return getEntity(id);
    }}

    @Override
    @Transactional
    public {entity_name} update(Integer id, {entity_name} replacement) {{
        {entity_name} current = getEntity(id);
{update_statements}
        return persistencePort.save(current);
    }}

    @Override
    @Transactional
    public {entity_name} patch(Integer id, {entity_name} changes) {{
        {entity_name} current = getEntity(id);
{patch_statements}
        return persistencePort.save(current);
    }}

    @Override
    @Transactional
    public void delete(Integer id) {{
        persistencePort.delete(getEntity(id));
    }}

    private {entity_name} getEntity(Integer id) {{
        return persistencePort.findById(id).orElseThrow(() ->
                new ResourceNotFoundException("{entity_name} no encontrado con ID: " + id));
    }}
}}
"""


def get_web_mapper(entity_name, layout):
    return f"""package {layout.web_mapper_package};

import {layout.domain_package}.{entity_name};
import {layout.dto_package}.*;
import org.mapstruct.Mapper;

@Mapper(componentModel = "spring")
public interface {entity_name}WebMapper {{
    {entity_name} toDomain({entity_name}CreateDTO dto);
    {entity_name} toDomain({entity_name}UpdateDTO dto);
    {entity_name} toDomain({entity_name}PatchDTO dto);
    {entity_name}ResponseDTO toDto({entity_name} entity);
}}
"""


def get_persistence_mapper(entity_name, layout):
    return f"""package {layout.persistence_package};

import {layout.domain_package}.{entity_name};
import org.mapstruct.Mapper;

@Mapper(componentModel = "spring")
public interface {entity_name}PersistenceMapper {{
    {entity_name}JpaEntity toJpaEntity({entity_name} domain);
    {entity_name} toDomain({entity_name}JpaEntity entity);
}}
"""


def get_repository(entity_name, layout):
    return f"""package {layout.persistence_package};

import org.springframework.data.jpa.repository.JpaRepository;

public interface {entity_name}JpaRepository
        extends JpaRepository<{entity_name}JpaEntity, Integer> {{
}}
"""


def get_persistence_adapter(entity_name, layout):
    return f"""package {layout.persistence_package};

import {layout.domain_package}.{entity_name};
import {layout.output_package}.{entity_name}PersistencePort;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;
import java.util.List;
import java.util.Optional;

@Component
@RequiredArgsConstructor
public class {entity_name}PersistenceAdapter implements {entity_name}PersistencePort {{

    private final {entity_name}JpaRepository repository;
    private final {entity_name}PersistenceMapper mapper;

    @Override
    public {entity_name} save({entity_name} entity) {{
        return mapper.toDomain(repository.save(mapper.toJpaEntity(entity)));
    }}

    @Override
    public List<{entity_name}> findAll() {{
        return repository.findAll().stream().map(mapper::toDomain).toList();
    }}

    @Override
    public Optional<{entity_name}> findById(Integer id) {{
        return repository.findById(id).map(mapper::toDomain);
    }}

    @Override
    public void delete({entity_name} entity) {{
        repository.delete(mapper.toJpaEntity(entity));
    }}
}}
"""


def get_controller(entity_name, entity_lower, layout):
    return f"""package {layout.controller_package};

import {layout.domain_package}.{entity_name};
import {layout.dto_package}.*;
import {layout.input_package}.{entity_name}UseCase;
import {layout.web_mapper_package}.{entity_name}WebMapper;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;
import java.net.URI;
import java.util.List;

@RestController
@RequestMapping("/api/{entity_lower}s")
@RequiredArgsConstructor
@Tag(name = "{entity_name}")
public class {entity_name}Controller {{

    private final {entity_name}UseCase useCase;
    private final {entity_name}WebMapper mapper;

    @PostMapping
    public ResponseEntity<{entity_name}ResponseDTO> create(
            @Valid @RequestBody {entity_name}CreateDTO dto) {{
        {entity_name} created = useCase.create(mapper.toDomain(dto));
        {entity_name}ResponseDTO response = mapper.toDto(created);
        URI location = ServletUriComponentsBuilder.fromCurrentRequest()
                .path("/{{id}}").buildAndExpand(response.getId()).toUri();
        return ResponseEntity.created(location).body(response);
    }}

    @GetMapping
    public ResponseEntity<List<{entity_name}ResponseDTO>> findAll() {{
        return ResponseEntity.ok(useCase.findAll().stream().map(mapper::toDto).toList());
    }}

    @GetMapping("/{{id}}")
    public ResponseEntity<{entity_name}ResponseDTO> findById(@PathVariable Integer id) {{
        return ResponseEntity.ok(mapper.toDto(useCase.findById(id)));
    }}

    @PutMapping("/{{id}}")
    public ResponseEntity<{entity_name}ResponseDTO> update(
            @PathVariable Integer id, @Valid @RequestBody {entity_name}UpdateDTO dto) {{
        return ResponseEntity.ok(mapper.toDto(useCase.update(id, mapper.toDomain(dto))));
    }}

    @PatchMapping("/{{id}}")
    public ResponseEntity<{entity_name}ResponseDTO> patch(
            @PathVariable Integer id, @Valid @RequestBody {entity_name}PatchDTO dto) {{
        return ResponseEntity.ok(mapper.toDto(useCase.patch(id, mapper.toDomain(dto))));
    }}

    @DeleteMapping("/{{id}}")
    public ResponseEntity<Void> delete(@PathVariable Integer id) {{
        useCase.delete(id);
        return ResponseEntity.noContent().build();
    }}
}}
"""


def get_exception_class(layout):
    return f"""package {layout.exception_package};

public class ResourceNotFoundException extends RuntimeException {{
    public ResourceNotFoundException(String message) {{
        super(message);
    }}
}}
"""


def get_exception_handler(layout):
    return f"""package {layout.exception_package};

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

@RestControllerAdvice
public class GlobalExceptionHandler {{
    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<Map<String, Object>> handleNotFound(ResourceNotFoundException ex) {{
        return error(HttpStatus.NOT_FOUND, ex.getMessage(), Map.of());
    }}

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Map<String, Object>> handleValidation(MethodArgumentNotValidException ex) {{
        Map<String, String> fields = new HashMap<>();
        ex.getBindingResult().getAllErrors().forEach(error -> fields.put(
                ((FieldError) error).getField(), error.getDefaultMessage()));
        return error(HttpStatus.BAD_REQUEST, "Error de validación", fields);
    }}

    private ResponseEntity<Map<String, Object>> error(
            HttpStatus status, String message, Map<String, String> fields) {{
        Map<String, Object> body = new HashMap<>();
        body.put("timestamp", LocalDateTime.now());
        body.put("status", status.value());
        body.put("message", message);
        body.put("validationErrors", fields);
        return new ResponseEntity<>(body, status);
    }}
}}
"""


def get_service_test(entity_name, layout):
    return f"""package {layout.service_package};

import {layout.domain_package}.{entity_name};
import {layout.exception_package}.ResourceNotFoundException;
import {layout.output_package}.{entity_name}PersistencePort;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import java.util.Optional;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class {entity_name}ServiceTest {{
    @Mock
    private {entity_name}PersistencePort persistencePort;

    @InjectMocks
    private {entity_name}Service service;

    @Test
    void create_ReturnsSavedDomain() {{
        {entity_name} entity = new {entity_name}();
        when(persistencePort.save(entity)).thenReturn(entity);

        assertSame(entity, service.create(entity));
        verify(persistencePort).save(entity);
    }}

    @Test
    void findById_ExistingId_ReturnsDomain() {{
        {entity_name} entity = new {entity_name}();
        when(persistencePort.findById(1)).thenReturn(Optional.of(entity));

        assertSame(entity, service.findById(1));
    }}

    @Test
    void findById_MissingId_ThrowsException() {{
        when(persistencePort.findById(99)).thenReturn(Optional.empty());

        assertThrows(ResourceNotFoundException.class, () -> service.findById(99));
    }}
}}
"""


def get_controller_test(
    entity_name,
    entity_lower,
    layout,
    create_assignments,
    has_required_fields,
    invalid_assignments,
):
    required_test = ""
    if has_required_fields:
        required_test = f"""
    @Test
    void create_MissingRequiredInput_Returns400() throws Exception {{
        mockMvc.perform(post("/api/{entity_lower}s")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{{}}"))
                .andExpect(status().isBadRequest());
        verifyNoInteractions(useCase);
    }}
"""
    constraint_test = ""
    if invalid_assignments:
        constraint_test = f"""
    @Test
    void create_InvalidValue_Returns400() throws Exception {{
        {entity_name}CreateDTO createDTO = new {entity_name}CreateDTO();
{invalid_assignments}
        mockMvc.perform(post("/api/{entity_lower}s")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(createDTO)))
                .andExpect(status().isBadRequest());
        verifyNoInteractions(useCase);
    }}
"""

    return f"""package {layout.controller_package};

import {layout.domain_package}.{entity_name};
import {layout.dto_package}.*;
import {layout.input_package}.{entity_name}UseCase;
import {layout.web_mapper_package}.{entity_name}WebMapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import java.time.LocalDate;
import java.time.LocalDateTime;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest({entity_name}Controller.class)
class {entity_name}ControllerTest {{
    @Autowired
    private MockMvc mockMvc;
    @Autowired
    private ObjectMapper objectMapper;
    @MockBean
    private {entity_name}UseCase useCase;
    @MockBean
    private {entity_name}WebMapper mapper;

    @Test
    void create_ValidInput_Returns201() throws Exception {{
        {entity_name}CreateDTO createDTO = new {entity_name}CreateDTO();
{create_assignments}
        {entity_name} domain = new {entity_name}();
        {entity_name}ResponseDTO responseDTO = new {entity_name}ResponseDTO();
        responseDTO.setId(1);
        when(mapper.toDomain(any({entity_name}CreateDTO.class))).thenReturn(domain);
        when(useCase.create(domain)).thenReturn(domain);
        when(mapper.toDto(domain)).thenReturn(responseDTO);

        mockMvc.perform(post("/api/{entity_lower}s")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(createDTO)))
                .andExpect(status().isCreated())
                .andExpect(header().string("Location", "http://localhost/api/{entity_lower}s/1"));
    }}
{required_test}
{constraint_test}

    @Test
    void patch_EmptyInput_Returns200() throws Exception {{
        {entity_name} domain = new {entity_name}();
        when(mapper.toDomain(any({entity_name}PatchDTO.class))).thenReturn(domain);
        when(useCase.patch(1, domain)).thenReturn(domain);
        when(mapper.toDto(domain)).thenReturn(new {entity_name}ResponseDTO());

        mockMvc.perform(patch("/api/{entity_lower}s/1")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{{}}"))
                .andExpect(status().isOk());
    }}
}}
"""
