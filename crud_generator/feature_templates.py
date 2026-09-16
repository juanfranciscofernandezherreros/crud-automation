"""Plantillas de la arquitectura feature-based alineada con las reglas de AGENTS.md."""

from . import shared_templates
from .parsing import pluralize


def get_model(entity_name, package, fields, include_all_args_builder=True):
    constructor_annotations = (
        "@AllArgsConstructor\n@Builder(setterPrefix = \"with\")\n"
        if include_all_args_builder
        else ""
    )
    return f"""package {package};

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import lombok.AllArgsConstructor;
import lombok.Builder;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Getter
@Setter
@NoArgsConstructor
{constructor_annotations}public class {entity_name} {{
{fields}
}}
"""


def get_entity(
    entity_name,
    entity_lower,
    package,
    fields,
    unique_constraints_annotation="",
    dynamic_insert=False,
    include_all_args_builder=True,
    enum_import_lines="",
    has_inverse_relations=False,
):
    return shared_templates.render_jpa_entity_class(
        package,
        f"{entity_name}Entity",
        entity_lower,
        fields,
        unique_constraints_annotation,
        dynamic_insert,
        include_all_args_builder,
        enum_import_lines,
        has_inverse_relations,
    )


def get_dto(class_name, package, fields, enum_import_lines=""):
    return shared_templates.render_dto_class(package, class_name, fields, enum_import_lines)


def get_repository(entity_name, feature_package):
    return f"""package {feature_package}.repository;

import {feature_package}.entity.{entity_name}Entity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;

public interface {entity_name}Repository
        extends JpaRepository<{entity_name}Entity, Integer>, JpaSpecificationExecutor<{entity_name}Entity> {{
}}
"""


def get_specification(entity_name, feature_package, filter_cases):
    return f"""package {feature_package}.repository;

import {feature_package}.entity.{entity_name}Entity;
import org.springframework.data.jpa.domain.Specification;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.Map;

public final class {entity_name}Specifications {{

    private {entity_name}Specifications() {{
        throw new UnsupportedOperationException("Utility class");
    }}

    public static Specification<{entity_name}Entity> fromFilters(Map<String, String> filters) {{
        Specification<{entity_name}Entity> spec = Specification.where(null);

        for (Map.Entry<String, String> entry : filters.entrySet()) {{
            String value = entry.getValue();
            if (value == null || value.isBlank()) {{
                continue;
            }}

            switch (entry.getKey()) {{
{filter_cases}
                default -> {{ }}
            }}
        }}

        return spec;
    }}
}}
"""


def get_web_mapper(entity_name, feature_package):
    return f"""package {feature_package}.mapper;

import {feature_package}.dto.*;
import {feature_package}.model.{entity_name};
import org.mapstruct.BeanMapping;
import org.mapstruct.Mapper;
import org.mapstruct.MappingTarget;
import org.mapstruct.NullValuePropertyMappingStrategy;

@Mapper(componentModel = "spring")
public interface {entity_name}Mapper {{

    {entity_name} toModel({entity_name}CreateDTO dto);

    {entity_name} toModel({entity_name}UpdateDTO dto);

    {entity_name} toModel({entity_name}PatchDTO dto);

    {entity_name}ResponseDTO toDto({entity_name} model);

    @BeanMapping(nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
    void patchModel({entity_name} changes, @MappingTarget {entity_name} target);
}}
"""


def get_entity_mapper(entity_name, feature_package, reference_attrs=None):
    reference_attrs = reference_attrs or []
    suffix = shared_templates.capitalize_first

    ignore_lines = "\n".join(
        f'    @Mapping(target = "{attr["camel_name"]}", ignore = true)'
        for attr in reference_attrs
    )
    ignore_block = f"{ignore_lines}\n" if ignore_lines else ""

    model_lines = "\n".join(
        f'    @Mapping(target = "{attr["camel_name"]}Id", '
        f'expression = "java(entity.get{suffix(attr["camel_name"])}() != null ? '
        f'entity.get{suffix(attr["camel_name"])}().getId() : null)")'
        for attr in reference_attrs
    )
    model_block = f"{model_lines}\n" if model_lines else ""
    mapping_import = "\nimport org.mapstruct.Mapping;" if reference_attrs else ""

    protected_fields = """    @Mapping(target = "id", ignore = true)
    @Mapping(target = "version", ignore = true)
"""

    return f"""package {feature_package}.mapper;

import {feature_package}.entity.{entity_name}Entity;
import {feature_package}.model.{entity_name};
import org.mapstruct.BeanMapping;
import org.mapstruct.Mapper;{mapping_import}
import org.mapstruct.MappingTarget;
import org.mapstruct.NullValuePropertyMappingStrategy;

@Mapper(componentModel = "spring")
public interface {entity_name}EntityMapper {{

{ignore_block}    {entity_name}Entity toEntity({entity_name} model);

{model_block}    {entity_name} toModel({entity_name}Entity entity);

{protected_fields}{ignore_block}    void updateEntity({entity_name} model, @MappingTarget {entity_name}Entity entity);

    @BeanMapping(nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
{protected_fields}{ignore_block}    void patchEntity({entity_name} model, @MappingTarget {entity_name}Entity entity);
}}
"""


