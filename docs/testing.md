# Testing

Generated Spring projects should use the test stack selected by their architecture. For modern Spring Boot projects, prefer JUnit, Mockito, and AssertJ.

## Layer strategy

- Service tests are the default because business logic lives there.
- Add `@WebMvcTest` controller tests when validation, status codes, serialization, or response shape matter.
- Add `@DataJpaTest` repository tests for custom queries, Specifications, or persistence behaviour that Spring Data itself does not already cover.
- Do not generate repository tests for plain inherited CRUD methods.

## Mockito

In a service unit test, `@InjectMocks` targets `<Feature>ServiceImpl`; Mockito cannot instantiate the service interface. Other collaborators should depend on/mock `<Feature>Service` rather than the implementation.

## Style

- Test method names use snake_case and may end with `_ok` / `_ko`, e.g. `create_task_ok` and `get_task_not_found_ko`.
- Structure tests with `// given`, `// when`, `// then`.
- Use `var` for test locals and do not add `final` to locals/parameters.
- Prefer AssertJ assertions.
- Group related assertions when useful so failures expose multiple mismatches.
- Field injection with `@Mock`, `@InjectMocks`, `@Autowired`, or Spring test equivalents is acceptable in tests.
- Keep loops/branching/business logic out of test bodies. Use small private fixture/factory helpers instead.
- One behaviour per test.

For each service operation, cover the happy path, not-found paths, relevant guard clauses, and partial-update/PATCH semantics. When a guard must prevent persistence, verify that `save` was never called.

Formatting checks and the full test suite are quality gates for generated projects when supported by the selected architecture.
