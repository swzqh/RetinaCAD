from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from retinacad.model_service import LockedA3Model
from retinacad.report_service import export_report


ROOT = Path(__file__).resolve().parents[2]


class ReportServiceTests(unittest.TestCase):
    def test_exports_matching_html_and_json(self) -> None:
        model = LockedA3Model(ROOT / "model" / "A3_locked_model.json")
        vectors = json.loads(
            (ROOT / "model" / "A3_test_vectors.json").read_text(encoding="utf-8")
        )
        result = model.predict(vectors[0]["inputs"])
        with tempfile.TemporaryDirectory() as temp_dir:
            html_path, json_path = export_report(
                directory=temp_dir,
                result=result,
                case_code="TEST-001",
                image_name=None,
                image_qc=None,
                phenotype_source="Manual entry",
            )
            self.assertTrue(html_path.exists())
            self.assertTrue(json_path.exists())
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertAlmostEqual(payload["probability"], result.probability)
            self.assertEqual(payload["phenotype_source"], "Manual entry")
            self.assertIn("For research reference only", html_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
