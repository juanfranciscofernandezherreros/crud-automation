import json
import tempfile
import unittest
from pathlib import Path

from crud_generator.conventions import (
    CONVENTIONS_FILENAME,
    load_conventions,
    save_conventions,
)
from crud_generator.parsing import DefinitionError


class LoadConventionsTest(unittest.TestCase):
    def test_returns_empty_dict_when_file_absent(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual({}, load_conventions(directory))

    def test_loads_known_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / CONVENTIONS_FILENAME
            path.write_text(
                json.dumps(
                    {
                        "architecture": "hexagonal",
                        "package": "com.miempresa.proyecto",
                        "endpoints": ["list", "get"],
                    }
                ),
                encoding="utf-8",
            )

            conventions = load_conventions(directory)

            self.assertEqual("hexagonal", conventions["architecture"])
            self.assertEqual("com.miempresa.proyecto", conventions["package"])
            self.assertEqual(["list", "get"], conventions["endpoints"])

    def test_rejects_invalid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / CONVENTIONS_FILENAME
            path.write_text("{ not valid", encoding="utf-8")

            with self.assertRaisesRegex(DefinitionError, "no es un JSON válido"):
                load_conventions(directory)

    def test_rejects_unknown_key(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / CONVENTIONS_FILENAME
            path.write_text(json.dumps({"sospechoso": True}), encoding="utf-8")

            with self.assertRaisesRegex(DefinitionError, "Claves desconocidas"):
                load_conventions(directory)

    def test_rejects_unknown_architecture(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / CONVENTIONS_FILENAME
            path.write_text(json.dumps({"architecture": "espagueti"}), encoding="utf-8")

            with self.assertRaisesRegex(DefinitionError, "arquitectura desconocida"):
                load_conventions(directory)

    def test_rejects_unknown_endpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / CONVENTIONS_FILENAME
            path.write_text(json.dumps({"endpoints": ["volar"]}), encoding="utf-8")

            with self.assertRaisesRegex(DefinitionError, "endpoints desconocidos"):
                load_conventions(directory)

    def test_rejects_invalid_package(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / CONVENTIONS_FILENAME
            path.write_text(json.dumps({"package": "Com.Not.Valid"}), encoding="utf-8")

            with self.assertRaisesRegex(DefinitionError, "'package' no válido"):
                load_conventions(directory)


class SaveConventionsTest(unittest.TestCase):
    def test_writes_and_round_trips(self):
        with tempfile.TemporaryDirectory() as directory:
            save_conventions({"architecture": "clean"}, directory)

            self.assertEqual({"architecture": "clean"}, load_conventions(directory))

    def test_returns_the_written_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = save_conventions({"architecture": "layered"}, directory)

            self.assertTrue(Path(path).is_file())
            self.assertTrue(path.endswith(CONVENTIONS_FILENAME))


if __name__ == "__main__":
    unittest.main()
