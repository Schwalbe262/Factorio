import unittest

from factorio_ai.vanilla_gui import AchievementPolicyError, validate_achievement_safe_args


class VanillaGuiTests(unittest.TestCase):
    def test_allows_window_size_argument(self):
        args = validate_achievement_safe_args(["--window-size", "1600x900"])
        self.assertEqual(args, ["--window-size", "1600x900"])

    def test_allows_inline_window_size_argument(self):
        args = validate_achievement_safe_args(["--window-size=1600x900"])
        self.assertEqual(args, ["--window-size=1600x900"])

    def test_rejects_mod_directory(self):
        with self.assertRaises(AchievementPolicyError):
            validate_achievement_safe_args(["--mod-directory", "runtime/mods"])

    def test_rejects_rcon(self):
        with self.assertRaises(AchievementPolicyError):
            validate_achievement_safe_args(["--rcon-port", "27015"])

    def test_rejects_unknown_custom_argument(self):
        with self.assertRaises(AchievementPolicyError):
            validate_achievement_safe_args(["--some-new-unsafe-flag"])

    def test_rejects_bare_save_argument(self):
        with self.assertRaises(AchievementPolicyError):
            validate_achievement_safe_args(["my-save.zip"])


if __name__ == "__main__":
    unittest.main()
