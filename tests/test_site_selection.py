from pathlib import Path
import tempfile
import unittest

from factorio_ai.site_selection import (
    clear_selected_improvement_site,
    load_selected_improvement_site,
    save_selected_improvement_site,
    selected_improvement_site_from_form,
)


class SiteSelectionTests(unittest.TestCase):
    def test_saves_and_loads_selected_improvement_site_per_objective(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime = Path(temp_dir)
            save_selected_improvement_site(
                runtime,
                "launch_rocket_program",
                {
                    "site_id": "plate_smelting_line:group:iron-plate:9.0,0.0",
                    "kind": "plate_smelting_line",
                    "item": "iron-plate",
                    "position": {"x": 9, "y": 0},
                },
                selected_at="2026-06-14T00:00:00+00:00",
            )

            selected = load_selected_improvement_site(runtime, "launch_rocket_program")
            self.assertEqual(selected["site_id"], "plate_smelting_line:group:iron-plate:9.0,0.0")
            self.assertEqual(selected["item"], "iron-plate")
            self.assertEqual(selected["position"], {"x": 9.0, "y": 0.0})
            self.assertEqual(load_selected_improvement_site(runtime, "other_objective"), {})

    def test_clears_selected_improvement_site_for_matching_objective(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime = Path(temp_dir)
            save_selected_improvement_site(
                runtime,
                "launch_rocket_program",
                {"site_id": "build_item_mall:2,2"},
                selected_at="2026-06-14T00:00:00+00:00",
            )

            self.assertTrue(clear_selected_improvement_site(runtime, "launch_rocket_program"))
            self.assertEqual(load_selected_improvement_site(runtime, "launch_rocket_program"), {})

    def test_parses_selected_improvement_site_from_dashboard_form(self):
        selected = selected_improvement_site_from_form(
            {
                "site_id": ["build_item_mall:2,2"],
                "site_kind": ["build_item_mall"],
                "site_item": ["transport-belt"],
                "site_position_x": ["2"],
                "site_position_y": ["2"],
            }
        )

        self.assertEqual(selected["site_id"], "build_item_mall:2,2")
        self.assertEqual(selected["kind"], "build_item_mall")
        self.assertEqual(selected["position"], {"x": 2.0, "y": 2.0})


if __name__ == "__main__":
    unittest.main()
