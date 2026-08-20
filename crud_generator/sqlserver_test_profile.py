"""Adaptaciones de tests e idempotencia cuando el proyecto usa SQL Server."""


def _sqlserver_integration_test(entity_lower, pluralize):
    table = pluralize(entity_lower)
    return f'''package com.example.crud.integration;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;
import com.example.crud.configuration.IdempotencyService;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.MSSQLServerContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@Testcontainers(disabledWithoutDocker = true)
class SQLServerIntegrationTest {{
    @Container
    static final MSSQLServerContainer<?> SQLSERVER =
            new MSSQLServerContainer<>("mcr.microsoft.com/mssql/server:2022-latest")
                    .acceptLicense();

    @DynamicPropertySource
    static void properties(DynamicPropertyRegistry registry) {{
        registry.add("spring.datasource.sqlserverdb.url", SQLSERVER::getJdbcUrl);
        registry.add("spring.datasource.sqlserverdb.username", SQLSERVER::getUsername);
        registry.add("spring.datasource.sqlserverdb.password", SQLSERVER::getPassword);
        registry.add("spring.datasource.sqlserverdb.driver-class-name", SQLSERVER::getDriverClassName);
        registry.add("spring.flyway.url", SQLSERVER::getJdbcUrl);
        registry.add("spring.flyway.user", SQLSERVER::getUsername);
        registry.add("spring.flyway.password", SQLSERVER::getPassword);
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
                "SELECT count(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = ?",
                Integer.class, "{table}");
        Integer versions = jdbcTemplate.queryForObject(
                "SELECT count(*) FROM INFORMATION_SCHEMA.COLUMNS " +
                        "WHERE TABLE_NAME = ? AND COLUMN_NAME = 'version'",
                Integer.class, "{table}");
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
        mockMvc.perform(get("/api/{table}"))
                .andExpect(status().isUnauthorized());
    }}
}}
'''


def _sqlserver_cucumber_configuration():
    return '''package com.example.crud.cucumber;

import io.cucumber.spring.CucumberContextConfiguration;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.MSSQLServerContainer;

@CucumberContextConfiguration
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public class CucumberSpringConfiguration {

    static final MSSQLServerContainer<?> SQLSERVER =
            new MSSQLServerContainer<>("mcr.microsoft.com/mssql/server:2022-latest")
                    .acceptLicense();

    static {
        SQLSERVER.start();
    }

    @DynamicPropertySource
    static void properties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.sqlserverdb.url", SQLSERVER::getJdbcUrl);
        registry.add("spring.datasource.sqlserverdb.username", SQLSERVER::getUsername);
        registry.add("spring.datasource.sqlserverdb.password", SQLSERVER::getPassword);
        registry.add("spring.datasource.sqlserverdb.driver-class-name", SQLSERVER::getDriverClassName);
        registry.add("spring.flyway.url", SQLSERVER::getJdbcUrl);
        registry.add("spring.flyway.user", SQLSERVER::getUsername);
        registry.add("spring.flyway.password", SQLSERVER::getPassword);
        registry.add("app.security.user", () -> "cucumber-admin");
        registry.add("app.security.password", () -> "cucumber-password");
    }
}
'''


def _sqlserver_idempotency_service():
    return '''package com.example.crud.configuration;

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
        jdbcTemplate.queryForObject(
                "DECLARE @result int; " +
                "EXEC @result = sp_getapplock @Resource = ?, @LockMode = 'Exclusive', " +
                "@LockOwner = 'Transaction', @LockTimeout = 10000; SELECT @result;",
                Integer.class, resourceType + ":" + key);
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
'''


def install_sqlserver_test_profile():
    """Hace que todos los tests y helpers DB generados sean nativos de SQL Server."""
    from . import parsing, templates

    templates.get_postgres_integration_test = (
        lambda entity_lower: _sqlserver_integration_test(entity_lower, parsing.pluralize)
    )
    templates.get_cucumber_spring_configuration = _sqlserver_cucumber_configuration
    templates.IDEMPOTENCY_SERVICE = _sqlserver_idempotency_service()

    # El generador histórico escribe el nombre PostgreSQLIntegrationTest.java.
    # Interceptamos únicamente ese path para que el nombre del fichero coincida
    # con la clase pública SQLServerIntegrationTest.
    from . import generator
    original_generator_write = generator._write_file

    def generator_write(path, content):
        if path.endswith("/PostgreSQLIntegrationTest.java"):
            path = path[:-len("PostgreSQLIntegrationTest.java")] + "SQLServerIntegrationTest.java"
        original_generator_write(path, content)

    generator._write_file = generator_write

    try:
        from . import ports_generator
        original_ports_write = ports_generator._write_file

        def ports_write(path, content):
            if path.endswith("/PostgreSQLIntegrationTest.java"):
                path = path[:-len("PostgreSQLIntegrationTest.java")] + "SQLServerIntegrationTest.java"
            original_ports_write(path, content)

        ports_generator._write_file = ports_write
    except AttributeError:
        pass
