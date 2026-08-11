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
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-security</artifactId></dependency>
        <dependency><groupId>io.micrometer</groupId><artifactId>micrometer-registry-prometheus</artifactId><scope>runtime</scope></dependency>
        <dependency><groupId>io.micrometer</groupId><artifactId>micrometer-tracing-bridge-otel</artifactId></dependency>
        <dependency><groupId>io.opentelemetry</groupId><artifactId>opentelemetry-exporter-otlp</artifactId></dependency>

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
        <dependency><groupId>org.springframework.security</groupId><artifactId>spring-security-test</artifactId><scope>test</scope></dependency>
        <dependency><groupId>org.testcontainers</groupId><artifactId>junit-jupiter</artifactId><scope>test</scope></dependency>
        <dependency><groupId>org.testcontainers</groupId><artifactId>postgresql</artifactId><scope>test</scope></dependency>
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
      - SPRING_DATASOURCE_USERNAME=${{POSTGRES_USER:?Set POSTGRES_USER}}
      - SPRING_DATASOURCE_PASSWORD=${{POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD}}
      - SPRING_FLYWAY_URL=jdbc:postgresql://db:5432/{entity_lower}_db
      - SPRING_FLYWAY_USER=${{POSTGRES_USER:?Set POSTGRES_USER}}
      - SPRING_FLYWAY_PASSWORD=${{POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD}}
      - APP_SECURITY_USER=${{APP_SECURITY_USER:?Set APP_SECURITY_USER}}
      - APP_SECURITY_PASSWORD=${{APP_SECURITY_PASSWORD:?Set APP_SECURITY_PASSWORD}}
      - OTEL_EXPORTER_OTLP_ENDPOINT=${{OTEL_EXPORTER_OTLP_ENDPOINT:-http://host.docker.internal:4318/v1/traces}}
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB={entity_lower}_db
      - POSTGRES_USER=${{POSTGRES_USER:?Set POSTGRES_USER}}
      - POSTGRES_PASSWORD=${{POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD}}
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${{POSTGRES_USER}} -d $${{POSTGRES_DB}}"]
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
    username: ${{SPRING_DATASOURCE_USERNAME}}
    password: ${{SPRING_DATASOURCE_PASSWORD}}
    driver-class-name: org.postgresql.Driver
  jpa:
    hibernate:
      ddl-auto: validate
    show-sql: ${{JPA_SHOW_SQL:false}}
    properties:
      hibernate:
        format_sql: true
        dialect: org.hibernate.dialect.PostgreSQLDialect
  flyway:
    enabled: true
    baseline-on-migrate: true
  data:
    web:
      pageable:
        default-page-size: 20
        max-page-size: 100
management:
  endpoints:
    web:
      exposure:
        include: health, info, prometheus
  endpoint:
    health:
      show-details: when_authorized
  tracing:
    sampling:
      probability: ${{TRACING_SAMPLING_PROBABILITY:0.1}}
  otlp:
    tracing:
      endpoint: ${{OTEL_EXPORTER_OTLP_ENDPOINT:http://localhost:4318/v1/traces}}
app:
  security:
    user: ${{APP_SECURITY_USER}}
    password: ${{APP_SECURITY_PASSWORD}}
  rate-limit:
    requests-per-minute: ${{RATE_LIMIT_PER_MINUTE:120}}
logging:
  pattern:
    level: "%5p [traceId=%X{{traceId:-}},spanId=%X{{spanId:-}}]"
springdoc:
  api-docs:
    path: /v3/api-docs
  swagger-ui:
    path: /swagger-ui.html
"""

def get_sql_migration(entity_lower, sql_fields, sql_indexes=""):
    indexes = f"\n{sql_indexes}\n" if sql_indexes else ""
    return f"""CREATE TABLE {entity_lower}s (
{sql_fields}
);
{indexes}
CREATE TABLE IF NOT EXISTS idempotency_keys (
    idempotency_key VARCHAR(128) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id INT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (idempotency_key, resource_type)
);
"""

def get_entity(
    entity_name,
    entity_lower,
    entity_fields,
    unique_constraints_annotation="",
    dynamic_insert=False,
    include_all_args_builder=True,
):
    dynamic_insert_import = (
        "\nimport org.hibernate.annotations.DynamicInsert;" if dynamic_insert else ""
    )
    dynamic_insert_annotation = "\n@DynamicInsert" if dynamic_insert else ""
    constructor_annotations = (
        "@AllArgsConstructor\n@Builder\n" if include_all_args_builder else ""
    )
    return f"""package com.example.crud.entity;

import jakarta.persistence.*;
import lombok.*;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;{dynamic_insert_import}

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.math.BigDecimal;

@Entity
@Table(name = "{entity_lower}s"{unique_constraints_annotation}){dynamic_insert_annotation}
@Getter
@Setter
@NoArgsConstructor
{constructor_annotations}@EntityListeners(AuditingEntityListener.class)
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
import java.math.BigDecimal;

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
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.stereotype.Repository;

@Repository
public interface {entity_name}Repository
        extends JpaRepository<{entity_name}, Integer>, JpaSpecificationExecutor<{entity_name}> {{
}}
"""

def get_specification(entity_name, filter_cases):
    return f"""package com.example.crud.specification;

import com.example.crud.entity.{entity_name};
import org.springframework.data.jpa.domain.Specification;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.Map;

public final class {entity_name}Specifications {{

    private {entity_name}Specifications() {{
    }}

    public static Specification<{entity_name}> fromFilters(Map<String, String> filters) {{
        Specification<{entity_name}> spec = Specification.where(null);
        for (Map.Entry<String, String> entry : filters.entrySet()) {{
            String value = entry.getValue();
            if (value == null || value.isBlank()) {{
                continue;
            }}
            switch (entry.getKey()) {{
{filter_cases}
                default -> {{ }}
            }}
        }}
        return spec;
    }}
}}
"""

def get_service(entity_name):
    return f"""package com.example.crud.service;

import com.example.crud.dto.*;
import com.example.crud.entity.{entity_name};
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.domain.Specification;

public interface {entity_name}Service {{
    {entity_name}ResponseDTO create({entity_name}CreateDTO createDTO);
    Page<{entity_name}ResponseDTO> findAll(Pageable pageable, Specification<{entity_name}> spec);
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
import org.springframework.data.jpa.domain.Specification;
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
    public Page<{entity_name}ResponseDTO> findAll(Pageable pageable, Specification<{entity_name}> spec) {{
        return repository.findAll(spec, pageable).map(mapper::toDto);
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
import com.example.crud.configuration.IdempotencyService;
import com.example.crud.service.{entity_name}Service;
import com.example.crud.specification.{entity_name}Specifications;
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
import java.util.Map;

@RestController
@RequestMapping("/api/{entity_lower}s")
@RequiredArgsConstructor
@Tag(name = "{entity_name}", description = "API CRUD para {entity_name}")
public class {entity_name}Controller {{

    private final {entity_name}Service service;
    private final IdempotencyService idempotencyService;

    @PostMapping
    @Operation(summary = "Crear {entity_lower}")
    public ResponseEntity<{entity_name}ResponseDTO> create(
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @Valid @RequestBody {entity_name}CreateDTO dto) {{
        {entity_name}ResponseDTO created = idempotencyService.execute(
                idempotencyKey,
                "{entity_name}",
                () -> service.create(dto),
                service::findById,
                value -> value.getId());
        URI location = ServletUriComponentsBuilder.fromCurrentRequest().path("/{{id}}").buildAndExpand(created.getId()).toUri();
        return ResponseEntity.created(location).body(created);
    }}

    @GetMapping
    @Operation(summary = "Listar {entity_lower}s",
            description = "Admite filtros por igualdad usando cualquier campo de la entidad como query param")
    public ResponseEntity<Page<{entity_name}ResponseDTO>> findAll(
            Pageable pageable, @RequestParam Map<String, String> filters) {{
        return ResponseEntity.ok(service.findAll(pageable, {entity_name}Specifications.fromFilters(filters)));
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

SECURITY_CONFIG = """package com.example.crud.configuration;

import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.security.config.http.SessionCreationPolicy;

@Configuration
@RequiredArgsConstructor
public class SecurityConfiguration {
    private final RateLimitFilter rateLimitFilter;

    @Bean
    SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        return http
                .csrf(csrf -> csrf.disable())
                .sessionManagement(session -> session
                        .sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers("/actuator/health", "/v3/api-docs/**", "/swagger-ui/**").permitAll()
                        .requestMatchers("/actuator/**").hasRole("ADMIN")
                        .requestMatchers(org.springframework.http.HttpMethod.GET, "/api/**").hasAnyRole("USER", "ADMIN")
                        .requestMatchers("/api/**").hasRole("ADMIN")
                        .anyRequest().authenticated())
                .httpBasic(Customizer.withDefaults())
                .addFilterBefore(rateLimitFilter, UsernamePasswordAuthenticationFilter.class)
                .build();
    }

    @Bean
    PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    UserDetailsService userDetailsService(
            @Value("${app.security.user}") String username,
            @Value("${app.security.password}") String password,
            PasswordEncoder encoder) {
        return new InMemoryUserDetailsManager(User.withUsername(username)
                .password(encoder.encode(password)).roles("USER", "ADMIN").build());
    }
}
"""

RATE_LIMIT_FILTER = """package com.example.crud.configuration;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import java.io.IOException;
import java.time.Instant;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class RateLimitFilter extends OncePerRequestFilter {
    private final ConcurrentHashMap<String, Window> windows = new ConcurrentHashMap<>();
    private final int limit;

    public RateLimitFilter(@Value("${app.rate-limit.requests-per-minute:120}") int limit) {
        this.limit = limit;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
            FilterChain chain) throws ServletException, IOException {
        long minute = Instant.now().getEpochSecond() / 60;
        String key = request.getRemoteAddr();
        Window window = windows.compute(key, (ignored, current) ->
                current == null || current.minute != minute ? new Window(minute) : current);
        if (!window.allow(limit)) {
            response.setStatus(HttpStatus.TOO_MANY_REQUESTS.value());
            response.setContentType("application/json");
            response.getWriter().write("{\\\"message\\\":\\\"Rate limit exceeded\\\"}");
            return;
        }
        chain.doFilter(request, response);
    }

    private static final class Window {
        private final long minute;
        private int requests;
        private Window(long minute) { this.minute = minute; }
        private synchronized boolean allow(int limit) { return ++requests <= limit; }
    }
}
"""

IDEMPOTENCY_SERVICE = """package com.example.crud.configuration;

import lombok.RequiredArgsConstructor;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;
import java.util.function.Function;
import java.util.function.Supplier;
import java.util.function.ToIntFunction;

@Component
@RequiredArgsConstructor
public class IdempotencyService {
    private final JdbcTemplate jdbcTemplate;

    @Transactional
    public <T> T execute(String key, String resourceType, Supplier<T> creator,
            Function<Integer, T> loader, ToIntFunction<T> idExtractor) {
        if (key == null || key.isBlank() || key.length() > 128) {
            throw new IllegalArgumentException("Idempotency-Key debe tener entre 1 y 128 caracteres");
        }
        jdbcTemplate.query(
                "SELECT pg_advisory_xact_lock(hashtext(?))",
                rs -> null,
                resourceType + ":" + key);
        List<Integer> existing = jdbcTemplate.query(
                "SELECT resource_id FROM idempotency_keys " +
                        "WHERE idempotency_key=? AND resource_type=?",
                (rs, row) -> rs.getInt(1), key, resourceType);
        if (!existing.isEmpty()) {
            return loader.apply(existing.get(0));
        }
        T created = creator.get();
        jdbcTemplate.update(
                "INSERT INTO idempotency_keys " +
                        "(idempotency_key, resource_type, resource_id) VALUES (?, ?, ?)",
                key, resourceType, idExtractor.applyAsInt(created));
        return created;
    }
}
"""

EXCEPTION_HANDLER = """package com.example.crud.exception;

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
public class GlobalExceptionHandler {

    @ExceptionHandler(PropertyReferenceException.class)
    public ResponseEntity<Map<String, Object>> handleInvalidSortProperty(PropertyReferenceException ex) {
        Map<String, Object> error = new HashMap<>();
        error.put("timestamp", LocalDateTime.now());
        error.put("status", HttpStatus.BAD_REQUEST.value());
        error.put("error", HttpStatus.BAD_REQUEST.getReasonPhrase());
        error.put("message", "Propiedad de ordenación no válida: " + ex.getPropertyName());
        return new ResponseEntity<>(error, HttpStatus.BAD_REQUEST);
    }

    @ExceptionHandler({NumberFormatException.class, DateTimeParseException.class})
    public ResponseEntity<Map<String, Object>> handleInvalidFilterValue(RuntimeException ex) {
        Map<String, Object> error = new HashMap<>();
        error.put("timestamp", LocalDateTime.now());
        error.put("status", HttpStatus.BAD_REQUEST.value());
        error.put("error", HttpStatus.BAD_REQUEST.getReasonPhrase());
        error.put("message", "Valor de filtro no válido: " + ex.getMessage());
        return new ResponseEntity<>(error, HttpStatus.BAD_REQUEST);
    }

    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<Map<String, Object>> handleNotFound(ResourceNotFoundException ex) {
        Map<String, Object> error = new HashMap<>();
        error.put("timestamp", LocalDateTime.now());
        error.put("status", HttpStatus.NOT_FOUND.value());
        error.put("error", HttpStatus.NOT_FOUND.getReasonPhrase());
        error.put("message", ex.getMessage());
        return new ResponseEntity<>(error, HttpStatus.NOT_FOUND);
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<Map<String, Object>> handleBadRequest(IllegalArgumentException ex) {
        Map<String, Object> error = new HashMap<>();
        error.put("timestamp", LocalDateTime.now());
        error.put("status", HttpStatus.BAD_REQUEST.value());
        error.put("error", HttpStatus.BAD_REQUEST.getReasonPhrase());
        error.put("message", ex.getMessage());
        return new ResponseEntity<>(error, HttpStatus.BAD_REQUEST);
    }

    @ExceptionHandler({ObjectOptimisticLockingFailureException.class,
            DataIntegrityViolationException.class})
    public ResponseEntity<Map<String, Object>> handleConflict(RuntimeException ex) {
        Map<String, Object> error = new HashMap<>();
        error.put("timestamp", LocalDateTime.now());
        error.put("status", HttpStatus.CONFLICT.value());
        error.put("error", HttpStatus.CONFLICT.getReasonPhrase());
        error.put("message", "Conflicto de concurrencia o integridad");
        return new ResponseEntity<>(error, HttpStatus.CONFLICT);
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

        mockMvc.perform(post("/api/{entity_lower}s").with(csrf())
                .header("Idempotency-Key", "test-key")
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

        mockMvc.perform(post("/api/{entity_lower}s").with(csrf())
                .header("Idempotency-Key", "test-key")
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
import com.example.crud.configuration.IdempotencyService;
import com.example.crud.service.{entity_name}Service;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.security.test.context.support.WithMockUser;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.math.BigDecimal;

import org.springframework.data.domain.PageImpl;
import java.util.List;

import static org.mockito.ArgumentMatchers.any;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;

@WebMvcTest({entity_name}Controller.class)
@WithMockUser(roles = "ADMIN")
class {entity_name}ControllerTest {{

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private {entity_name}Service service;

    @MockBean
    private IdempotencyService idempotencyService;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void create_ValidInput_Returns201() throws Exception {{
        {entity_name}CreateDTO createDTO = new {entity_name}CreateDTO();
{create_assignments}
        {entity_name}ResponseDTO responseDTO = new {entity_name}ResponseDTO();
        responseDTO.setId(1);

        Mockito.when(idempotencyService.execute(any(), any(), any(), any(), any()))
                .thenReturn(responseDTO);

        mockMvc.perform(post("/api/{entity_lower}s").with(csrf())
                .header("Idempotency-Key", "test-key")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(createDTO)))
                .andExpect(status().isCreated())
                .andExpect(header().string("Location", "http://localhost/api/{entity_lower}s/1"));
    }}
{invalid_test}
{constraint_test}

    @Test
    void findAll_WithFilterQueryParam_Returns200() throws Exception {{
        Mockito.when(service.findAll(any(), any())).thenReturn(new PageImpl<>(List.of()));

        mockMvc.perform(get("/api/{entity_lower}s?page=0&size=5&estadoInventado=cualquier-valor"))
                .andExpect(status().isOk());
    }}

    @Test
    void patch_EmptyInput_Returns200() throws Exception {{
        {entity_name}ResponseDTO responseDTO = new {entity_name}ResponseDTO();
        Mockito.when(service.patch(Mockito.eq(1), any({entity_name}PatchDTO.class)))
                .thenReturn(responseDTO);

        mockMvc.perform(patch("/api/{entity_lower}s/1").with(csrf())
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


def get_postgres_integration_test(entity_lower):
    return f"""package com.example.crud.integration;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;
import com.example.crud.configuration.IdempotencyService;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@Testcontainers(disabledWithoutDocker = true)
class PostgreSQLIntegrationTest {{
    @Container
    static final PostgreSQLContainer<?> POSTGRES =
            new PostgreSQLContainer<>("postgres:16-alpine");

    @DynamicPropertySource
    static void properties(DynamicPropertyRegistry registry) {{
        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", POSTGRES::getUsername);
        registry.add("spring.datasource.password", POSTGRES::getPassword);
        registry.add("spring.flyway.url", POSTGRES::getJdbcUrl);
        registry.add("spring.flyway.user", POSTGRES::getUsername);
        registry.add("spring.flyway.password", POSTGRES::getPassword);
        registry.add("app.security.user", () -> "integration-admin");
        registry.add("app.security.password", () -> "integration-password");
    }}

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Autowired
    private IdempotencyService idempotencyService;

    @Autowired
    private MockMvc mockMvc;

    @Test
    void flywayCreatesTableAndVersionColumn() {{
        Integer tables = jdbcTemplate.queryForObject(
                "SELECT count(*) FROM information_schema.tables " +
                        "WHERE table_schema='public' AND table_name='{entity_lower}s'",
                Integer.class);
        Integer versions = jdbcTemplate.queryForObject(
                "SELECT count(*) FROM information_schema.columns " +
                        "WHERE table_schema='public' AND table_name='{entity_lower}s' " +
                        "AND column_name='version'",
                Integer.class);
        assertEquals(1, tables);
        assertEquals(1, versions);
    }}

    @Test
    void idempotencyKeyCreatesTheResourceOnlyOnce() {{
        AtomicInteger creations = new AtomicInteger();
        Integer first = idempotencyService.execute(
                "integration-key", "integration-resource",
                () -> {{ creations.incrementAndGet(); return 41; }},
                id -> id, Integer::intValue);
        Integer repeated = idempotencyService.execute(
                "integration-key", "integration-resource",
                () -> {{ creations.incrementAndGet(); return 99; }},
                id -> id, Integer::intValue);

        assertEquals(41, first);
        assertEquals(41, repeated);
        assertEquals(1, creations.get());
    }}

    @Test
    void apiRejectsUnauthenticatedRequests() throws Exception {{
        mockMvc.perform(get("/api/{entity_lower}s"))
                .andExpect(status().isUnauthorized());
    }}
}}
"""
