package com.example.crud.controller;

import com.example.crud.dto.ProductoCreateDTO;
import com.example.crud.dto.ProductoResponseDTO;
import com.example.crud.service.ProductoService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.ArgumentMatchers.any;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(ProductoController.class)
class ProductoControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private ProductoService service;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void create_ValidInput_Returns201() throws Exception {
        ProductoCreateDTO createDTO = new ProductoCreateDTO();
        ProductoResponseDTO responseDTO = new ProductoResponseDTO();

        Mockito.when(service.create(any(ProductoCreateDTO.class))).thenReturn(responseDTO);

        mockMvc.perform(post("/api/productos")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(createDTO)))
                .andExpect(status().isCreated());
    }

    @Test
    void findById_ExistingId_Returns200() throws Exception {
        ProductoResponseDTO responseDTO = new ProductoResponseDTO();
        
        Mockito.when(service.findById(1)).thenReturn(responseDTO);

        mockMvc.perform(get("/api/productos/1")
                .contentType(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk());
    }
}
