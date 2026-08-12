"""Plantillas del proyecto Kafka Streams generado por --stream. Basadas en el
patrón de referencia: Spring Boot + Spring Kafka + Kafka Streams, filtro
opcional + agregación con estado (KTable/RocksDB) + join de enriquecimiento."""

from .parsing import to_camel_case


def _pascal_case(camel_name):
    return camel_name[0].upper() + camel_name[1:]


def get_pom_xml(project):
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
    <artifactId>{project}</artifactId>
    <version>0.0.1-SNAPSHOT</version>
    <name>{project}</name>

    <properties>
        <java.version>21</java.version>
        <lombok.version>1.18.30</lombok.version>
    </properties>

    <dependencies>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter</artifactId></dependency>
        <dependency><groupId>org.springframework.kafka</groupId><artifactId>spring-kafka</artifactId></dependency>
        <dependency><groupId>org.apache.kafka</groupId><artifactId>kafka-streams</artifactId></dependency>
        <dependency><groupId>com.fasterxml.jackson.core</groupId><artifactId>jackson-databind</artifactId></dependency>
        <dependency><groupId>org.projectlombok</groupId><artifactId>lombok</artifactId><optional>true</optional></dependency>

        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-test</artifactId><scope>test</scope></dependency>
        <dependency><groupId>org.springframework.kafka</groupId><artifactId>spring-kafka-test</artifactId><scope>test</scope></dependency>
        <!-- Sin version explicita: Spring Boot la gestiona junto con kafka-streams -->
        <dependency><groupId>org.apache.kafka</groupId><artifactId>kafka-streams-test-utils</artifactId><scope>test</scope></dependency>
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
                    </annotationProcessorPaths>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
"""


def get_application(package, project_class_prefix):
    return f"""package {package};

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class {project_class_prefix}Application {{
    public static void main(String[] args) {{
        SpringApplication.run({project_class_prefix}Application.class, args);
    }}
}}
"""


def get_kafka_streams_config(package, project, project_class_prefix, input_topic, output_topic):
    return f"""package {package}.config;

import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.streams.StreamsConfig;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.annotation.EnableKafkaStreams;
import org.springframework.kafka.config.KafkaStreamsConfiguration;

import java.util.HashMap;
import java.util.Map;

@Configuration
@EnableKafkaStreams
public class KafkaStreamsConfig {{

    @Value("${{spring.kafka.bootstrap-servers}}")
    private String bootstrapServers;

    @Value("${{spring.kafka.streams.application-id}}")
    private String applicationId;

    @Value("${{spring.kafka.streams.properties.state.dir}}")
    private String stateDir;

    @Bean(name = "defaultKafkaStreamsConfig")
    public KafkaStreamsConfiguration kStreamsConfig() {{
        Map<String, Object> props = new HashMap<>();
        props.put(StreamsConfig.APPLICATION_ID_CONFIG, applicationId);
        props.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
        props.put(StreamsConfig.STATE_DIR_CONFIG, stateDir);
        return new KafkaStreamsConfiguration(props);
    }}

    @Bean
    public NewTopic {project_class_prefix[0].lower()}{project_class_prefix[1:]}InputTopic() {{
        return new NewTopic("{input_topic}", 3, (short) 1);
    }}

