package com.example.crud.service;

import com.example.crud.dto.ProductoCreateDTO;
import com.example.crud.dto.ProductoResponseDTO;
import com.example.crud.entity.Producto;
import com.example.crud.exception.ResourceNotFoundException;
import com.example.crud.mapper.ProductoMapper;
import com.example.crud.repository.ProductoRepository;
import com.example.crud.service.impl.ProductoServiceImpl;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class ProductoServiceTest {

    @Mock
    private ProductoRepository repository;

    @Mock
    private ProductoMapper mapper;

    @InjectMocks
    private ProductoServiceImpl service;

    private Producto entity;
    private ProductoResponseDTO responseDTO;

    @BeforeEach
    void setUp() {
        entity = new Producto();
        responseDTO = new ProductoResponseDTO();
    }

    @Test
    void create_ReturnsResponseDTO() {
        ProductoCreateDTO createDTO = new ProductoCreateDTO();
        
        when(mapper.toEntity(any(ProductoCreateDTO.class))).thenReturn(entity);
        when(repository.save(any(Producto.class))).thenReturn(entity);
        when(mapper.toDto(any(Producto.class))).thenReturn(responseDTO);

        ProductoResponseDTO result = service.create(createDTO);

        assertNotNull(result);
        verify(repository).save(any(Producto.class));
    }

    @Test
    void findById_ExistingId_ReturnsResponseDTO() {
        when(repository.findById(1)).thenReturn(Optional.of(entity));
        when(mapper.toDto(entity)).thenReturn(responseDTO);

        ProductoResponseDTO result = service.findById(1);

        assertNotNull(result);
    }

    @Test
    void findById_NonExistingId_ThrowsException() {
        when(repository.findById(99)).thenReturn(Optional.empty());

        assertThrows(ResourceNotFoundException.class, () -> service.findById(99));
    }
}
