from __future__ import annotations

import unittest
import subprocess
import tempfile
import importlib.util
from pathlib import Path

from retinacad.pipeline_service import LocalPipelineAdapter


class PipelineServiceTests(unittest.TestCase):
    def test_current_extraction_schema(self) -> None:
        adapter = LocalPipelineAdapter(command_template="")
        with tempfile.TemporaryDirectory() as folder:
            result_path = Path(folder) / "phenotypes.json"
            result_path.write_text('{"ratio_AV_DF": 1.1, "ratio_AV_medianDiameter": 0.8}', encoding="utf-8")
            result = adapter._read_result(subprocess.CompletedProcess([], 0, "", ""), result_path)
        self.assertEqual(result.df_ratio, 1.1)
        self.assertEqual(result.ratio, 0.8)

    def test_retired_extraction_schema_is_rejected(self) -> None:
        adapter = LocalPipelineAdapter(command_template="")
        with tempfile.TemporaryDirectory() as folder:
            result_path = Path(folder) / "phenotypes.json"
            result_path.write_text('{"VD": 0.1, "Ratio": 0.8}', encoding="utf-8")
            with self.assertRaises(ValueError):
                adapter._read_result(subprocess.CompletedProcess([], 0, "", ""), result_path)

    def test_distance_factor_uses_arterial_and_venous_medians(self) -> None:
        script = Path(__file__).resolve().parents[1] / "wsl_engine" / "extract_retina.py"
        spec = importlib.util.spec_from_file_location("extract_retina_test", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as folder:
            stats = Path(folder) / "synthetic.tsv"
            stats.write_text("DF\tAVScore\n1\t1\n3\t1\n9\t1\n2\t-1\n4\t-1\n100\t0\n", encoding="utf-8")
            self.assertEqual(module.compute_df_ratio(stats), 1.0)

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
