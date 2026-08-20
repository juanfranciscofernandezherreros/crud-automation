import unittest

from crud_generator.database_profiles import (
    _data_source_configuration,
    _data_source_properties,
    _sqlserver_application_yml,
    _sqlserver_pom,
    extract_database_argument,
    normalize_database,
)


class DatabaseProfilesTest(unittest.TestCase):

    def test_normalize_database_aliases(self):
        self.assertEqual("postgresql", normalize_database("postgres"))
        self.assertEqual("sqlserver", normalize_database("mssql"))
        self.assertEqual("sqlserver", normalize_database("sql-server"))

    def test_extract_database_argument_keeps_postgresql_as_default(self):
        args, database = extract_database_argument(["Producto", "id:int"])
        self.assertEqual(["Producto", "id:int"], args)
        self.assertEqual("postgresql", database)

    def test_extract_sqlserver_long_option(self):
        args, database = extract_database_argument(
            ["Producto", "id:int", "--database", "sqlserver"]
        )
        self.assertEqual(["Producto", "id:int"], args)
        self.assertEqual("sqlserver", database)

    def test_extract_sqlserver_equals_option(self):
        args, database = extract_database_argument(
            ["--database=sqlserver", "Producto", "id:int"]
        )
        self.assertEqual(["Producto", "id:int"], args)
        self.assertEqual("sqlserver", database)

    def test_sqlserver_pom_replaces_postgresql_dependencies(self):
        source = """
<artifactId>flyway-database-postgresql</artifactId>
<dependency><groupId>org.postgresql</groupId><artifactId>postgresql</artifactId><scope>runtime</scope></dependency>
<dependency><groupId>org.testcontainers</groupId><artifactId>postgresql</artifactId><scope>test</scope></dependency>
"""
        result = _sqlserver_pom(source)
        self.assertIn("flyway-sqlserver", result)
        self.assertIn("com.microsoft.sqlserver", result)
        self.assertIn("mssql-jdbc", result)
        self.assertIn("mssqlserver", result)
        self.assertNotIn("flyway-database-postgresql", result)

    def test_application_yml_contains_requested_hikari_configuration(self):
        result = _sqlserver_application_yml("billing")
        self.assertIn("sqlserverdb:", result)
        self.assertIn("jdbc:sqlserver://${HOSTNAME};database=${DATABASENAME}", result)
        self.assertIn("driver-class-name: com.microsoft.sqlserver.jdbc.SQLServerDriver", result)
        self.assertIn("connection-timeout: 30000", result)
        self.assertIn("idle-timeout: 300000", result)
        self.assertIn("max-lifetime: 900000", result)
        self.assertIn("maximum-pool-size: 40", result)
        self.assertIn("minimum-idle: 25", result)
        self.assertIn("pool-name: ConnPool", result)

    def test_generated_datasource_classes_use_custom_prefix_and_hikari(self):
        properties = _data_source_properties("com.example.crud")
        configuration = _data_source_configuration("com.example.crud")
        self.assertIn(
            '@ConfigurationProperties("spring.datasource.sqlserverdb")',
            properties,
        )
        self.assertIn("private Hikari hikari = new Hikari();", properties)
        self.assertIn("new HikariDataSource()", configuration)
        self.assertIn("dataSource.setMaximumPoolSize", configuration)


if __name__ == "__main__":
    unittest.main()