    @Bean
    public NewTopic {project_class_prefix[0].lower()}{project_class_prefix[1:]}OutputTopic() {{
        return new NewTopic("{output_topic}", 3, (short) 1);
    }}
}}
"""


def get_model(package, class_name, fields, with_json_property):
    field_lines = []
    for field in fields:
        annotation = (
            f'    @JsonProperty("{field["camel_name"]}")\n' if with_json_property else ""
        )
        field_lines.append(f"{annotation}    private {field['java_type']} {field['camel_name']};")
    fields_block = "\n\n".join(field_lines)
    json_import = "\nimport com.fasterxml.jackson.annotation.JsonProperty;" if with_json_property else ""
    return f"""package {package}.model;
{json_import}
import lombok.*;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@ToString
@EqualsAndHashCode
public class {class_name} {{
{fields_block}
}}
"""


def _filter_line(definition, input_fields):
    """Siempre descarta tombstones (valor null: p.ej. un borrado logico en el
    topic origen) antes de que el resto de la topologia toque ningun getter —
    sin este filtro, un tombstone revienta el stream-thread con
    NullPointerException en selectKey/mapValues. Se combina con la condicion
    de 'processing.filter_*' cuando el usuario configura una."""
    condition = "v != null"
    if definition["filter_field"]:
        filter_camel = next(
            f["camel_name"] for f in input_fields if f["name"] == definition["filter_field"]
        )
        filter_getter = f"get{_pascal_case(filter_camel)}"
        condition += (
            f" && v.{filter_getter}() != null "
            f'&& v.{filter_getter}() {definition["filter_operator"]} {definition["filter_value"]}'
        )
    return f"\n                .filter((k, v) -> {condition})"


def _get_passthrough_topology(definition):
    """Sin 'processing.group_by_field'/'aggregate_field'/'aggregate_as': lee el
    topic de entrada y reescribe cada evento tal cual (mapeando campo a campo,
    sin cambios) en el topic de salida. Sin estado, sin KTable, sin join."""
    package = definition["package"]
    project_class_prefix = definition["project_class_prefix"]
    input_event = definition["input_event"]
    output_event = definition["output_event"]
    input_topic = definition["input_topic"]
    output_topic = definition["output_topic"]
    input_fields = definition["input_fields"]

    constructor_args = ", ".join(
        f"v.get{_pascal_case(f['camel_name'])}()" for f in input_fields
    )
    filter_line = _filter_line(definition, input_fields)
    bean_name = f"{project_class_prefix[0].lower()}{project_class_prefix[1:]}Stream"

    return f"""package {package}.topology;

import {package}.model.{input_event};
import {package}.model.{output_event};
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.kstream.Consumed;
import org.apache.kafka.streams.kstream.KStream;
import org.apache.kafka.streams.kstream.Produced;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.support.serializer.JsonSerde;

@Configuration
public class {project_class_prefix}Topology {{

    @Bean
    public KStream<String, {output_event}> {bean_name}(StreamsBuilder builder) {{
        JsonSerde<{input_event}> inputSerde = new JsonSerde<>({input_event}.class);
        JsonSerde<{output_event}> outputSerde = new JsonSerde<>({output_event}.class);

        KStream<String, {output_event}> relayed = builder
                .stream("{input_topic}", Consumed.with(Serdes.String(), inputSerde)){filter_line}
                .mapValues(v -> new {output_event}({constructor_args}));

        relayed.to("{output_topic}", Produced.with(Serdes.String(), outputSerde));
        return relayed;
    }}
}}
"""


def get_topology(definition, state_store_name):
    """definition: el dict devuelto por stream_schema.load_stream_definition."""
    if definition["group_by_field"] is None:
        return _get_passthrough_topology(definition)

    package = definition["package"]
    project_class_prefix = definition["project_class_prefix"]
    input_event = definition["input_event"]
    output_event = definition["output_event"]
    input_topic = definition["input_topic"]
    output_topic = definition["output_topic"]
    input_fields = definition["input_fields"]
    group_by_camel = next(
        f["camel_name"] for f in input_fields if f["name"] == definition["group_by_field"]
    )
    aggregate_camel = next(
        f["camel_name"] for f in input_fields if f["name"] == definition["aggregate_field"]
    )
    group_by_getter = f"get{_pascal_case(group_by_camel)}"
    aggregate_getter = f"get{_pascal_case(aggregate_camel)}"

    filter_line = _filter_line(definition, input_fields)

    constructor_args = ", ".join(
        f"order.get{_pascal_case(f['camel_name'])}()" for f in input_fields
    )

    return f"""package {package}.topology;

import {package}.model.{input_event};
import {package}.model.{output_event};
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.common.utils.Bytes;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.kstream.*;
import org.apache.kafka.streams.state.KeyValueStore;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.support.serializer.JsonSerde;

@Configuration
public class {project_class_prefix}Topology {{

