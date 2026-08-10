"""Plantillas de los archivos del proyecto Spring Boot generado."""


def get_pom_xml(entity_lower):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.4</version>
        <relativePath/>
    </parent>
    <groupId>com.example</groupId>
    <artifactId>crud-{entity_lower}</artifactId>
    <version>0.0.1-SNAPSHOT</version>
    <name>crud-{entity_lower}</name>

    <properties>
        <java.version>21</java.version>
        <org.mapstruct.version>1.5.5.Final</org.mapstruct.version>
        <springdoc.version>2.5.0</springdoc.version>
        <lombok.version>1.18.30</lombok.version>
    </properties>

    <dependencies>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-web</artifactId></dependency>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-data-jpa</artifactId></dependency>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-validation</artifactId></dependency>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-actuator</artifactId></dependency>

        <!-- Flyway con versión explícita hardcodeada para evitar errores en el POM -->
        <dependency>
            <groupId>org.flywaydb</groupId>
            <artifactId>flyway-core</artifactId>
            <version>10.8.1</version>
        </dependency>
        <dependency>
            <groupId>org.flywaydb</groupId>
            <artifactId>flyway-database-postgresql</artifactId>
            <version>10.8.1</version>
        </dependency>

        <dependency><groupId>org.postgresql</groupId><artifactId>postgresql</artifactId><scope>runtime</scope></dependency>
        <dependency><groupId>org.projectlombok</groupId><artifactId>lombok</artifactId><optional>true</optional></dependency>
        <dependency><groupId>org.mapstruct</groupId><artifactId>mapstruct</artifactId><version>${{org.mapstruct.version}}</version></dependency>
        <dependency><groupId>org.springdoc</groupId><artifactId>springdoc-openapi-starter-webmvc-ui</artifactId><version>${{springdoc.version}}</version></dependency>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-test</artifactId><scope>test</scope></dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
                <configuration>
                    <excludes>
                        <exclude>
                            <groupId>org.projectlombok</groupId>
                            <artifactId>lombok</artifactId>
                        </exclude>
                    </excludes>
                </configuration>
            </plugin>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <configuration>
                    <source>${{java.version}}</source>
                    <target>${{java.version}}</target>
                    <annotationProcessorPaths>
                        <path><groupId>org.projectlombok</groupId><artifactId>lombok</artifactId><version>${{lombok.version}}</version></path>
                        <path><groupId>org.mapstruct</groupId><artifactId>mapstruct-processor</artifactId><version>${{org.mapstruct.version}}</version></path>
                        <path><groupId>org.projectlombok</groupId><artifactId>lombok-mapstruct-binding</artifactId><version>0.2.0</version></path>
                    </annotationProcessorPaths>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
"""

DOCKERFILE = """FROM maven:3.9.9-eclipse-temurin-21-alpine AS builder
WORKDIR /app
COPY . .
RUN mvn clean package -DskipTests

FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY --from=builder /app/target/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
"""

def get_docker_compose(entity_lower):
    return f"""version: '3.8'
services:
  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      - SPRING_DATASOURCE_URL=jdbc:postgresql://db:5432/{entity_lower}_db
      - SPRING_DATASOURCE_USERNAME=postgres
      - SPRING_DATASOURCE_PASSWORD=postgres
      - SPRING_FLYWAY_URL=jdbc:postgresql://db:5432/{entity_lower}_db
      - SPRING_FLYWAY_USER=postgres
      - SPRING_FLYWAY_PASSWORD=postgres
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB={entity_lower}_db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
"""

def get_application_yml(entity_lower):
    return f"""server:
  port: 8080
