import tempfile
import unittest
from pathlib import Path

from factorio_ai.layout_validation import (
    append_layout_validation_feedback,
    candidate_blueprint_entities,
    layout_validation_feedback_row,
    layout_validation_feedback_summary,
    merge_sandbox_validation_feedback,
    sandbox_payload_for_entities,
)
from factorio_ai.planner import factory_layout_simulation_candidates


def layout_observation():
    return {
        "tick": 1,
        "player": {"position": {"x": 0, "y": 0}},
        "inventory": {},
        "craftable": {},
        "resources": [],
        "entities": [
            {
                "name": "assembling-machine-1",
                "unit_number": 10,
                "recipe": "electronic-circuit",
                "position": {"x": 0, "y": 0},
                "electric_network_connected": True,
                "inventories": {},
            }
        ],
    }


class LayoutValidationTests(unittest.TestCase):
    def test_sandbox_payload_feeds_terminal_inputs_and_expects_circuit_output(self):
        candidate = next(
            item
            for item in factory_layout_simulation_candidates(layout_observation())
            if item["candidate_id"] == "green-circuit-3-cable-2-circuit-cell"
        )
        entities = candidate_blueprint_entities(candidate, variant="after")
        payload = sandbox_payload_for_entities(
            candidate_id="green-circuit-3-cable-2-circuit-cell",
            variant="after",
            entities=entities,
            ticks=120,
        )

        feed_items = {row["item"] for row in payload["input_feeds"]}
        self.assertIn("copper-plate", feed_items)
        self.assertIn("iron-plate", feed_items)
        self.assertEqual(payload["expected_outputs"], ["electronic-circuit"])
        self.assertTrue(payload["surface_name"].startswith("codex-layout-green-circuit-3-cable-2-circuit-cell-after-"))

    def test_feedback_log_summary_and_merge_attach_sandbox_validation(self):
        row = layout_validation_feedback_row(
            candidate_id="green-circuit-3-cable-2-circuit-cell",
            variant="after",
            static_validation={"status": "pass"},
            sandbox_validation={
                "status": "fail",
                "reasons": ["expected output electronic-circuit was not observed after sandbox ticks"],
                "observed_outputs": {"electronic-circuit": 0},
                "ticks": 3600,
                "checked_machines": 5,
            },
            timestamp="2026-06-14T00:00:00+00:00",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            append_layout_validation_feedback(Path(temp_dir), row)
            summary = layout_validation_feedback_summary(Path(temp_dir))

        layout = {
            "simulation_candidates": [
                {"candidate_id": "green-circuit-3-cable-2-circuit-cell", "validation": {"status": "pass"}},
            ]
        }
        merged = merge_sandbox_validation_feedback(layout, summary)
        candidate = merged["simulation_candidates"][0]
        self.assertEqual(candidate["sandbox_validation"]["status"], "fail")
        self.assertFalse(candidate["build_ready"])
        self.assertIn("sandbox validation feedback must pass", candidate["build_ready_blockers"][0])
        self.assertIn("Do not mark green-circuit-3-cable-2-circuit-cell build-ready", candidate["sandbox_validation_lesson"])

    def test_feedback_merge_marks_candidate_build_ready_only_after_site_and_sandbox_pass(self):
        feedback = {
            "latest_by_candidate": {
                "green-circuit-3-cable-2-circuit-cell": {
                    "timestamp": "2026-06-14T00:00:00+00:00",
                    "sandbox_validation": {
                        "status": "pass",
                        "reasons": [],
                        "warnings": [],
                        "observed_outputs": {"electronic-circuit": 95},
                        "ticks": 1200,
                    },
                    "lesson": "Sandbox produced expected electronic-circuit output.",
                }
            }
        }
        layout = {
            "simulation_candidates": [
                {
                    "candidate_id": "green-circuit-3-cable-2-circuit-cell",
                    "site_prebuild_gate": {"status": "pass", "build_ready": True, "errors": []},
                    "site_placement_search": {"status": "found", "summary": "found candidate build anchor"},
                    "build_ready": False,
                },
            ]
        }

        merged = merge_sandbox_validation_feedback(layout, feedback)
        candidate = merged["simulation_candidates"][0]
        self.assertTrue(candidate["build_ready"])
        self.assertEqual(candidate["build_ready_blockers"], [])


if __name__ == "__main__":
    unittest.main()
