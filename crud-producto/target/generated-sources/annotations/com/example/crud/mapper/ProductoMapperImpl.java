package com.example.crud.mapper;

import com.example.crud.dto.ProductoCreateDTO;
import com.example.crud.dto.ProductoPatchDTO;
import com.example.crud.dto.ProductoResponseDTO;
import com.example.crud.dto.ProductoUpdateDTO;
import com.example.crud.entity.Producto;
import javax.annotation.processing.Generated;
import org.springframework.stereotype.Component;

@Generated(
    value = "org.mapstruct.ap.MappingProcessor",
    date = "2026-08-10T20:16:56+0200",
    comments = "version: 1.5.5.Final, compiler: javac, environment: Java 21.0.11 (Oracle Corporation)"
)
@Component
public class ProductoMapperImpl implements ProductoMapper {

    @Override
    public Producto toEntity(ProductoCreateDTO dto) {
        if ( dto == null ) {
            return null;
        }

        Producto.ProductoBuilder producto = Producto.builder();

        producto.nombre( dto.getNombre() );
        producto.precio( dto.getPrecio() );

        return producto.build();
    }

    @Override
    public Producto toEntity(ProductoUpdateDTO dto) {
        if ( dto == null ) {
            return null;
        }

        Producto.ProductoBuilder producto = Producto.builder();

        producto.nombre( dto.getNombre() );
        producto.precio( dto.getPrecio() );

        return producto.build();
    }

    @Override
    public ProductoResponseDTO toDto(Producto entity) {
        if ( entity == null ) {
            return null;
        }

        ProductoResponseDTO productoResponseDTO = new ProductoResponseDTO();

        productoResponseDTO.setId( entity.getId() );
        productoResponseDTO.setNombre( entity.getNombre() );
        productoResponseDTO.setPrecio( entity.getPrecio() );

        return productoResponseDTO;
    }

    @Override
    public void updateEntityFromPatchDto(ProductoPatchDTO dto, Producto entity) {
        if ( dto == null ) {
            return;
        }

        if ( dto.getNombre() != null ) {
            entity.setNombre( dto.getNombre() );
        }
        if ( dto.getPrecio() != null ) {
            entity.setPrecio( dto.getPrecio() );
        }
    }

    @Override
    public void updateEntityFromUpdateDto(ProductoUpdateDTO dto, Producto entity) {
        if ( dto == null ) {
            return;
        }

        entity.setNombre( dto.getNombre() );
        entity.setPrecio( dto.getPrecio() );
    }
}
