#!/usr/bin/env python3
"""Generate a Spring Batch microservice that queries "coches" and writes a CSV.

A minimal, self-contained Spring Batch project: one job with a chunk-oriented
step (reader = JDBC query against an H2 "coches" table seeded with sample
data, processor = normalizes the plate, writer = CSV). Meant as a starting
template -- swap the query/model/writer for your own domain to build a real
job on top of it.

Usage:
    python generate_crud.py --batch [target_dir] [--force]
    python -m crud_generator.generate_service [target_dir] [--force]

    target_dir   Directory to create the project in (default:
                 "spring-batch-coches", created if missing).
    --force      Overwrite files that already exist in target_dir.
"""

import argparse
import sys
from pathlib import Path

from .parsing import DefinitionError

DEFAULT_TARGET = "spring-batch-coches"

FILES: dict[str, str] = {}

# --------------------------------------------------------------------------
# Root-level files
# --------------------------------------------------------------------------

FILES[".gitignore"] = r'''target/
*.class
.vscode/
.idea/
/output/
'''

FILES["README.md"] = r'''# spring-batch-coches

Microservicio Spring Batch minimo y autocontenido: un unico job
(`cochesJob`) con un unico paso de chunk (`cochesStep`) que consulta la
tabla `coches` (H2 en memoria, sembrada con datos de muestra), normaliza la
matricula a mayusculas y escribe el resultado en un CSV. Pensado como
plantilla de arranque -- sustituye la consulta, el modelo `Coche` y el
writer por tu propio dominio cuando lo adaptes.

## Arranque

    mvn spring-boot:run

`spring.batch.job.enabled` es `true` por defecto, asi que Spring Boot lanza
`cochesJob` automaticamente al arrancar. Al no haber servidor web, el
proceso termina solo en cuanto el job completa.

## Salida

El CSV se escribe en `output/coches.csv` (ruta configurable con la
propiedad `app.output.coches-csv`), con cabecera
`id,marca,modelo,anio,precio,matricula`.

## Tests

    mvn test

`CochesJobConfigTest` lanza el job contra el repositorio de Spring Batch y
la tabla `coches`, ambos en H2 en memoria, y comprueba que termina en
estado `COMPLETED` y que el CSV generado tiene el contenido esperado.

## Docker

    docker compose up --build

El CSV generado dentro del contenedor aparece en `./output/coches.csv` en
el host (montado como volumen).

## Estructura

    src/main/java/.../CochesBatchApplication.java       Punto de entrada
    src/main/java/.../job/CochesJobConfig.java           Reader + processor + writer + Job/Step
    src/main/java/.../model/Coche.java                   Fila mapeada de la tabla coches
    src/main/resources/application.yml                   Datasource H2 + Spring Batch
    src/main/resources/schema.sql                        Tabla coches
    src/main/resources/data.sql                          Datos de muestra
    src/test/java/.../job/CochesJobConfigTest.java        Test de aceptacion del job
'''

FILES["docker-compose.yml"] = r'''services:
  app:
    build: .
    container_name: spring-batch-coches
    volumes:
      - ./output:/app/output
'''

FILES["Dockerfile"] = r'''# syntax=docker/dockerfile:1

FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app

COPY pom.xml .
RUN mvn -B dependency:go-offline

COPY src ./src
RUN mvn -B clean package -DskipTests

FROM eclipse-temurin:17-jre
WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app
COPY --from=build /app/target/*.jar app.jar
RUN mkdir -p /app/output && chown -R app:app /app
USER app

ENTRYPOINT ["java", "-jar", "app.jar"]
'''

FILES["pom.xml"] = r'''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.4</version>
        <relativePath/>
    </parent>

    <groupId>com.example.batch</groupId>
    <artifactId>spring-batch-coches</artifactId>
    <version>0.0.1-SNAPSHOT</version>
    <name>spring-batch-coches</name>

    <properties>
        <java.version>17</java.version>
    </properties>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-batch</artifactId>
        </dependency>
        <dependency>
            <groupId>com.h2database</groupId>
            <artifactId>h2</artifactId>
            <scope>runtime</scope>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.springframework.batch</groupId>
            <artifactId>spring-batch-test</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>

</project>
'''

# --------------------------------------------------------------------------
# CI
# --------------------------------------------------------------------------

FILES[".github/workflows/ci.yml"] = r'''name: CI

on:
  push:
    branches: ["main", "master"]
  pull_request:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configurar JDK 17
        uses: actions/setup-java@v4
        with:
          java-version: "17"
          distribution: "temurin"
          cache: maven

      - name: mvn verify
        run: mvn --batch-mode --no-transfer-progress verify
'''

# --------------------------------------------------------------------------
# src/main/java
# --------------------------------------------------------------------------

