import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from crud_generator.agent_rules import (
    AGENT_COMMAND_ENV,
    RULE_FILES,
    apply_agent_rules,
    build_agent_prompt,
    load_agent_rules,
    resolve_agent_command,
)
from crud_generator.parsing import DefinitionError


class AgentRulesTest(unittest.TestCase):
    def _write_rule_fixture(self, root):
        for relative_path in RULE_FILES:
            path = Path(root) / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"rule from {relative_path}\n", encoding="utf-8")

    def test_load_agent_rules_reads_generator_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write_rule_fixture(tmp)

            rules = load_agent_rules(tmp)

            self.assertIn("# Source: AGENTS.md", rules)
            self.assertIn("# Source: docs/testing.md", rules)

    def test_build_agent_prompt_forbids_copying_rule_files(self):
        prompt = build_agent_prompt(".", rules_text="example rule")

        self.assertIn("Do NOT copy AGENTS.md", prompt)
        self.assertIn("Apply the rules to the generated implementation", prompt)
        self.assertIn("example rule", prompt)

    def test_resolve_agent_command_uses_environment_variable(self):
        with patch.dict(os.environ, {AGENT_COMMAND_ENV: "agent --stdin"}, clear=False):
            command = resolve_agent_command()

        self.assertEqual("agent --stdin", command)

    def test_resolve_agent_command_requires_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(DefinitionError):
                resolve_agent_command()

    @patch("crud_generator.agent_rules.load_agent_rules", return_value="rules")
    @patch("crud_generator.agent_rules.subprocess.run")
    def test_apply_agent_rules_runs_in_generated_project(self, run, _load_rules):
        run.return_value.returncode = 0
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "crud-producto"
            project.mkdir()

            result = apply_agent_rules(project, command="agent --stdin")

        self.assertEqual(project.resolve(), result)
        run.assert_called_once()
        call = run.call_args
        self.assertEqual(["agent", "--stdin"], call.args[0])
        self.assertEqual(project.resolve(), call.kwargs["cwd"])
        self.assertIn("rules", call.kwargs["input"])
        self.assertTrue(call.kwargs["text"])
        self.assertFalse(call.kwargs["check"])

    @patch("crud_generator.agent_rules.load_agent_rules", return_value="rules")
    @patch("crud_generator.agent_rules.subprocess.run")
    def test_apply_agent_rules_fails_when_agent_returns_error(self, run, _load_rules):
        run.return_value.returncode = 7
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "crud-producto"
            project.mkdir()

            with self.assertRaisesRegex(DefinitionError, "código 7"):
                apply_agent_rules(project, command="agent --stdin")


if __name__ == "__main__":
    unittest.main()
