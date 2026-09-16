"""Plantillas de tests generados para la arquitectura feature-based."""

from .parsing import pluralize


def get_controller_test(entity_name, entity_lower, feature_package):
    return f"""package {feature_package}.controller;

import {feature_package}.dto.{entity_name}ResponseDTO;
import {feature_package}.mapper.{entity_name}Mapper;
import {feature_package}.model.{entity_name};
import {feature_package}.service.{entity_name}Service;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest({entity_name}Controller.class)
@AutoConfigureMockMvc(addFilters = false)
class {entity_name}ControllerTest {{

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private {entity_name}Service service;

    @MockBean
    private {entity_name}Mapper mapper;

    @Test
    void find_by_id_ok() throws Exception {{
        // given
        var model = new {entity_name}();
        var dto = new {entity_name}ResponseDTO();
        when(service.findById(1)).thenReturn(model);
        when(mapper.toDto(model)).thenReturn(dto);

        // when / then
        mockMvc.perform(get("/api/{pluralize(entity_lower)}/1"))
                .andExpect(status().isOk());
    }}
}}
"""
