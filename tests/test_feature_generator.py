"""Contrato de la arquitectura feature-based alineada con AGENTS.md."""

import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from crud_generator.feature_generator import generate_feature_project


@contextmanager
def working_directory(path):
    previous = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class FeatureGeneratorTest(unittest.TestCase):

    def test_generates_feature_package_with_model_entity_services_and_two_mappers(self):
        with tempfile.TemporaryDirectory() as tmp, working_directory(tmp):
            base_dir = generate_feature_project(
                "Producto",
                "id:int,nombre:string,precio:decimal",
            )

            project = Path(tmp) / base_dir
            java = project / "src/main/java/com/example/crud/producto"

            self.assertTrue((java / "model/Producto.java").exists())
            self.assertTrue((java / "entity/ProductoEntity.java").exists())
            self.assertTrue((java / "service/ProductoService.java").exists())
            self.assertTrue((java / "service/ProductoServiceImpl.java").exists())
            self.assertTrue((java / "mapper/ProductoMapper.java").exists())
            self.assertTrue((java / "mapper/ProductoEntityMapper.java").exists())
            self.assertTrue((java / "repository/ProductoRepository.java").exists())
            self.assertTrue((java / "controller/ProductoController.java").exists())

            self.assertFalse((java / "service/impl/ProductoServiceImpl.java").exists())
            self.assertFalse((java / "entity/Producto.java").exists())

    def test_model_is_persistence_free_and_entity_contains_jpa_mapping(self):
        with tempfile.TemporaryDirectory() as tmp, working_directory(tmp):
            base_dir = generate_feature_project("Producto", "id:int,nombre:string")
            project = Path(tmp) / base_dir
            java = project / "src/main/java/com/example/crud/producto"

            model = (java / "model/Producto.java").read_text(encoding="utf-8")
            entity = (java / "entity/ProductoEntity.java").read_text(encoding="utf-8")

            self.assertNotIn("jakarta.persistence", model)
            self.assertNotIn("@Entity", model)
            self.assertIn("@Entity", entity)
            self.assertIn("class ProductoEntity", entity)

    def test_repository_has_no_explicit_repository_annotation(self):
        with tempfile.TemporaryDirectory() as tmp, working_directory(tmp):
            base_dir = generate_feature_project("Producto", "id:int,nombre:string")
            project = Path(tmp) / base_dir
            repository = (
                project
                / "src/main/java/com/example/crud/producto/repository/ProductoRepository.java"
            ).read_text(encoding="utf-8")

            self.assertIn("JpaRepository<ProductoEntity, Integer>", repository)
            self.assertNotIn("@Repository", repository)
            self.assertNotIn("org.springframework.stereotype.Repository", repository)

    def test_service_impl_is_transactional_and_uses_explicit_types(self):
        with tempfile.TemporaryDirectory() as tmp, working_directory(tmp):
            base_dir = generate_feature_project("Producto", "id:int,nombre:string")
            project = Path(tmp) / base_dir
            service = (
                project
                / "src/main/java/com/example/crud/producto/service/ProductoServiceImpl.java"
            ).read_text(encoding="utf-8")

            self.assertIn("@Transactional\npublic class ProductoServiceImpl", service)
            self.assertIn("@Transactional(readOnly = true)", service)
            self.assertNotIn(" var ", service)

    def test_controller_uses_var_and_separates_mapping_from_service_calls(self):
        with tempfile.TemporaryDirectory() as tmp, working_directory(tmp):
            base_dir = generate_feature_project("Producto", "id:int,nombre:string")
            project = Path(tmp) / base_dir
            controller = (
                project
                / "src/main/java/com/example/crud/producto/controller/ProductoController.java"
            ).read_text(encoding="utf-8")

            self.assertIn("var model = mapper.toModel(dto);", controller)
            self.assertIn("var created = service.create(model);", controller)
            self.assertNotIn("service.create(mapper.toModel(dto))", controller)

    def test_service_unit_test_targets_implementation(self):
        with tempfile.TemporaryDirectory() as tmp, working_directory(tmp):
            base_dir = generate_feature_project("Producto", "id:int,nombre:string")
            project = Path(tmp) / base_dir
            test = (
                project
                / "src/test/java/com/example/crud/producto/service/ProductoServiceTest.java"
            ).read_text(encoding="utf-8")

            self.assertIn("@InjectMocks", test)
            self.assertIn("private ProductoServiceImpl service;", test)
            self.assertIn("var result = service.findById(1);", test)


if __name__ == "__main__":
    unittest.main()
