import unittest
from types import SimpleNamespace
from unittest.mock import patch

from factorio_ai.cli import _observer_player_control_problem


class CliTests(unittest.TestCase):
    def test_no_mod_autopilot_blocks_auto_observer_control_without_explicit_override(self):
        cfg = SimpleNamespace(agent_player_name="auto")

        with patch.dict(
            "os.environ",
            {
                "FACTORIO_AI_REQUIRE_REAL_PLAYER": "1",
                "FACTORIO_AI_USE_GUI_INPUT_FOR_MOVEMENT": "1",
            },
            clear=True,
        ):
            problem = _observer_player_control_problem(cfg)

        self.assertIn("refusing to control", problem)
        self.assertIn("FACTORIO_AI_ALLOW_OBSERVER_CONTROL", problem)

    def test_no_mod_autopilot_allows_virtual_ai_agent(self):
        cfg = SimpleNamespace(agent_player_name="AI")

        with patch.dict("os.environ", {"FACTORIO_AI_REQUIRE_REAL_PLAYER": "1"}, clear=True):
            problem = _observer_player_control_problem(cfg)

        self.assertEqual(problem, "")

    def test_no_mod_autopilot_allows_auto_only_with_explicit_override(self):
        cfg = SimpleNamespace(agent_player_name="auto")

        with patch.dict(
            "os.environ",
            {
                "FACTORIO_AI_REQUIRE_REAL_PLAYER": "1",
                "FACTORIO_AI_ALLOW_OBSERVER_CONTROL": "1",
            },
            clear=True,
        ):
            problem = _observer_player_control_problem(cfg)

        self.assertEqual(problem, "")


if __name__ == "__main__":
    unittest.main()