FILES["src/main/java/com/example/batch/CochesBatchApplication.java"] = r'''package com.example.batch;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class CochesBatchApplication {

    public static void main(String[] args) {
        SpringApplication.run(CochesBatchApplication.class, args);
    }
}
'''

FILES["src/main/java/com/example/batch/model/Coche.java"] = r'''package com.example.batch.model;

import java.math.BigDecimal;

/**
 * One row of the "coches" table. Field names match the query's column
 * aliases so BeanPropertyRowMapper can populate it without extra config.
 */
public class Coche {

    private Long id;
    private String marca;
    private String modelo;
    private Integer anio;
    private BigDecimal precio;
    private String matricula;

    public Coche() {
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getMarca() {
        return marca;
    }

    public void setMarca(String marca) {
        this.marca = marca;
    }

    public String getModelo() {
        return modelo;
    }

    public void setModelo(String modelo) {
        this.modelo = modelo;
    }

    public Integer getAnio() {
        return anio;
    }

    public void setAnio(Integer anio) {
        this.anio = anio;
    }

    public BigDecimal getPrecio() {
        return precio;
    }

    public void setPrecio(BigDecimal precio) {
        this.precio = precio;
    }

    public String getMatricula() {
        return matricula;
    }

    public void setMatricula(String matricula) {
        this.matricula = matricula;
    }
}
'''

FILES["src/main/java/com/example/batch/job/CochesJobConfig.java"] = r'''package com.example.batch.job;

import com.example.batch.model.Coche;
import org.springframework.batch.core.Job;
import org.springframework.batch.core.Step;
import org.springframework.batch.core.job.builder.JobBuilder;
import org.springframework.batch.core.repository.JobRepository;
import org.springframework.batch.core.step.builder.StepBuilder;
import org.springframework.batch.item.ItemProcessor;
import org.springframework.batch.item.database.JdbcCursorItemReader;
import org.springframework.batch.item.database.builder.JdbcCursorItemReaderBuilder;
import org.springframework.batch.item.file.FlatFileItemWriter;
import org.springframework.batch.item.file.builder.FlatFileItemWriterBuilder;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.io.FileSystemResource;
import org.springframework.jdbc.core.BeanPropertyRowMapper;
import org.springframework.transaction.PlatformTransactionManager;

import javax.sql.DataSource;

/**
 * Wires the coches job: reader runs the query against the H2 "coches"
 * table (see schema.sql/data.sql), processor uppercases the plate, writer
 * writes the result out as CSV.
 */
@Configuration
public class CochesJobConfig {

    @Bean
    public JdbcCursorItemReader<Coche> cochesReader(DataSource dataSource) {
        return new JdbcCursorItemReaderBuilder<Coche>()
                .name("cochesReader")
                .dataSource(dataSource)
                .sql("SELECT id, marca, modelo, anio, precio, matricula FROM coches ORDER BY id")
                .rowMapper(new BeanPropertyRowMapper<>(Coche.class))
                .build();
    }

    @Bean
    public ItemProcessor<Coche, Coche> cochesProcessor() {
        return coche -> {
            coche.setMatricula(coche.getMatricula().toUpperCase());
            return coche;
        };
    }

    @Bean
    public FlatFileItemWriter<Coche> cochesCsvWriter(
            @Value("${app.output.coches-csv:output/coches.csv}") String outputPath) {
        return new FlatFileItemWriterBuilder<Coche>()
                .name("cochesCsvWriter")
                .resource(new FileSystemResource(outputPath))
                .headerCallback(writer -> writer.write("id,marca,modelo,anio,precio,matricula"))
                .delimited()
                .delimiter(",")
                .names("id", "marca", "modelo", "anio", "precio", "matricula")
                .build();
    }

    @Bean
    public Step cochesStep(
            JobRepository jobRepository,
            PlatformTransactionManager transactionManager,
            JdbcCursorItemReader<Coche> cochesReader,
            ItemProcessor<Coche, Coche> cochesProcessor,
            FlatFileItemWriter<Coche> cochesCsvWriter) {
        return new StepBuilder("cochesStep", jobRepository)
                .<Coche, Coche>chunk(10, transactionManager)
                .reader(cochesReader)
                .processor(cochesProcessor)
                .writer(cochesCsvWriter)
                .build();
    }

    @Bean
    public Job cochesJob(JobRepository jobRepository, Step cochesStep) {
        return new JobBuilder("cochesJob", jobRepository)
                .start(cochesStep)
                .build();
    }
}
'''

# --------------------------------------------------------------------------
# src/main/resources
# --------------------------------------------------------------------------

