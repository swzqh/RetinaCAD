from __future__ import annotations

import unittest
from pathlib import Path

from retinacad.pipeline_service import LocalPipelineAdapter


class PipelineServiceTests(unittest.TestCase):
    def test_unconfigured_pipeline_is_unavailable(self) -> None:
        adapter = LocalPipelineAdapter(
            command_template="",
            engine_script=Path("missing-engine.sh"),
            pipeline_root=Path("missing-pipeline"),
        )
        self.assertFalse(adapter.status().available)

    def test_json_array_command_template(self) -> None:
        adapter = LocalPipelineAdapter(
            command_template='["python", "worker.py", "{input}", "{output}"]'
        )
        command = adapter._build_command(
            image_path=__import__("pathlib").Path("input.png"),
            result_path=__import__("pathlib").Path("result.json"),
        )
        self.assertEqual(command[-2:], ["input.png", "result.json"])


if __name__ == "__main__":
    unittest.main()
