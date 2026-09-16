# Spring and Lombok annotations

Use annotations intentionally and keep them in the layer that owns the concern.

## Lombok

- `@RequiredArgsConstructor` for constructor injection.
- `@Slf4j` for logging.
- `@Builder(setterPrefix = "with")` when an object benefits from a builder.
- Avoid `@Data`; prefer `@Getter` / `@Setter` explicitly.
- Model POJOs may use `@Getter`, `@Setter`, `@NoArgsConstructor`, `@AllArgsConstructor`, and `@Builder(setterPrefix = "with")`.
- Entity classes may use the same Lombok annotations plus JPA annotations, but must not contain business behaviour.

## Spring

- `@RestController` on HTTP controllers.
- HTTP mapping annotations at method level.
- `@Service` only on the feature implementation, e.g. `TaskServiceImpl`.
- The service interface carries no Spring annotation.
- Do not write `@Repository` on ordinary Spring Data interfaces; extending `JpaRepository` is enough.
- `@Component` for generic Spring beans and `@Configuration` for configuration classes.
- Production dependency injection is constructor-based. Field injection is reserved for tests.
- Prefer `@ConfigurationProperties` when binding three or more related properties; a small number of isolated properties may use `@Value`.
- Put `@Transactional` on service classes, not controllers or repositories. Prefer `readOnly = true` for read-only service implementations/paths where the selected design allows it.
- Use `@Validated` for method/class validation and `@RequestBody @Valid` for validated write DTOs.
- `@PreAuthorize` belongs at the controller/application boundary when method security is enabled.

Keep dependencies acyclic. Do not use `@Order` to hide dependency-resolution problems.