    @Bean
    public KStream<String, {output_event}> {project_class_prefix[0].lower()}{project_class_prefix[1:]}Stream(StreamsBuilder builder) {{
        JsonSerde<{input_event}> inputSerde = new JsonSerde<>({input_event}.class);
        JsonSerde<{output_event}> outputSerde = new JsonSerde<>({output_event}.class);

        KStream<String, {input_event}> baseStream = builder
                .stream("{input_topic}", Consumed.with(Serdes.String(), inputSerde)){filter_line};

        KStream<String, {input_event}> repartitioned = baseStream
                .selectKey((k, v) -> v.{group_by_getter}() != null ? v.{group_by_getter}() : "UNKNOWN");

        KGroupedStream<String, {input_event}> grouped = repartitioned.groupByKey(
                Grouped.with(Serdes.String(), inputSerde)
        );

        KTable<String, Double> totals = grouped.aggregate(
                () -> 0.0,
                (key, order, aggregate) -> aggregate + order.{aggregate_getter}(),
                Materialized.<String, Double, KeyValueStore<Bytes, byte[]>>as("{state_store_name}")
                        .withKeySerde(Serdes.String())
                        .withValueSerde(Serdes.Double())
        );

        KStream<String, {output_event}> enrichedStream = repartitioned.join(
                totals,
                (order, total) -> new {output_event}({constructor_args}, total),
                Joined.with(Serdes.String(), inputSerde, Serdes.Double())
        );

        enrichedStream.to("{output_topic}", Produced.with(Serdes.String(), outputSerde));
        return enrichedStream;
    }}
}}
"""


def get_application_yml(project, input_topic_dummy=None):
    return f"""spring:
  application:
    name: {project}
  kafka:
    bootstrap-servers: ${{KAFKA_BOOTSTRAP_SERVERS:localhost:9092}}
    streams:
      application-id: {project}-app-v1
      properties:
        state.dir: ${{KAFKA_STREAMS_STATE_DIR:/tmp/kafka-streams/{project}}}
"""


def get_docker_compose(project):
    return f"""version: '3.8'
services:
  kafka:
    image: apache/kafka:3.7.0
    ports:
      - "29092:29092"
    environment:
      - KAFKA_NODE_ID=1
      - KAFKA_PROCESS_ROLES=broker,controller
      - KAFKA_LISTENERS=PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093,PLAINTEXT_HOST://0.0.0.0:29092
      # Dos listeners con nombres distintos: 'kafka:9092' es el que resuelven los
      # contenedores de la red de docker compose (p.ej. 'app'); 'localhost:29092'
      # es el que resuelve el host. Un solo listener advertised como 'localhost'
      # rompe al cliente 'app', que tras el bootstrap recibe esa metadata y
      # intenta reconectar a su propio 'localhost' en vez de al broker.
      - KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092,PLAINTEXT_HOST://localhost:29092
      - KAFKA_CONTROLLER_LISTENER_NAMES=CONTROLLER
      - KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      - KAFKA_INTER_BROKER_LISTENER_NAME=PLAINTEXT
      - KAFKA_CONTROLLER_QUORUM_VOTERS=1@localhost:9093
      - KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1

  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
    depends_on:
      - kafka
"""


DOCKERFILE = """FROM maven:3.9.9-eclipse-temurin-21-alpine AS builder
WORKDIR /app
COPY . .
RUN mvn clean package -DskipTests

# Imagen glibc (no alpine/musl): el store RocksDB de Kafka Streams carga una
# libreria nativa (librocksdbjni) enlazada contra libstdc++.so.6 de glibc, que
# no existe en alpine y hace fallar el arranque con UnsatisfiedLinkError.
FROM eclipse-temurin:21-jre-jammy
WORKDIR /app
COPY --from=builder /app/target/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
"""

GITIGNORE = """target/
"""


def _sample_value(field, value):
    if value is None:
        return "null"
    if field["type"] == "string":
        return f'"{value}"'
    if field["type"] == "double":
        return f"{float(value)}"
    if field["type"] in {"int", "long"}:
        return str(int(value))
    if field["type"] == "boolean":
        return "true" if value else "false"
    return str(value)


def _build_event_args(input_fields, overrides, sample_field_defaults=None):
    values = dict(sample_field_defaults or {})
    values.update(overrides)
    args = []
    for field in input_fields:
        if field["name"] in values:
            args.append(_sample_value(field, values[field["name"]]))
        elif field["type"] == "string":
            args.append(f'"{field["name"]}-1"')
        elif field["type"] == "double":
            args.append("0.0")
        elif field["type"] in {"int", "long"}:
            args.append("0")
        else:
            args.append("false")
    return ", ".join(args)


def _filter_test_case(definition, input_event, build_event_args):
    if not definition["filter_field"]:
        return ""
    below_threshold = (
        definition["filter_value"] - 1
        if definition["filter_operator"] in (">", ">=")
        else definition["filter_value"] + 1
    )
    filter_overrides = {definition["filter_field"]: below_threshold}
    return f"""
    @Test
    @DisplayName("Filtra los eventos que no cumplen la condicion configurada")
    void filterTest() {{
        inputTopic.pipeInput("K1", new {input_event}({build_event_args(filter_overrides)}));

        assertTrue(outputTopic.isEmpty());
    }}
