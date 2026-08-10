package com.example.crud.mapper;

import com.example.crud.dto.*;
import com.example.crud.entity.Producto;
import org.mapstruct.BeanMapping;
import org.mapstruct.Mapper;
import org.mapstruct.MappingTarget;
import org.mapstruct.NullValuePropertyMappingStrategy;

@Mapper(componentModel = "spring")
public interface ProductoMapper {
    Producto toEntity(ProductoCreateDTO dto);
    Producto toEntity(ProductoUpdateDTO dto);
    ProductoResponseDTO toDto(Producto entity);

    @BeanMapping(nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
    void updateEntityFromPatchDto(ProductoPatchDTO dto, @MappingTarget Producto entity);
    
    void updateEntityFromUpdateDto(ProductoUpdateDTO dto, @MappingTarget Producto entity);
}
