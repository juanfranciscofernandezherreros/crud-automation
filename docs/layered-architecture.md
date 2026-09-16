# Layered architecture

Each generated feature is one package split into layers.

| Layer | Responsibility | May import | Must not |
| --- | --- | --- | --- |
| controller | Bind/validate HTTP, call one service operation, map response, set status | service, dto, mapper, model | repository/entity, business branching, existence checks |
| service | Business logic, transactions, not-found/uniqueness checks, pagination/orchestration | repository, model, mapper, other feature services | controllers, another feature's repository/entity |
| repository | Persistence through Spring Data | entity | hand-written CRUD implementations or business logic |
| model | In-memory domain/application representation | Lombok, other model types | JPA, Spring, DTOs |
| entity | Database row mapping | JPA, Lombok | business behaviour, controller exposure |
| dto | Wire contract | validation annotations as required | divergence from the intended API contract |
| mapper | Copy between representations | mapped source/target types | services, repositories, I/O |

## Request flow

```text
POST /<feature>
  Controller(Create<Feature>DTO)
    -> <Feature>Mapper.toModel(dto)
    -> <Feature>Service.create(model)
        -> <Feature>EntityMapper.toEntity(model)
        -> repository.save(entity)
        -> <Feature>EntityMapper.toModel(saved)
    -> <Feature>Mapper.toDto(model)
```

Paged reads pass `Pageable` from controller to service. The service returns `Page<Model>` and the controller maps it to the API response/envelope required by the generated contract.

## Feature boundaries

- Everyone depends on a feature's service interface, never directly on its implementation.
- `findById(...).orElseThrow(...)` and similar not-found behaviour belong in the service.
- `model/` remains framework-free.
- `entity/` remains persistence-only.
- One feature may call another feature's service and use its public DTO/model types when intentionally exposed.
- A feature must never reach into another feature's repository or entity package directly.