def get_service_interface(entity_name, feature_package):
    return f"""package {feature_package}.service;

import {feature_package}.model.{entity_name};
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import java.util.Map;

public interface {entity_name}Service {{

    {entity_name} create({entity_name} model);

    Page<{entity_name}> search(Pageable pageable, Map<String, String> filters);

    {entity_name} findById(Integer id);

    {entity_name} update(Integer id, {entity_name} model);

    {entity_name} patch(Integer id, {entity_name} model);

    void delete(Integer id);
}}
"""


def _reference_blocks(reference_attrs, base_package):
    reference_attrs = reference_attrs or []
    imports = []
    fields = []
    resolvers = []
    create_calls = []
    update_calls = []
    patch_calls = []

    for attr in reference_attrs:
        referenced = attr["references"]
        referenced_lower = referenced.lower()
        field = attr["camel_name"]
        suffix = shared_templates.capitalize_first(field)
        imports.extend([
            f"import {base_package}.{referenced_lower}.entity.{referenced}Entity;",
            f"import {base_package}.{referenced_lower}.repository.{referenced}Repository;",
        ])
        fields.append(f"    private final {referenced}Repository {field}Repository;")
        resolvers.append(
            f"""    private {referenced}Entity resolve{suffix}(Integer id) {{
        if (id == null) {{
            return null;
        }}

        return {field}Repository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("{referenced} no encontrado: " + id));
    }}"""
        )
        create_calls.append(f"        entity.set{suffix}(resolve{suffix}(model.get{suffix}Id()));")
        update_calls.append(f"        entity.set{suffix}(resolve{suffix}(model.get{suffix}Id()));")
        patch_calls.append(
            f"""        if (model.get{suffix}Id() != null) {{
            entity.set{suffix}(resolve{suffix}(model.get{suffix}Id()));
        }}"""
        )

    return (
        "\n".join(imports),
        "\n".join(fields),
        "\n\n".join(resolvers),
        "\n".join(create_calls),
        "\n".join(update_calls),
        "\n".join(patch_calls),
    )


def get_service_impl(entity_name, feature_package, base_package, reference_attrs=None):
    (
        reference_imports,
        reference_fields,
        resolvers,
        create_calls,
        update_calls,
        patch_calls,
    ) = _reference_blocks(reference_attrs, base_package)

    reference_imports_block = f"{reference_imports}\n" if reference_imports else ""
    reference_fields_block = f"\n{reference_fields}" if reference_fields else ""
    create_block = f"\n{create_calls}" if create_calls else ""
    update_block = f"\n{update_calls}" if update_calls else ""
    patch_block = f"\n{patch_calls}" if patch_calls else ""
    resolvers_block = f"\n\n{resolvers}" if resolvers else ""

    return f"""package {feature_package}.service;

import {feature_package}.entity.{entity_name}Entity;
import {feature_package}.mapper.{entity_name}EntityMapper;
import {feature_package}.model.{entity_name};
import {feature_package}.repository.{entity_name}Repository;
import {feature_package}.repository.{entity_name}Specifications;
import {base_package}.exception.ResourceNotFoundException;
{reference_imports_block}import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Transactional
public class {entity_name}ServiceImpl implements {entity_name}Service {{

    private final {entity_name}Repository repository;
    private final {entity_name}EntityMapper entityMapper;{reference_fields_block}

    @Override
    public {entity_name} create({entity_name} model) {{
        {entity_name}Entity entity = entityMapper.toEntity(model);{create_block}
        {entity_name}Entity saved = repository.save(entity);

        return entityMapper.toModel(saved);
    }}

    @Override
    @Transactional(readOnly = true)
    public Page<{entity_name}> search(Pageable pageable, Map<String, String> filters) {{
        return repository.findAll({entity_name}Specifications.fromFilters(filters), pageable)
                .map(entityMapper::toModel);
    }}

    @Override
    @Transactional(readOnly = true)
    public {entity_name} findById(Integer id) {{
        {entity_name}Entity entity = getEntity(id);

        return entityMapper.toModel(entity);
    }}

    @Override
    public {entity_name} update(Integer id, {entity_name} model) {{
        {entity_name}Entity entity = getEntity(id);
        entityMapper.updateEntity(model, entity);{update_block}
        {entity_name}Entity saved = repository.save(entity);

        return entityMapper.toModel(saved);
    }}

    @Override
    public {entity_name} patch(Integer id, {entity_name} model) {{
        {entity_name}Entity entity = getEntity(id);
        entityMapper.patchEntity(model, entity);{patch_block}
        {entity_name}Entity saved = repository.save(entity);

        return entityMapper.toModel(saved);
    }}

    @Override
    public void delete(Integer id) {{
        {entity_name}Entity entity = getEntity(id);
        repository.delete(entity);
    }}

    private {entity_name}Entity getEntity(Integer id) {{
        return repository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("{entity_name} no encontrado con ID: " + id));
    }}{resolvers_block}
}}
"""