spring:
  application:
    name: {entity_lower}-service
  datasource:
    url: ${{SPRING_DATASOURCE_URL:jdbc:postgresql://localhost:5432/{entity_lower}_db}}
    username: ${{SPRING_DATASOURCE_USERNAME:postgres}}
    password: ${{SPRING_DATASOURCE_PASSWORD:postgres}}
    driver-class-name: org.postgresql.Driver
  jpa:
    hibernate:
      ddl-auto: validate
    show-sql: true
    properties:
      hibernate:
        format_sql: true
        dialect: org.hibernate.dialect.PostgreSQLDialect
  flyway:
    enabled: true
    baseline-on-migrate: true
management:
  endpoints:
    web:
      exposure:
        include: health, info, metrics
  endpoint:
    health:
      show-details: always
springdoc:
  api-docs:
    path: /v3/api-docs
  swagger-ui:
    path: /swagger-ui.html
"""

def get_sql_migration(entity_lower, sql_fields):
    return f"""CREATE TABLE {entity_lower}s (
{sql_fields}
);
"""

def get_entity(entity_name, entity_lower, entity_fields):
    return f"""package com.example.crud.entity;

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
public class {entity_name} {{
{entity_fields}
}}
"""

def get_dto(class_name, dto_fields):
    return f"""package com.example.crud.dto;

import jakarta.validation.constraints.*;
import lombok.Data;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
public class {class_name} {{
{dto_fields}
}}
"""

def get_mapper(entity_name):
    return f"""package com.example.crud.mapper;

import com.example.crud.dto.*;
import com.example.crud.entity.{entity_name};
import org.mapstruct.BeanMapping;
import org.mapstruct.Mapper;
import org.mapstruct.MappingTarget;
import org.mapstruct.NullValuePropertyMappingStrategy;

@Mapper(componentModel = "spring")
public interface {entity_name}Mapper {{
    {entity_name} toEntity({entity_name}CreateDTO dto);
    {entity_name} toEntity({entity_name}UpdateDTO dto);
    {entity_name}ResponseDTO toDto({entity_name} entity);

    @BeanMapping(nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
    void updateEntityFromPatchDto({entity_name}PatchDTO dto, @MappingTarget {entity_name} entity);

    void updateEntityFromUpdateDto({entity_name}UpdateDTO dto, @MappingTarget {entity_name} entity);
}}
"""

def get_repository(entity_name):
    return f"""package com.example.crud.repository;

import com.example.crud.entity.{entity_name};
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface {entity_name}Repository extends JpaRepository<{entity_name}, Integer> {{
}}
"""

def get_service(entity_name):
    return f"""package com.example.crud.service;

import com.example.crud.dto.*;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;

public interface {entity_name}Service {{
    {entity_name}ResponseDTO create({entity_name}CreateDTO createDTO);
    Page<{entity_name}ResponseDTO> findAll(Pageable pageable);
    {entity_name}ResponseDTO findById(Integer id);
    {entity_name}ResponseDTO update(Integer id, {entity_name}UpdateDTO updateDTO);
    {entity_name}ResponseDTO patch(Integer id, {entity_name}PatchDTO patchDTO);
    void delete(Integer id);
}}
"""

def get_service_impl(entity_name):
    return f"""package com.example.crud.service.impl;

import com.example.crud.dto.*;
import com.example.crud.entity.{entity_name};
import com.example.crud.exception.ResourceNotFoundException;
import com.example.crud.mapper.{entity_name}Mapper;
import com.example.crud.repository.{entity_name}Repository;
import com.example.crud.service.{entity_name}Service;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class {entity_name}ServiceImpl implements {entity_name}Service {{

    private final {entity_name}Repository repository;
    private final {entity_name}Mapper mapper;

    @Override
    @Transactional
    public {entity_name}ResponseDTO create({entity_name}CreateDTO createDTO) {{
        {entity_name} entity = mapper.toEntity(createDTO);
        return mapper.toDto(repository.save(entity));
    }}

    @Override
    @Transactional(readOnly = true)
    public Page<{entity_name}ResponseDTO> findAll(Pageable pageable) {{
        return repository.findAll(pageable).map(mapper::toDto);
    }}

    @Override
    @Transactional(readOnly = true)
    public {entity_name}ResponseDTO findById(Integer id) {{
        return mapper.toDto(getEntity(id));
    }}

    @Override
    @Transactional
    public {entity_name}ResponseDTO update(Integer id, {entity_name}UpdateDTO updateDTO) {{
        {entity_name} entity = getEntity(id);
        mapper.updateEntityFromUpdateDto(updateDTO, entity);
        return mapper.toDto(repository.save(entity));
    }}

    @Override
    @Transactional
    public {entity_name}ResponseDTO patch(Integer id, {entity_name}PatchDTO patchDTO) {{
        {entity_name} entity = getEntity(id);
        mapper.updateEntityFromPatchDto(patchDTO, entity);
        return mapper.toDto(repository.save(entity));
    }}

    @Override
    @Transactional
    public void delete(Integer id) {{
        repository.delete(getEntity(id));
    }}

    private {entity_name} getEntity(Integer id) {{
        return repository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("{entity_name} no encontrado con ID: " + id));
    }}
}}
"""

def get_controller(entity_name, entity_lower):
    return f"""package com.example.crud.controller;

import com.example.crud.dto.*;
import com.example.crud.service.{entity_name}Service;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;
import java.net.URI;

@RestController
@RequestMapping("/api/{entity_lower}s")
@RequiredArgsConstructor
@Tag(name = "{entity_name}", description = "API CRUD para {entity_name}")
public class {entity_name}Controller {{

    private final {entity_name}Service service;

    @PostMapping
    @Operation(summary = "Crear {entity_lower}")
    public ResponseEntity<{entity_name}ResponseDTO> create(@Valid @RequestBody {entity_name}CreateDTO dto) {{
        {entity_name}ResponseDTO created = service.create(dto);
        URI location = ServletUriComponentsBuilder.fromCurrentRequest().path("/{{id}}").buildAndExpand(created.getId()).toUri();
        return ResponseEntity.created(location).body(created);
    }}

    @GetMapping
    @Operation(summary = "Listar {entity_lower}s")
    public ResponseEntity<Page<{entity_name}ResponseDTO>> findAll(Pageable pageable) {{
        return ResponseEntity.ok(service.findAll(pageable));
    }}

    @GetMapping("/{{id}}")
    @Operation(summary = "Obtener por ID")
    public ResponseEntity<{entity_name}ResponseDTO> findById(@PathVariable Integer id) {{
        return ResponseEntity.ok(service.findById(id));
    }}

    @PutMapping("/{{id}}")
    @Operation(summary = "Actualización completa")
    public ResponseEntity<{entity_name}ResponseDTO> update(@PathVariable Integer id, @Valid @RequestBody {entity_name}UpdateDTO dto) {{
        return ResponseEntity.ok(service.update(id, dto));
    }}

    @PatchMapping("/{{id}}")
    @Operation(summary = "Actualización parcial")
    public ResponseEntity<{entity_name}ResponseDTO> patch(@PathVariable Integer id, @Valid @RequestBody {entity_name}PatchDTO dto) {{
        return ResponseEntity.ok(service.patch(id, dto));
    }}

    @DeleteMapping("/{{id}}")
    @Operation(summary = "Eliminar {entity_lower}")
    public ResponseEntity<Void> delete(@PathVariable Integer id) {{
        service.delete(id);
        return ResponseEntity.noContent().build();
    }}
}}
"""

APP_MAIN = """package com.example.crud;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class CrudApplication {
    public static void main(String[] args) {
        SpringApplication.run(CrudApplication.class, args);
    }
}
"""

AUDITING_CONFIG = """package com.example.crud.configuration;

import org.springframework.context.annotation.Configuration;
import org.springframework.data.jpa.repository.config.EnableJpaAuditing;

@Configuration
@EnableJpaAuditing
public class JpaAuditingConfiguration {
}
"""

EXCEPTION_HANDLER = """package com.example.crud.exception;

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
public class GlobalExceptionHandler {

    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<Map<String, Object>> handleNotFound(ResourceNotFoundException ex) {
        Map<String, Object> error = new HashMap<>();
        error.put("timestamp", LocalDateTime.now());
        error.put("status", HttpStatus.NOT_FOUND.value());
        error.put("error", HttpStatus.NOT_FOUND.getReasonPhrase());
        error.put("message", ex.getMessage());
        return new ResponseEntity<>(error, HttpStatus.NOT_FOUND);
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Map<String, Object>> handleValidationExceptions(MethodArgumentNotValidException ex) {
        Map<String, String> fieldErrors = new HashMap<>();
        ex.getBindingResult().getAllErrors().forEach((error) -> {
            String fieldName = ((FieldError) error).getField();
            String errorMessage = error.getDefaultMessage();
            fieldErrors.put(fieldName, errorMessage);
        });

        Map<String, Object> error = new HashMap<>();
        error.put("timestamp", LocalDateTime.now());
        error.put("status", HttpStatus.BAD_REQUEST.value());
        error.put("error", HttpStatus.BAD_REQUEST.getReasonPhrase());
        error.put("message", "Error de validación en los campos");
        error.put("validationErrors", fieldErrors);

        return new ResponseEntity<>(error, HttpStatus.BAD_REQUEST);
    }
}
"""

EXCEPTION_CLASS = """package com.example.crud.exception;
public class ResourceNotFoundException extends RuntimeException {
    public ResourceNotFoundException(String message) { super(message); }
}
"""

def get_service_test(entity_name):
    return f"""package com.example.crud.service;

import com.example.crud.dto.{entity_name}CreateDTO;
import com.example.crud.dto.{entity_name}ResponseDTO;
import com.example.crud.entity.{entity_name};
import com.example.crud.exception.ResourceNotFoundException;
import com.example.crud.mapper.{entity_name}Mapper;
import com.example.crud.repository.{entity_name}Repository;
import com.example.crud.service.impl.{entity_name}ServiceImpl;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class {entity_name}ServiceTest {{

    @Mock
    private {entity_name}Repository repository;

    @Mock
    private {entity_name}Mapper mapper;

    @InjectMocks
    private {entity_name}ServiceImpl service;

    private {entity_name} entity;
    private {entity_name}ResponseDTO responseDTO;

    @BeforeEach
    void setUp() {{
        entity = new {entity_name}();
        responseDTO = new {entity_name}ResponseDTO();
    }}

    @Test
    void create_ReturnsResponseDTO() {{
        {entity_name}CreateDTO createDTO = new {entity_name}CreateDTO();

        when(mapper.toEntity(any({entity_name}CreateDTO.class))).thenReturn(entity);
        when(repository.save(any({entity_name}.class))).thenReturn(entity);
        when(mapper.toDto(any({entity_name}.class))).thenReturn(responseDTO);

        {entity_name}ResponseDTO result = service.create(createDTO);

        assertNotNull(result);
        verify(repository).save(any({entity_name}.class));
    }}

    @Test
    void findById_ExistingId_ReturnsResponseDTO() {{
        when(repository.findById(1)).thenReturn(Optional.of(entity));
        when(mapper.toDto(entity)).thenReturn(responseDTO);

        {entity_name}ResponseDTO result = service.findById(1);

        assertNotNull(result);
    }}

    @Test
    void findById_NonExistingId_ThrowsException() {{
        when(repository.findById(99)).thenReturn(Optional.empty());

        assertThrows(ResourceNotFoundException.class, () -> service.findById(99));
    }}
}}
"""

def get_controller_test(
    entity_name,
    entity_lower,
    create_assignments,
    has_required_fields,
    invalid_assignments,
):
    invalid_test = ""
    if has_required_fields:
        invalid_test = f"""
    @Test
    void create_MissingRequiredInput_Returns400() throws Exception {{
        {entity_name}CreateDTO createDTO = new {entity_name}CreateDTO();

        mockMvc.perform(post("/api/{entity_lower}s")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(createDTO)))
                .andExpect(status().isBadRequest());

        Mockito.verifyNoInteractions(service);
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

        Mockito.verifyNoInteractions(service);
    }}
"""

    return f"""package com.example.crud.controller;

import com.example.crud.dto.{entity_name}CreateDTO;
import com.example.crud.dto.{entity_name}PatchDTO;
import com.example.crud.dto.{entity_name}ResponseDTO;
import com.example.crud.service.{entity_name}Service;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.time.LocalDate;
import java.time.LocalDateTime;

import static org.mockito.ArgumentMatchers.any;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest({entity_name}Controller.class)
class {entity_name}ControllerTest {{

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private {entity_name}Service service;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void create_ValidInput_Returns201() throws Exception {{
        {entity_name}CreateDTO createDTO = new {entity_name}CreateDTO();
{create_assignments}
        {entity_name}ResponseDTO responseDTO = new {entity_name}ResponseDTO();
        responseDTO.setId(1);

        Mockito.when(service.create(any({entity_name}CreateDTO.class))).thenReturn(responseDTO);

        mockMvc.perform(post("/api/{entity_lower}s")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(createDTO)))
                .andExpect(status().isCreated())
                .andExpect(header().string("Location", "http://localhost/api/{entity_lower}s/1"));
    }}
{invalid_test}
{constraint_test}

    @Test
    void patch_EmptyInput_Returns200() throws Exception {{
        {entity_name}ResponseDTO responseDTO = new {entity_name}ResponseDTO();
        Mockito.when(service.patch(Mockito.eq(1), any({entity_name}PatchDTO.class)))
                .thenReturn(responseDTO);

        mockMvc.perform(patch("/api/{entity_lower}s/1")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{{}}"))
                .andExpect(status().isOk());
    }}

    @Test
    void findById_ExistingId_Returns200() throws Exception {{
        {entity_name}ResponseDTO responseDTO = new {entity_name}ResponseDTO();

        Mockito.when(service.findById(1)).thenReturn(responseDTO);

        mockMvc.perform(get("/api/{entity_lower}s/1")
                .contentType(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }}
}}
"""
