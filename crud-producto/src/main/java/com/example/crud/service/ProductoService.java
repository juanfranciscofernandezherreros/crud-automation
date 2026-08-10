package com.example.crud.service;

import com.example.crud.dto.*;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;

public interface ProductoService {
    ProductoResponseDTO create(ProductoCreateDTO createDTO);
    Page<ProductoResponseDTO> findAll(Pageable pageable);
    ProductoResponseDTO findById(Integer id);
    ProductoResponseDTO update(Integer id, ProductoUpdateDTO updateDTO);
    ProductoResponseDTO patch(Integer id, ProductoPatchDTO patchDTO);
    void delete(Integer id);
}
