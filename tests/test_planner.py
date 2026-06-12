import unittest

from factorio_ai.planner import AutomationScienceSkill, IronPlateSkill


def base_observation():
    return {
        "tick": 1,
        "player": {"position": {"x": 0, "y": 0}},
        "inventory": {
            "coal": 10,
            "burner-mining-drill": 1,
            "stone-furnace": 1,
        },
        "craftable": {},
        "resources": [
            {"name": "iron-ore", "position": {"x": 4, "y": 0}, "distance": 4},
            {"name": "coal", "position": {"x": 2, "y": 0}, "distance": 2},
        ],
        "entities": [],
    }


class PlannerTests(unittest.TestCase):
    def test_done_when_target_reached(self):
        obs = base_observation()
        obs["inventory"]["iron-plate"] = 10
        decision = IronPlateSkill(target_count=10).next_action(obs)
        self.assertTrue(decision.done)
        self.assertIsNone(decision.action)

    def test_places_burner_mining_drill_first(self):
        decision = IronPlateSkill(target_count=10).next_action(base_observation())
        self.assertFalse(decision.done)
        self.assertEqual(decision.action["type"], "build")
        self.assertEqual(decision.action["name"], "burner-mining-drill")
        self.assertTrue(decision.action["allow_nearby"])

    def test_moves_next_to_ore_before_building_distant_drill(self):
        obs = base_observation()
        obs["resources"][0]["position"] = {"x": 100, "y": 0}
        obs["resources"][0]["distance"] = 100
        decision = IronPlateSkill(target_count=10).next_action(obs)
        self.assertEqual(decision.action["type"], "move_to")
        self.assertEqual(decision.action["position"], {"x": 102.0, "y": 0.0})

    def test_mines_ore_when_drill_and_furnace_exist(self):
        obs = base_observation()
        obs["inventory"].pop("burner-mining-drill")
        obs["entities"] = [
            {
                "name": "burner-mining-drill",
                "unit_number": 101,
                "position": {"x": 4, "y": 0},
                "distance": 4,
                "inventories": {},
            },
            {
                "name": "stone-furnace",
                "unit_number": 102,
                "position": {"x": 5, "y": 0},
                "distance": 5,
                "inventories": {},
            },
        ]
        decision = IronPlateSkill(target_count=10).next_action(obs)
        self.assertEqual(decision.action["type"], "mine")
        self.assertEqual(decision.action["name"], "iron-ore")

    def test_science_skill_crafts_science_when_prerequisites_exist(self):
        obs = base_observation()
        obs["inventory"] = {
            "iron-plate": 10,
            "iron-gear-wheel": 1,
            "copper-plate": 1,
        }
        obs["craftable"] = {"automation-science-pack": 1}
        decision = AutomationScienceSkill(target_count=1).next_action(obs)
        self.assertEqual(decision.action["type"], "craft")
        self.assertEqual(decision.action["recipe"], "automation-science-pack")

    def test_science_skill_builds_second_furnace_for_copper(self):
        obs = base_observation()
        obs["inventory"] = {
            "iron-plate": 10,
            "stone-furnace": 1,
            "coal": 8,
        }
        obs["resources"].append({"name": "copper-ore", "position": {"x": 8, "y": 0}, "distance": 8})
        obs["entities"] = [
            {
                "name": "stone-furnace",
                "unit_number": 201,
                "position": {"x": 4, "y": 0},
                "distance": 4,
                "inventories": {"2": {"iron-plate": 1}},
            }
        ]
        decision = AutomationScienceSkill(target_count=1).next_action(obs)
        self.assertEqual(decision.action["type"], "build")
        self.assertEqual(decision.action["name"], "stone-furnace")

    def test_science_skill_takes_copper_from_furnace_before_waiting(self):
        obs = base_observation()
        obs["inventory"] = {
            "iron-plate": 10,
            "iron-gear-wheel": 1,
            "coal": 8,
            "automation-science-pack": 4,
        }
        obs["resources"].append({"name": "copper-ore", "position": {"x": 8, "y": 0}, "distance": 8})
        obs["entities"] = [
            {
                "name": "stone-furnace",
                "unit_number": 201,
                "position": {"x": 4, "y": 0},
                "distance": 4,
                "inventories": {"3": {"copper-plate": 4}},
            }
        ]
        decision = AutomationScienceSkill(target_count=5).next_action(obs)
        self.assertEqual(decision.action["type"], "take")
        self.assertEqual(decision.action["item"], "copper-plate")


if __name__ == "__main__":
    unittest.main()
