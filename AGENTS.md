# crud-automation — Agent Guidelines

These instructions apply to agents working on this repository.

> Important: `crud-automation` itself is a Python generator. The Java/Spring rules below apply to generated Spring Boot code, Java templates, fixtures, examples, and changes that define the generated architecture. They do **not** replace the existing conventions of the Python generator.

Also read `CLAUDE.md` for repository-specific commit/reporting rules.

## Spring Boot standards

Detailed rules:

- [`docs/java-style.md`](docs/java-style.md)
- [`docs/annotations.md`](docs/annotations.md)
- [`docs/layered-architecture.md`](docs/layered-architecture.md)
- [`docs/controllers.md`](docs/controllers.md)
- [`docs/mappers.md`](docs/mappers.md)
- [`docs/exceptions.md`](docs/exceptions.md)
- [`docs/testing.md`](docs/testing.md)
- [`docs/logging.md`](docs/logging.md)

## Agent workflow

Before modifying or generating Spring Boot code:

1. Read this file completely.
2. Read the relevant files under `docs/`.
3. Inspect the generator's existing architecture and templates before creating new conventions.
4. Do not introduce new dependencies unless required by the requested feature.
5. Keep generated code consistent across generator templates, examples, tests, and documentation.
6. Do not silently change public CLI behaviour, generated API contracts, database schemas, or package layout.
7. Update or add generator tests whenever generation behaviour changes.
8. Run the smallest relevant Python test set first, then the full suite when practical.
9. For generated Java projects, run formatting and Java tests when the test fixture/build supports it.

## Target Spring architecture

For generated CRUD-style Spring Boot services, prefer one package per feature:

```text
com/<company>/<app>/<feature>/
  controller/   <Feature>Controller
  service/      <Feature>Service
                <Feature>ServiceImpl
  repository/   <Feature>Repository
  model/        <Feature>, enums
  entity/       <Feature>Entity
  dto/          Create/Update/Response DTOs
  mapper/       <Feature>Mapper
                <Feature>EntityMapper
```

Only generate layers that are actually needed.

## Core rules

- Service = interface plus one `@Service` implementation. Depend on and mock the interface; unit-test the implementation.
- Repository = Spring Data interface. Do not generate hand-written repository implementations for ordinary CRUD.
- `model/` contains framework-free POJOs. It must not import `jakarta.persistence`.
- `entity/` contains persistence mapping only and no business behaviour.
- Controllers bind/validate, map, call one service operation, and map the response. No repository access or business rules.
- `@Transactional` belongs on service classes. Use read-only transactions for read-only services/implementations where appropriate.
- Do not use `final` on Java method parameters or local variables. Constructor-injected Lombok fields may remain `final`.
- Prefer `var` for controller/test locals and explicit types in services and mappers.
- Keep mapping statements separate from service calls so generated code remains easy to debug.
- Domain exceptions are handled centrally by a global exception handler; do not duplicate logging at throw sites.

## Version compatibility

Do not blindly hard-code Java or Spring Boot versions from this file. Use the versions selected by the generator architecture/profile being modified. When adding a new architecture targeting Java 25 / Spring Boot 4.x, apply these conventions directly and verify dependency compatibility.
