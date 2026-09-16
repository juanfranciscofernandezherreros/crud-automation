# Java style

Use 4-space indentation, UTF-8, a 120-character line target, and the project formatter. Generated projects should include an automated formatting check whenever the selected architecture supports it.

Prefer a formatter enforced in CI rather than relying on manual review. For Maven projects, Spotless with Palantir Java Format is a good default when compatible with the selected Java version.

## Conventions

- No `final` on method parameters or local variables.
- `final` is allowed on constructor-injected fields used by Lombok `@RequiredArgsConstructor`.
- Use `var` in controllers and tests.
- Use explicit types in services, mappers, and the rest of production code.
- Prefer immutability where practical.
- Avoid magic values; extract meaningful constants.
- Prefer early returns over deep nesting.
- For compound conditions, extract a named boolean when it improves readability.
- Use `@Override` whenever applicable.
- Avoid wildcard imports.
- Avoid unnecessary Javadocs and comments. Comments are appropriate for non-obvious cron expressions, regexes, TODOs, and `given/when/then` test sections.
- Prefer unchecked/domain exceptions over declaring checked `throws` clauses for application-level failures.
- For one or two null checks, `value == null` / `value != null` is clearer than `Objects.isNull` / `Objects.nonNull`.
- Keep methods and constructors small. When several parameters form one concept, prefer a record/value object rather than a long parameter list.

## Formatting

Generated code should leave blank lines between logical blocks. Keep mapping, service calls, and return statements easy to scan and debug.
