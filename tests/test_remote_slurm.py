import unittest

from factorio_ai.remote_slurm import RemoteSlurmConfig, _llm_status_remediation


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
            time_limit="24:00:00",
            setup_timeout_seconds=60,
            task_timeout_seconds=30,
        )
        remediation = _llm_status_remediation(["FACTORIO_AI_LLM_BASE_URL"], cfg, True)
        self.assertIsNotNone(remediation)
        self.assertIn("FACTORIO_AI_LLM_BASE_URL", remediation["required_remote_env"])
        self.assertEqual(remediation["job_name"], "AUTO")
        self.assertTrue(remediation["vllm_available_in_job"])


if __name__ == "__main__":
    unittest.main()
