"""Contrato de la arquitectura feature-based alineada con AGENTS.md."""

import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from crud_generator.feature_generator import generate_feature_project


MAVEN = shutil.which("mvn.cmd") or shutil.which("mvn")


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
            test_java = project / "src/test/java/com/example/crud/producto"

            self.assertTrue((java / "model/Producto.java").exists())
            self.assertTrue((java / "entity/ProductoEntity.java").exists())
            self.assertTrue((java / "service/ProductoService.java").exists())
            self.assertTrue((java / "service/ProductoServiceImpl.java").exists())
            self.assertTrue((java / "mapper/ProductoMapper.java").exists())
            self.assertTrue((java / "mapper/ProductoEntityMapper.java").exists())
            self.assertTrue((java / "repository/ProductoRepository.java").exists())
            self.assertTrue((java / "controller/ProductoController.java").exists())
            self.assertTrue((test_java / "service/ProductoServiceTest.java").exists())
            self.assertTrue((test_java / "controller/ProductoControllerTest.java").exists())

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

    def test_entity_mapper_uses_separate_model_entity_mapping(self):
        with tempfile.TemporaryDirectory() as tmp, working_directory(tmp):
            base_dir = generate_feature_project("Producto", "id:int,nombre:string")
            project = Path(tmp) / base_dir
            mapper = (
                project
                / "src/main/java/com/example/crud/producto/mapper/ProductoEntityMapper.java"
            ).read_text(encoding="utf-8")

            self.assertIn("import org.mapstruct.Mapping;", mapper)
            self.assertIn("ProductoEntity toEntity(Producto model);", mapper)
            self.assertIn("Producto toModel(ProductoEntity entity);", mapper)

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

    def test_controller_test_mocks_service_interface(self):
        with tempfile.TemporaryDirectory() as tmp, working_directory(tmp):
            base_dir = generate_feature_project("Producto", "id:int,nombre:string")
            project = Path(tmp) / base_dir
            test = (
                project
                / "src/test/java/com/example/crud/producto/controller/ProductoControllerTest.java"
            ).read_text(encoding="utf-8")

            self.assertIn("@WebMvcTest(ProductoController.class)", test)
            self.assertIn("private ProductoService service;", test)
            self.assertIn("var model = new Producto();", test)


@unittest.skipUnless(MAVEN, "Maven no está instalado")
class FeatureGeneratedProjectAcceptanceTest(unittest.TestCase):

    def test_generated_feature_project_compiles_and_passes_tests(self):
        workspace = Path.cwd()
        with tempfile.TemporaryDirectory(prefix=".feature-generated-", dir=workspace) as tmp:
            root = Path(tmp)
            with working_directory(root):
                base_dir = generate_feature_project(
                    "Producto",
                    "id:int,nombre:string:not_blank:max=120,precio:decimal:required:positive",
                )

            project = root / base_dir
            local_repository = os.environ.get(
                "CRUD_GENERATOR_MAVEN_REPO",
                str(workspace / ".m2" / "repository"),
            )
            result = subprocess.run(
                [MAVEN, f"-Dmaven.repo.local={local_repository}", "test", "--quiet"],
                cwd=project,
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )

            if result.returncode != 0:
                self.fail(
                    "El proyecto feature generado no compila o sus tests fallan.\n"
                    f"STDOUT:\n{result.stdout[-6000:]}\n"
                    f"STDERR:\n{result.stderr[-6000:]}"
                )


if __name__ == "__main__":
    unittest.main()
