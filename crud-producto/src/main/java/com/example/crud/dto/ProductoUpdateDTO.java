package com.example.crud.dto;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class ProductoUpdateDTO {
    private String nombre;
    private Float precio;
}