"""


def _get_passthrough_topology_test(definition):
    package = definition["package"]
    project_class_prefix = definition["project_class_prefix"]
    input_event = definition["input_event"]
    output_event = definition["output_event"]
    input_topic = definition["input_topic"]
    output_topic = definition["output_topic"]
    input_fields = definition["input_fields"]
    stream_bean = f"{project_class_prefix[0].lower()}{project_class_prefix[1:]}Stream"

    def build_event_args(overrides):
        return _build_event_args(input_fields, overrides)

    filter_test = _filter_test_case(definition, input_event, build_event_args)
    event_args = build_event_args({})

    return f"""package {package}.topology;

import {package}.model.{input_event};
import {package}.model.{output_event};
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.StreamsConfig;
import org.apache.kafka.streams.TestInputTopic;
import org.apache.kafka.streams.TestOutputTopic;
import org.apache.kafka.streams.TopologyTestDriver;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.kafka.support.serializer.JsonSerde;

import java.util.Properties;

import static org.junit.jupiter.api.Assertions.*;

class {project_class_prefix}TopologyTest {{

    private TopologyTestDriver testDriver;
    private TestInputTopic<String, {input_event}> inputTopic;
    private TestOutputTopic<String, {output_event}> outputTopic;

    @BeforeEach
    void setup() {{
        StreamsBuilder builder = new StreamsBuilder();
        new {project_class_prefix}Topology().{stream_bean}(builder);

        Properties props = new Properties();
        props.put(StreamsConfig.APPLICATION_ID_CONFIG, "test-{definition['project']}");
        props.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "dummy:1234");
        props.put(StreamsConfig.DEFAULT_KEY_SERDE_CLASS_CONFIG, Serdes.String().getClass());

        testDriver = new TopologyTestDriver(builder.build(), props);

        JsonSerde<{input_event}> inputSerde = new JsonSerde<>({input_event}.class);
        JsonSerde<{output_event}> outputSerde = new JsonSerde<>({output_event}.class);

        inputTopic = testDriver.createInputTopic(
                "{input_topic}", Serdes.String().serializer(), inputSerde.serializer());
        outputTopic = testDriver.createOutputTopic(
                "{output_topic}", Serdes.String().deserializer(), outputSerde.deserializer());
    }}

    @AfterEach
    void tearDown() {{
        if (testDriver != null) {{
            testDriver.close();
        }}
    }}
{filter_test}
    @Test
    @DisplayName("Reenvia el evento sin cambios al topic de salida")
    void relaysEventUnchanged() {{
        inputTopic.pipeInput("K1", new {input_event}({event_args}));

        {output_event} expected = new {output_event}({event_args});
        assertEquals(expected, outputTopic.readValue());
    }}

    @Test
    @DisplayName("Ignora los tombstones (valor nulo)")
    void tombstoneTest() {{
        inputTopic.pipeInput("K1", null);

        assertTrue(outputTopic.isEmpty());
    }}
}}
"""


def get_topology_test(definition, state_store_name):
    if definition["group_by_field"] is None:
        return _get_passthrough_topology_test(definition)

    package = definition["package"]
    project_class_prefix = definition["project_class_prefix"]
    input_event = definition["input_event"]
    output_event = definition["output_event"]
    input_topic = definition["input_topic"]
    output_topic = definition["output_topic"]
    input_fields = definition["input_fields"]
    group_by_camel = next(
        f["camel_name"] for f in input_fields if f["name"] == definition["group_by_field"]
    )
    group_by_getter = f"get{_pascal_case(group_by_camel)}"
    aggregate_as_getter = f"get{_pascal_case(to_camel_case(definition['aggregate_as']))}"

    sample_field_defaults = {
        definition["group_by_field"]: "C1",
        definition["aggregate_field"]: 50.0,
    }

    def build_event_args(overrides):
        return _build_event_args(input_fields, overrides, sample_field_defaults)

    stream_bean = f"{project_class_prefix[0].lower()}{project_class_prefix[1:]}Stream"

    filter_test = _filter_test_case(definition, input_event, build_event_args)

    return f"""package {package}.topology;

