import json
import tempfile
import unittest
from pathlib import Path

from factorio_ai.config import AppConfig
from factorio_ai.factorio import write_server_settings


def test_config(root: Path) -> AppConfig:
    return AppConfig(
        factorio_exe=Path("factorio.exe"),
        runtime_dir=root / "runtime",
        mod_runtime_dir=root / "runtime" / "mods",
        save_path=root / "runtime" / "saves" / "test.zip",
        rcon_host="127.0.0.1",
        rcon_port=27015,
        rcon_password="factorio-ai",
        server_port=34197,
        log_dir=root / "logs",
        agent_player_name="AI",
        slurm_enabled=False,
    )


class FactorioProcessConfigTests(unittest.TestCase):
    def test_development_server_is_single_review_client_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_server_settings(test_config(Path(temp_dir)))
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["max_players"], 1)
        self.assertFalse(payload["visibility"]["public"])
        self.assertFalse(payload["visibility"]["lan"])


if __name__ == "__main__":
    unittest.main()
