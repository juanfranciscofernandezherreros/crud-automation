# Mappers

Choose one mapping strategy per generated architecture and keep it consistent.

## Static mappers

For simple generated CRUD code, static mappers are preferred unless the architecture explicitly selects MapStruct.

Use two mapping boundaries per feature:

| Mapper | Converts | Used by |
| --- | --- | --- |
| `<Feature>Mapper` | DTO <-> model | controller |
| `<Feature>EntityMapper` | model <-> entity | service |

Static mapper classes should be `public final` with a private constructor that prevents instantiation.

```java
public final class TaskMapper {
    private TaskMapper() {
        throw new UnsupportedOperationException("This class should never be instantiated");
    }
}
```

Mapper methods:

- Use direction-obvious names such as `toModel`, `toDto`, `toEntity`, `fromCreateDto`, `fromUpdateDto`.
- Guard `null` inputs where the generated API allows them.
- Use explicit local types in mapper code.
- Keep builders/mapping expressions readable rather than embedding them inside service/repository calls.
- Never perform I/O or call services/repositories.

## MapStruct

When the generated architecture opts into MapStruct, use `@Mapper(componentModel = "spring")` and explicit `@Mapping` declarations for fields whose names differ. Mapper naming and layer boundaries stay the same.

In unit tests, `Mappers.getMapper(...)` may be used when a Spring context is unnecessary.
