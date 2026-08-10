package com.example.crud.service.impl;

import com.example.crud.dto.*;
import com.example.crud.entity.Producto;
import com.example.crud.exception.ResourceNotFoundException;
import com.example.crud.mapper.ProductoMapper;
import com.example.crud.repository.ProductoRepository;
import com.example.crud.service.ProductoService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class ProductoServiceImpl implements ProductoService {

    private final ProductoRepository repository;
    private final ProductoMapper mapper;

    @Override
    @Transactional
    public ProductoResponseDTO create(ProductoCreateDTO createDTO) {
        Producto entity = mapper.toEntity(createDTO);
        return mapper.toDto(repository.save(entity));
    }

    @Override
    @Transactional(readOnly = true)
    public Page<ProductoResponseDTO> findAll(Pageable pageable) {
        return repository.findAll(pageable).map(mapper::toDto);
    }

    @Override
    @Transactional(readOnly = true)
    public ProductoResponseDTO findById(Integer id) {
        return mapper.toDto(getEntity(id));
    }

    @Override
    @Transactional
    public ProductoResponseDTO update(Integer id, ProductoUpdateDTO updateDTO) {
        Producto entity = getEntity(id);
        mapper.updateEntityFromUpdateDto(updateDTO, entity);
        return mapper.toDto(repository.save(entity));
    }

    @Override
    @Transactional
    public ProductoResponseDTO patch(Integer id, ProductoPatchDTO patchDTO) {
        Producto entity = getEntity(id);
        mapper.updateEntityFromPatchDto(patchDTO, entity);
        return mapper.toDto(repository.save(entity));
    }

    @Override
    @Transactional
    public void delete(Integer id) {
        repository.delete(getEntity(id));
    }

    private Producto getEntity(Integer id) {
        return repository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Producto no encontrado con ID: " + id));
    }
}