FILES["src/main/resources/application.yml"] = r'''spring:
  application:
    name: spring-batch-coches

  datasource:
    url: jdbc:h2:mem:coches
    username: sa
    password: ""
    driver-class-name: org.h2.Driver

  batch:
    jdbc:
      initialize-schema: always

app:
  output:
    coches-csv: output/coches.csv
'''

FILES["src/main/resources/schema.sql"] = r'''DROP TABLE IF EXISTS coches;
CREATE TABLE coches (
    id        BIGINT        NOT NULL PRIMARY KEY,
    marca     VARCHAR(50)   NOT NULL,
    modelo    VARCHAR(50)   NOT NULL,
    anio      INT           NOT NULL,
    precio    DECIMAL(10,2) NOT NULL,
    matricula VARCHAR(15)   NOT NULL
);
'''

FILES["src/main/resources/data.sql"] = r'''INSERT INTO coches (id, marca, modelo, anio, precio, matricula) VALUES (1, 'Toyota', 'Corolla', 2021, 21500.00, '1234abc');
INSERT INTO coches (id, marca, modelo, anio, precio, matricula) VALUES (2, 'Seat', 'Leon', 2020, 18700.50, '5678bcd');
INSERT INTO coches (id, marca, modelo, anio, precio, matricula) VALUES (3, 'Renault', 'Megane', 2019, 15900.00, '9012cde');
INSERT INTO coches (id, marca, modelo, anio, precio, matricula) VALUES (4, 'Volkswagen', 'Golf', 2022, 24300.75, '3456def');
INSERT INTO coches (id, marca, modelo, anio, precio, matricula) VALUES (5, 'Ford', 'Focus', 2018, 13200.00, '7890efg');
'''

# --------------------------------------------------------------------------
# src/test/java
# --------------------------------------------------------------------------

FILES["src/test/java/com/example/batch/job/CochesJobConfigTest.java"] = r'''package com.example.batch.job;

import org.junit.jupiter.api.Test;
import org.springframework.batch.core.BatchStatus;
import org.springframework.batch.core.JobExecution;
import org.springframework.batch.test.JobLauncherTestUtils;
import org.springframework.batch.test.context.SpringBatchTest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.EnableAutoConfiguration;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.TestPropertySource;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * coches/data.sql (on the test classpath via src/main/resources) seeds 5
 * rows -- see that file for the raw data.
 */
@SpringBatchTest
@SpringBootTest(classes = {
        CochesJobConfigTest.TestConfig.class,
        CochesJobConfig.class
})
@TestPropertySource(properties = {
        "app.output.coches-csv=target/test-output/coches.csv"
})
class CochesJobConfigTest {

    @EnableAutoConfiguration
    static class TestConfig {
    }

    @Autowired
    private JobLauncherTestUtils jobLauncherTestUtils;

    @Test
    void queriesCochesAndWritesCsv() throws Exception {
        JobExecution execution = jobLauncherTestUtils.launchJob();

        assertThat(execution.getStatus()).isEqualTo(BatchStatus.COMPLETED);

        List<String> lines = Files.readAllLines(Path.of("target/test-output/coches.csv"));
        assertThat(lines).containsExactly(
                "id,marca,modelo,anio,precio,matricula",
                "1,Toyota,Corolla,2021,21500.00,1234ABC",
                "2,Seat,Leon,2020,18700.50,5678BCD",
                "3,Renault,Megane,2019,15900.00,9012CDE",
                "4,Volkswagen,Golf,2022,24300.75,3456DEF",
                "5,Ford,Focus,2018,13200.00,7890EFG");
    }
}
'''


def generate_batch_project(target=None, overwrite=False):
    """Writes the "coches" Spring Batch (query -> CSV) project under `target`.

    Used both by this script's CLI and by `crud_generator.cli` (--batch).
    Raises DefinitionError instead of exiting so callers can report it
    uniformly with the rest of the generator's error handling.
    """
    target_path = Path(target) if target else Path(DEFAULT_TARGET)

    if target_path.exists() and any(target_path.iterdir()) and not overwrite:
        raise DefinitionError(
            f"El directorio '{target_path}' ya existe y no esta vacio "
            "(usa --force para sobrescribirlo)."
        )

    for rel_path, content in FILES.items():
        dest = target_path / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8", newline="\n")

    return str(target_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "target",
        nargs="?",
        default=DEFAULT_TARGET,
        help="directory to generate the project into (default: %(default)s)",
    )
    parser.add_argument("--force", action="store_true", help="overwrite files that already exist")
    args = parser.parse_args()

    try:
        target = generate_batch_project(args.target, overwrite=args.force)
    except DefinitionError as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)

    print(f"Proyecto {target} generado con exito, bajo '{target}/'.")
    print("\nNext steps:")
    print(f"  cd {target}")
    print("  mvn -q test")
    print("  mvn spring-boot:run")


if __name__ == "__main__":
    main()