import {package}.model.{input_event};
import {package}.model.{output_event};
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.*;
import org.apache.kafka.streams.state.KeyValueStore;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.kafka.support.serializer.JsonSerde;

import java.util.Properties;

import static org.junit.jupiter.api.Assertions.*;

class {project_class_prefix}TopologyTest {{

    private TopologyTestDriver testDriver;
    private TestInputTopic<String, {input_event}> inputTopic;
    private TestOutputTopic<String, {output_event}> outputTopic;
    private KeyValueStore<String, Double> stateStore;

    @BeforeEach
    void setup() {{
        StreamsBuilder builder = new StreamsBuilder();
        new {project_class_prefix}Topology().{stream_bean}(builder);

        Properties props = new Properties();
        props.put(StreamsConfig.APPLICATION_ID_CONFIG, "test-{definition['project']}");
        props.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "dummy:1234");
        props.put(StreamsConfig.DEFAULT_KEY_SERDE_CLASS_CONFIG, Serdes.String().getClass());
        props.put(StreamsConfig.DEFAULT_VALUE_SERDE_CLASS_CONFIG, Serdes.Double().getClass());

        testDriver = new TopologyTestDriver(builder.build(), props);

        JsonSerde<{input_event}> inputSerde = new JsonSerde<>({input_event}.class);
        JsonSerde<{output_event}> outputSerde = new JsonSerde<>({output_event}.class);

        inputTopic = testDriver.createInputTopic(
                "{input_topic}", Serdes.String().serializer(), inputSerde.serializer());
        outputTopic = testDriver.createOutputTopic(
                "{output_topic}", Serdes.String().deserializer(), outputSerde.deserializer());
        stateStore = testDriver.getKeyValueStore("{state_store_name}");
    }}

    @AfterEach
    void tearDown() {{
        if (testDriver != null) {{
            testDriver.close();
        }}
    }}
{filter_test}
    @Test
    @DisplayName("Agrega correctamente el total para una misma clave")
    void aggregationTest() {{
        inputTopic.pipeInput("K1", new {input_event}({build_event_args({})}));
        {output_event} first = outputTopic.readValue();
        assertEquals(50.0, first.{aggregate_as_getter}());

        inputTopic.pipeInput("K2", new {input_event}({build_event_args({definition['aggregate_field']: 30.0})}));
        {output_event} second = outputTopic.readValue();
        assertEquals(80.0, second.{aggregate_as_getter}());

        assertEquals(80.0, stateStore.get("C1"));
    }}

    @Test
    @DisplayName("Mantiene totales independientes por clave")
    void multiKeyTest() {{
        inputTopic.pipeInput("K1", new {input_event}({build_event_args({})}));
        inputTopic.pipeInput(
                "K2", new {input_event}({build_event_args({definition['group_by_field']: 'C2', definition['aggregate_field']: 200.0})}));
        outputTopic.readValuesToList();

        inputTopic.pipeInput("K3", new {input_event}({build_event_args({definition['aggregate_field']: 25.0})}));
        {output_event} last = outputTopic.readValue();

        assertEquals("C1", last.{group_by_getter}());
        assertEquals(75.0, last.{aggregate_as_getter}());
    }}

    @Test
    @DisplayName("Asigna la clave UNKNOWN cuando el campo de agrupacion es null")
    void nullGroupByKeyTest() {{
        inputTopic.pipeInput("K1", new {input_event}({build_event_args({definition['group_by_field']: None})}));

        assertNotNull(stateStore.get("UNKNOWN"));
    }}

    @Test
    @DisplayName("Ignora los tombstones (valor nulo)")
    void tombstoneTest() {{
        inputTopic.pipeInput("K1", null);

        assertTrue(outputTopic.isEmpty());
    }}
}}
"""
