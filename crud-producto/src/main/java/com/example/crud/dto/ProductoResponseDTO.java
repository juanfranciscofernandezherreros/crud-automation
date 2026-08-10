package com.example.crud.dto;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class ProductoResponseDTO {
    private Integer id;
    private String nombre;
    private Float precio;
}