def get_controller(entity_name, entity_lower, feature_package):
    return f"""package {feature_package}.controller;

import {feature_package}.dto.*;
import {feature_package}.mapper.{entity_name}Mapper;
import {feature_package}.model.{entity_name};
import {feature_package}.service.{entity_name}Service;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import java.util.Map;

@RestController
@RequestMapping("/api/{pluralize(entity_lower)}")
@RequiredArgsConstructor
public class {entity_name}Controller {{

    private final {entity_name}Service service;
    private final {entity_name}Mapper mapper;

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public {entity_name}ResponseDTO create(@RequestBody @Valid {entity_name}CreateDTO dto) {{
        var model = mapper.toModel(dto);
        var created = service.create(model);

        return mapper.toDto(created);
    }}

    @GetMapping
    public Page<{entity_name}ResponseDTO> search(Pageable pageable, @RequestParam Map<String, String> filters) {{
        var result = service.search(pageable, filters);

        return result.map(mapper::toDto);
    }}

    @GetMapping("/{id}")
    public {entity_name}ResponseDTO findById(@PathVariable Integer id) {{
        var model = service.findById(id);

        return mapper.toDto(model);
    }}

    @PutMapping("/{id}")
    public {entity_name}ResponseDTO update(
            @PathVariable Integer id,
            @RequestBody @Valid {entity_name}UpdateDTO dto) {{
        var model = mapper.toModel(dto);
        var updated = service.update(id, model);

        return mapper.toDto(updated);
    }}

    @PatchMapping("/{id}")
    public {entity_name}ResponseDTO patch(
            @PathVariable Integer id,
            @RequestBody @Valid {entity_name}PatchDTO dto) {{
        var model = mapper.toModel(dto);
        var updated = service.patch(id, model);

        return mapper.toDto(updated);
    }}

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable Integer id) {{
        service.delete(id);
    }}
}}
"""


def get_service_test(entity_name, feature_package):
    return f"""package {feature_package}.service;

import {feature_package}.entity.{entity_name}Entity;
import {feature_package}.mapper.{entity_name}EntityMapper;
import {feature_package}.model.{entity_name};
import {feature_package}.repository.{entity_name}Repository;
import {base_exception_import(feature_package)}
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class {entity_name}ServiceTest {{

    @Mock
    private {entity_name}Repository repository;

    @Mock
    private {entity_name}EntityMapper entityMapper;

    @InjectMocks
    private {entity_name}ServiceImpl service;

    @Test
    void find_by_id_ok() {{
        // given
        var entity = new {entity_name}Entity();
        var model = new {entity_name}();
        when(repository.findById(1)).thenReturn(Optional.of(entity));
        when(entityMapper.toModel(entity)).thenReturn(model);

        // when
        var result = service.findById(1);

        // then
        assertThat(result).isSameAs(model);
    }}

    @Test
    void find_by_id_ko() {{
        // given
        when(repository.findById(1)).thenReturn(Optional.empty());

        // when / then
        assertThatThrownBy(() -> service.findById(1))
                .isInstanceOf(RuntimeException.class);
        verify(repository, never()).save(any());
    }}
}}
"""


def base_exception_import(feature_package):
    root = feature_package.rsplit(".", 1)[0]
    return f"import {root}.exception.ResourceNotFoundException;"
