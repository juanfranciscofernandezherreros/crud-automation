import os
import tempfile
import unittest
from subprocess import CompletedProcess
from unittest.mock import patch

from crud_generator.verification import verify_project


def _completed(returncode, stdout="", stderr=""):
    return CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class VerifyProjectTest(unittest.TestCase):
    @patch("crud_generator.verification.shutil.which", return_value=None)
    def test_skips_when_maven_not_installed(self, which):
        result = verify_project("some-dir")

        self.assertFalse(result["ran"])
        self.assertIn("Maven no está instalado", result["summary"])

    @patch("crud_generator.verification.subprocess.run")
    @patch("crud_generator.verification.shutil.which", return_value="/usr/bin/mvn")
    def test_reports_success(self, which, run):
        run.return_value = _completed(0)

        with tempfile.TemporaryDirectory() as base_dir:
            result = verify_project(base_dir)

        self.assertTrue(result["ran"])
        self.assertTrue(result["success"])
        self.assertEqual(0, result["returncode"])
        self.assertIsNone(result["hint"])

    @patch("crud_generator.verification.subprocess.run")
    @patch("crud_generator.verification.shutil.which", return_value="/usr/bin/mvn")
    def test_reports_failure_with_returncode_and_log(self, which, run):
        run.return_value = _completed(1, stdout="", stderr="[ERROR] boom")

        with tempfile.TemporaryDirectory() as base_dir:
            result = verify_project(base_dir)

        self.assertTrue(result["ran"])
        self.assertFalse(result["success"])
        self.assertEqual(1, result["returncode"])
        self.assertIn("boom", result["log"])

    @patch("crud_generator.verification.subprocess.run")
    @patch("crud_generator.verification.shutil.which", return_value="/usr/bin/mvn")
    def test_classifies_known_docker_failure(self, which, run):
        run.return_value = _completed(
            1, stderr="Could not find a valid Docker environment. Please check configuration."
        )

        with tempfile.TemporaryDirectory() as base_dir:
            result = verify_project(base_dir)

        self.assertIsNotNone(result["hint"])
        self.assertIn("Docker", result["hint"])

    @patch("crud_generator.verification.subprocess.run")
    @patch("crud_generator.verification.shutil.which", return_value="/usr/bin/mvn")
    def test_unrecognized_failure_has_no_hint(self, which, run):
        run.return_value = _completed(1, stderr="[ERROR] something totally novel")

        with tempfile.TemporaryDirectory() as base_dir:
            result = verify_project(base_dir)

        self.assertIsNone(result["hint"])

    @patch("crud_generator.verification.subprocess.run")
    @patch("crud_generator.verification.shutil.which", return_value="/usr/bin/mvn")
    def test_summarizes_surefire_reports_when_present(self, which, run):
        run.return_value = _completed(0)

        with tempfile.TemporaryDirectory() as base_dir:
            reports_dir = os.path.join(base_dir, "target", "surefire-reports")
            os.makedirs(reports_dir)
            with open(os.path.join(reports_dir, "SomeTest.txt"), "w", encoding="utf-8") as handle:
                handle.write("Tests run: 4, Failures: 0, Errors: 0, Skipped: 1, Time elapsed: 1.2 s\n")
            with open(os.path.join(reports_dir, "OtherTest.txt"), "w", encoding="utf-8") as handle:
                handle.write("Tests run: 2, Failures: 1, Errors: 0, Skipped: 0, Time elapsed: 0.5 s\n")

            result = verify_project(base_dir)

        self.assertEqual(6, result["tests"]["run"])
        self.assertEqual(1, result["tests"]["failures"])
        self.assertEqual(0, result["tests"]["errors"])
        self.assertEqual(1, result["tests"]["skipped"])

    @patch("crud_generator.verification.subprocess.run")
    @patch("crud_generator.verification.shutil.which", return_value="/usr/bin/mvn")
    def test_tests_is_none_without_surefire_reports(self, which, run):
        run.return_value = _completed(0)

        with tempfile.TemporaryDirectory() as base_dir:
            result = verify_project(base_dir)

        self.assertIsNone(result["tests"])


if __name__ == "__main__":
    unittest.main()
