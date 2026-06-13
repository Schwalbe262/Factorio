import unittest
from unittest.mock import patch

from factorio_ai.remote_slurm import (
    RemoteSlurmConfig,
    _attached_env_setup,
    _gpu_allocation_visible,
    _llm_status_remediation,
    _status_needs_local_gpu,
    _worker_env_values,
    config,
)
from factorio_ai.slurm_worker import run_strategy_model_benchmark


class RemoteSlurmTests(unittest.TestCase):
    def test_llm_status_remediation_explains_required_env(self):
        cfg = RemoteSlurmConfig(
            enabled=True,
            ssh_path="ssh",
            scp_path="scp",
            host="example",
            user="user",
            port=22,
            key_path="key",
            remote_dir="~/kakao-bot-worker",
            job_name="AUTO",
            conda_env="factorio-ai",
            partition="gpu",
            cpus_per_task=8,
            gpus_per_node=1,
            gres="gpu:1",
            time_limit="24:00:00",
            setup_timeout_seconds=60,
            task_timeout_seconds=30,
        )
        remediation = _llm_status_remediation(["FACTORIO_AI_LLM_BASE_URL"], cfg, True, {"count": 1})
        self.assertIsNotNone(remediation)
        self.assertIn("FACTORIO_AI_LLM_BASE_URL", remediation["required_remote_env"])
        self.assertEqual(remediation["job_name"], "AUTO")
        self.assertTrue(remediation["vllm_available_in_job"])
        self.assertEqual(remediation["required_gpu_allocation"]["sbatch_option"], "--gres=gpu:1")

    def test_llm_status_remediation_marks_missing_gpu(self):
        cfg = RemoteSlurmConfig(
            enabled=True,
            ssh_path="ssh",
            scp_path="scp",
            host="example",
            user="user",
            port=22,
            key_path="key",
            remote_dir="~/kakao-bot-worker",
            job_name="AUTO",
            conda_env="factorio-ai",
            partition="gpu",
            cpus_per_task=8,
            gpus_per_node=1,
            gres="gpu:1",
            time_limit="24:00:00",
            setup_timeout_seconds=60,
            task_timeout_seconds=30,
        )
        remediation = _llm_status_remediation(
            ["GPU allocation"],
            cfg,
            False,
            {"count": 0, "env": {"CUDA_VISIBLE_DEVICES": "none"}},
        )
        self.assertTrue(remediation["required_gpu_allocation"]["needed"])
        self.assertIn("FACTORIO_AI_SLURM_GPUS_PER_NODE=1", remediation["required_gpu_allocation"]["factorio_worker_env"])

    def test_llm_status_remediation_marks_pending_gpu_allocation(self):
        cfg = RemoteSlurmConfig(
            enabled=True,
            ssh_path="ssh",
            scp_path="scp",
            host="example",
            user="user",
            port=22,
            key_path="key",
            remote_dir="~/kakao-bot-worker",
            job_name="AUTO",
            conda_env="factorio-ai",
            partition="gpu",
            cpus_per_task=8,
            gpus_per_node=3,
            gres="gpu:a6000ada:3",
            time_limit="24:00:00",
            setup_timeout_seconds=60,
            task_timeout_seconds=30,
        )
        remediation = _llm_status_remediation(
            ["Slurm worker job pending GPU allocation", "GPU allocation"],
            cfg,
            False,
            None,
        )
        self.assertIn("not allocated the requested GPUs yet", remediation["why"])
        self.assertTrue(remediation["required_gpu_allocation"]["needed"])

    def test_config_defaults_to_factorio_owned_worker(self):
        with patch.dict("os.environ", {"USERPROFILE": "C:\\Users\\Test"}, clear=True):
            cfg = config()
        self.assertEqual(cfg.remote_dir, "~/factorio-ai-worker")
        self.assertEqual(cfg.job_name, "factorio-ai-worker")
        self.assertEqual(cfg.gres, "gpu:1")

    def test_config_prefers_factorio_remote_dir_and_typed_gres(self):
        with patch.dict(
            "os.environ",
            {
                "SUPERCOMPUTER_WORKER_REMOTE_DIR": "~/kakao-bot-worker",
                "FACTORIO_AI_SLURM_REMOTE_DIR": "~/factorio-ai-worker",
                "FACTORIO_AI_SLURM_GPUS_PER_NODE": "3",
                "FACTORIO_AI_SLURM_GRES": "gpu:a6000ada:3",
                "USERPROFILE": "C:\\Users\\Test",
            },
            clear=True,
        ):
            cfg = config()
        self.assertEqual(cfg.remote_dir, "~/factorio-ai-worker")
        self.assertEqual(cfg.gpus_per_node, 3)
        self.assertEqual(cfg.gres, "gpu:a6000ada:3")

    def test_worker_env_values_derives_loopback_endpoint_for_vllm(self):
        cfg = RemoteSlurmConfig(
            enabled=True,
            ssh_path="ssh",
            scp_path="scp",
            host="example",
            user="user",
            port=22,
            key_path="key",
            remote_dir="~/factorio-ai-worker",
            job_name="factorio-ai-worker",
            conda_env="factorio-ai",
            partition="gpu3",
            cpus_per_task=8,
            gpus_per_node=3,
            gres="gpu:a6000ada:3",
            time_limit="24:00:00",
            setup_timeout_seconds=60,
            task_timeout_seconds=30,
        )
        with patch.dict("os.environ", {"FACTORIO_AI_VLLM_MODEL": "Qwen/test", "FACTORIO_AI_VLLM_PORT": "8001"}, clear=True):
            values = _worker_env_values(cfg)
        self.assertEqual(values["FACTORIO_AI_SLURM_CONDA_ENV"], "factorio-ai")
        self.assertEqual(values["FACTORIO_AI_LLM_MODEL"], "Qwen/test")
        self.assertEqual(values["FACTORIO_AI_LLM_BASE_URL"], "http://127.0.0.1:8001/v1")

    def test_gpu_allocation_visible_from_nvidia_or_slurm_env(self):
        self.assertTrue(_gpu_allocation_visible({"count": 1, "env": {}}))
        self.assertTrue(_gpu_allocation_visible({"count": 0, "env": {"SLURM_JOB_GPUS": "0"}}))
        self.assertFalse(_gpu_allocation_visible({"count": 0, "env": {"CUDA_VISIBLE_DEVICES": "none"}}))

    def test_local_gpu_needed_for_vllm_or_loopback_endpoint(self):
        self.assertTrue(_status_needs_local_gpu({"FACTORIO_AI_VLLM_MODEL": "Qwen/Qwen3.5-4B"}))
        self.assertTrue(_status_needs_local_gpu({"FACTORIO_AI_LLM_BASE_URL": "http://127.0.0.1:8000/v1"}))
        self.assertFalse(_status_needs_local_gpu({"FACTORIO_AI_LLM_BASE_URL": "https://llm.example/v1"}))

    def test_attached_env_setup_loads_remote_worker_config(self):
        setup = _attached_env_setup("/home/user/kakao-bot-worker")
        self.assertIn("/home/user/kakao-bot-worker/config.env", setup)
        self.assertIn("FACTORIO_AI_LLM_*|FACTORIO_AI_VLLM_*|FACTORIO_AI_CONDA_ENV", setup)
        self.assertIn('export "\\$key=\\$value"', setup)

    def test_strategy_model_benchmark_runs_same_payload_per_model(self):
        result = run_strategy_model_benchmark(
            {
                "models": ["Qwen/test-3B", "Qwen/test-7B"],
                "strategy_payload": {
                    "objective": "launch_rocket_program",
                    "observation": {"inventory": {}, "entities": [], "enemies": []},
                    "production_targets": {},
                },
            }
        )
        self.assertTrue(result["ok"])
        self.assertFalse(result["base_url_configured"])
        self.assertEqual([row["model"] for row in result["models"]], ["Qwen/test-3B", "Qwen/test-7B"])
        self.assertTrue(all(row["source"] == "heuristic" for row in result["models"]))


if __name__ == "__main__":
    unittest.main()
