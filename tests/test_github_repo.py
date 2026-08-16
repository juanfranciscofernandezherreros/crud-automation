import os
import tempfile
import unittest
from subprocess import CompletedProcess
from unittest.mock import patch

from crud_generator.github_repo import push_to_github
from crud_generator.parsing import DefinitionError


def _ok(stdout=""):
    return CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")


def _fail(stderr="boom"):
    return CompletedProcess(args=[], returncode=1, stdout="", stderr=stderr)


class PushToGithubTest(unittest.TestCase):
    def test_missing_project_dir_raises(self):
        with self.assertRaises(DefinitionError):
            push_to_github("no-existe-este-directorio")

    @patch("crud_generator.github_repo.subprocess.run")
    def test_initializes_git_commits_and_creates_repo_when_not_a_repo(self, run):
        run.side_effect = [
            _ok(),  # git init -b main
            _ok(),  # git add -A
            _ok("M  file.txt"),  # git status --porcelain (hay cambios)
            _ok(),  # git commit
            _ok(),  # gh repo create
            _ok("https://github.com/user/mi-proyecto"),  # gh repo view
        ]

        with tempfile.TemporaryDirectory() as tmp:
            project_dir = os.path.join(tmp, "mi-proyecto")
            os.mkdir(project_dir)

            url = push_to_github(project_dir)

        self.assertEqual("https://github.com/user/mi-proyecto", url)
        called_commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(["git", "init", "-b", "main"], called_commands[0])
        self.assertEqual(["git", "add", "-A"], called_commands[1])
        self.assertEqual(["git", "status", "--porcelain"], called_commands[2])
        self.assertEqual(
            ["git", "commit", "-m", "Initial commit: mi-proyecto"], called_commands[3]
        )
        create_command = called_commands[4]
        self.assertEqual("gh", create_command[0])
        self.assertIn("--public", create_command)
        self.assertIn("mi-proyecto", create_command)

    @patch("crud_generator.github_repo.subprocess.run")
    def test_skips_git_init_when_already_a_repo(self, run):
        run.side_effect = [
            _ok(),  # git add -A
            _ok(""),  # git status --porcelain (sin cambios)
            _ok(),  # gh repo create
            _ok("https://github.com/user/mi-proyecto"),  # gh repo view
        ]

        with tempfile.TemporaryDirectory() as tmp:
            project_dir = os.path.join(tmp, "mi-proyecto")
            os.mkdir(project_dir)
            os.mkdir(os.path.join(project_dir, ".git"))

            push_to_github(project_dir)

        called_commands = [call.args[0] for call in run.call_args_list]
        self.assertNotIn(["git", "init", "-b", "main"], called_commands)
        self.assertFalse(
            any(cmd[:2] == ["git", "commit"] for cmd in called_commands),
            "sin cambios pendientes no debe intentar comitear",
        )

    @patch("crud_generator.github_repo.subprocess.run")
    def test_private_flag_is_propagated(self, run):
        run.side_effect = [
            _ok(),  # git init -b main
            _ok(),  # git add -A
            _ok(""),  # git status --porcelain
            _ok(),  # gh repo create
            _ok("https://github.com/user/priv"),  # gh repo view
        ]

        with tempfile.TemporaryDirectory() as tmp:
            project_dir = os.path.join(tmp, "priv")
            os.mkdir(project_dir)

            push_to_github(project_dir, private=True)

        create_command = run.call_args_list[3].args[0]
        self.assertIn("--private", create_command)
        self.assertNotIn("--public", create_command)

    @patch("crud_generator.github_repo.subprocess.run")
    def test_failed_command_raises_definition_error(self, run):
        run.return_value = _fail("fatal: not a git repository")

        with tempfile.TemporaryDirectory() as tmp:
            project_dir = os.path.join(tmp, "roto")
            os.mkdir(project_dir)
            os.mkdir(os.path.join(project_dir, ".git"))

            with self.assertRaises(DefinitionError) as ctx:
                push_to_github(project_dir)

        self.assertIn("fatal: not a git repository", str(ctx.exception))

    @patch("crud_generator.github_repo.subprocess.run", side_effect=FileNotFoundError())
    def test_missing_executable_raises_friendly_error(self, run):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = os.path.join(tmp, "sin-git")
            os.mkdir(project_dir)
            os.mkdir(os.path.join(project_dir, ".git"))

            with self.assertRaises(DefinitionError) as ctx:
                push_to_github(project_dir)

        self.assertIn("PATH", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
