package com.example.crud.controller;

import com.example.crud.dto.*;
import com.example.crud.service.ProductoService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;
import java.net.URI;

@RestController
@RequestMapping("/api/productos")
@RequiredArgsConstructor
@Tag(name = "Producto", description = "API CRUD para Producto")
public class ProductoController {

    private final ProductoService service;

    @PostMapping
    @Operation(summary = "Crear producto")
    public ResponseEntity<ProductoResponseDTO> create(@Valid @RequestBody ProductoCreateDTO dto) {
        ProductoResponseDTO created = service.create(dto);
        URI location = ServletUriComponentsBuilder.fromCurrentRequest().path("/{id}").buildAndExpand(created.getId()).toUri();
        return ResponseEntity.created(location).body(created);
    }

    @GetMapping
    @Operation(summary = "Listar productos")
    public ResponseEntity<Page<ProductoResponseDTO>> findAll(Pageable pageable) {
        return ResponseEntity.ok(service.findAll(pageable));
    }

    @GetMapping("/{id}")
    @Operation(summary = "Obtener por ID")
    public ResponseEntity<ProductoResponseDTO> findById(@PathVariable Integer id) {
        return ResponseEntity.ok(service.findById(id));
    }

    @PutMapping("/{id}")
    @Operation(summary = "Actualización completa")
    public ResponseEntity<ProductoResponseDTO> update(@PathVariable Integer id, @Valid @RequestBody ProductoUpdateDTO dto) {
        return ResponseEntity.ok(service.update(id, dto));
    }

    @PatchMapping("/{id}")
    @Operation(summary = "Actualización parcial")
    public ResponseEntity<ProductoResponseDTO> patch(@PathVariable Integer id, @Valid @RequestBody ProductoPatchDTO dto) {
        return ResponseEntity.ok(service.patch(id, dto));
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Eliminar producto")
    public ResponseEntity<Void> delete(@PathVariable Integer id) {
        service.delete(id);
        return ResponseEntity.noContent().build();
    }
}
