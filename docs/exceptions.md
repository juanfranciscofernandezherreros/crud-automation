# Exceptions

Prefer one domain/application exception type carrying a stable error-code enum rather than generating one exception class per failure mode.

Example:

```java
throw new AppException(AppErrorMessage.TASK_NOT_FOUND);
```

All application exceptions should flow through one global handler using `@ControllerAdvice` / `@RestControllerAdvice` plus `@ExceptionHandler` methods. The handler maps exceptions to HTTP status codes and the project's standard error response.

## Rules

- Do not add local `@ExceptionHandler` methods to feature controllers.
- Not-found, uniqueness, and business guard failures are service concerns.
- Code that throws a domain exception should not also log the same failure.
- Log the exception once in the global handler when logging is appropriate.
- Keep the error response stable and suitable for API clients; do not expose stack traces or sensitive internal details.
