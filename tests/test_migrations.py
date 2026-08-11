import os
import tempfile
import unittest

from crud_generator import templates
from crud_generator.migrations import write_migration
from crud_generator.parsing import parse_attributes
from crud_generator.writer import write_file


class MigrationsTest(unittest.TestCase):
    def _write(self, res_base, entity_name, entity_lower, table_name, attrs_str):
        attrs = parse_attributes(attrs_str)
        write_migration(
            res_base, entity_name, entity_lower, table_name, attrs, write_file,
            templates.get_sql_migration,
        )

    def test_first_generation_writes_v1(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                self._write(
                    "res", "Producto", "producto", "productos",
                    "id:int,nombre:string:required",
                )
                migration_dir = os.path.join("res", "db", "migration")
                files = os.listdir(migration_dir)
                self.assertEqual(["V1__Create_Table_Producto.sql"], files)
                content = open(
                    os.path.join(migration_dir, files[0]), encoding="utf-8"
                ).read()
                self.assertIn("CREATE TABLE productos", content)
                self.assertIn("nombre", content)
            finally:
                os.chdir(cwd)

    def test_regeneration_with_new_field_adds_incremental_migration(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                self._write(
                    "res", "Producto", "producto", "productos",
                    "id:int,nombre:string:required",
                )
                migration_dir = os.path.join("res", "db", "migration")

                self._write(
                    "res", "Producto", "producto", "productos",
                    "id:int,nombre:string:required,activo:boolean",
                )
                files = sorted(os.listdir(migration_dir))
                self.assertEqual(
                    ["V1__Create_Table_Producto.sql", "V2__Update_Table_Producto.sql"],
                    files,
                )
                v1_content = open(
                    os.path.join(migration_dir, files[0]), encoding="utf-8"
                ).read()
                self.assertIn("nombre", v1_content)
                self.assertNotIn("activo", v1_content)

                v2_content = open(
                    os.path.join(migration_dir, files[1]), encoding="utf-8"
                ).read()
                self.assertIn("ALTER TABLE productos ADD COLUMN activo", v2_content)
            finally:
                os.chdir(cwd)

    def test_regeneration_without_new_fields_does_not_touch_migrations(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                self._write(
                    "res", "Producto", "producto", "productos",
                    "id:int,nombre:string:required",
                )
                migration_dir = os.path.join("res", "db", "migration")
                before = sorted(os.listdir(migration_dir))

                self._write(
                    "res", "Producto", "producto", "productos",
                    "id:int,nombre:string:required",
                )
                after = sorted(os.listdir(migration_dir))
                self.assertEqual(before, after)
            finally:
                os.chdir(cwd)

    def test_multi_entity_project_numbers_migrations_sequentially_per_project(self):
        # Un proyecto multi-entidad comparte un unico db/migration/: la segunda
        # entidad debe recibir V2__Create_Table (version global siguiente), NO
        # tratarse como si regenerara V1 de la primera entidad.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                self._write(
                    "res", "Cliente", "cliente", "clientes",
                    "id:int,nombre:string:required",
                )
                self._write(
                    "res", "Pedido", "pedido", "pedidos",
                    "id:int,total:decimal:precision=10:scale=2:required",
                )
                migration_dir = os.path.join("res", "db", "migration")
                files = sorted(os.listdir(migration_dir))
                self.assertEqual(
                    ["V1__Create_Table_Cliente.sql", "V2__Create_Table_Pedido.sql"],
                    files,
                )
                pedido_sql = open(
                    os.path.join(migration_dir, "V2__Create_Table_Pedido.sql"),
                    encoding="utf-8",
                ).read()
                self.assertIn("CREATE TABLE pedidos", pedido_sql)

                # Regenerar Pedido con un campo nuevo debe anadir V3 (siguiente
                # global), no colisionar con Cliente ni con su propio V2.
                self._write(
                    "res", "Pedido", "pedido", "pedidos",
                    "id:int,total:decimal:precision=10:scale=2:required,"
                    "nota:string",
                )
                files = sorted(os.listdir(migration_dir))
                self.assertEqual(
                    [
                        "V1__Create_Table_Cliente.sql",
                        "V2__Create_Table_Pedido.sql",
                        "V3__Update_Table_Pedido.sql",
                    ],
                    files,
                )
            finally:
                os.chdir(cwd)

    def test_incremental_required_field_without_default_is_nullable_with_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                self._write(
                    "res", "Producto", "producto", "productos",
                    "id:int,nombre:string:required",
                )
                self._write(
                    "res", "Producto", "producto", "productos",
                    "id:int,nombre:string:required,codigo:string:required",
                )
                migration_dir = os.path.join("res", "db", "migration")
                v2_content = open(
                    os.path.join(migration_dir, "V2__Update_Table_Producto.sql"),
                    encoding="utf-8",
                ).read()
                self.assertIn("ADD COLUMN codigo", v2_content)
                self.assertNotIn("codigo VARCHAR(255) NOT NULL", v2_content)
                self.assertIn("ATENCION", v2_content)
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()
