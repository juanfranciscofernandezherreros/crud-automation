# Controllers

Controllers are the HTTP edge only: bind/validate, map request DTO to model, call the service, map the result to a response DTO, and set the HTTP status.

Do not put business logic, repository access, existence checks, or local exception handlers in controllers.

## Mapping flow

Keep each step separate and assigned to a `var`:

```java
@PostMapping
@ResponseStatus(HttpStatus.CREATED)
public TaskDTO createTask(@RequestBody @Valid CreateTaskDTO dto) {
    var task = TaskMapper.toModel(dto);
    var created = taskService.create(task);
    var response = TaskMapper.toDto(created);

    return response;
}
```

Avoid nesting mapper and service calls:

```java
return TaskMapper.toDto(taskService.create(TaskMapper.toModel(dto)));
```

## Query parameters and paging

- One or two filter values may be individual `@RequestParam`s.
- Three or more related filters should be grouped into an object bound with `@ModelAttribute`.
- Paged endpoints accept a `Pageable` and return the project's standard list/paging envelope.
- Prefer handler/service names beginning with `search...` for paged search endpoints.

## Status codes

- Create: `201 CREATED`.
- Delete: `204 NO_CONTENT`.
- Successful reads/updates default to `200 OK` unless the API contract says otherwise.
