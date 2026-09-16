# Logging

Use Lombok `@Slf4j` in generated Java code rather than hand-written logger instances.

## Levels

- `INFO` for meaningful business/application milestones worth tracing.
- `WARN` / `ERROR` when something has gone wrong and the event is actionable.
- Avoid noisy logs for ordinary control flow.

## Message shape

Keep log messages structured and consistent, for example:

```java
log.info("[TASK] - ACTION: create: id: {}", task.getId());
```

Use `{}` placeholders, never string concatenation.

## Rules

- Include correlation/request identifiers when the generated architecture supports them.
- Never log passwords, tokens, authorization headers, secrets, or sensitive payload data.
- Prefer logging in the service/application layer.
- Do not log an exception at the throw site if the global exception handler will log it; one failure should normally produce one useful log event.
