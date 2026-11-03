"""Synthetic fixtures for interface and report tests, not model validation."""
from pathlib import Path
import json
from retinacad.model_service import PredictionResult

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = json.loads((ROOT / "model/A3_TabPFN_manifest.json").read_text(encoding="utf-8"))
VECTORS = json.loads((ROOT / "model/A3_test_vectors.json").read_text(encoding="utf-8"))


class SyntheticModel:
    features = tuple(MANIFEST["feature_order"])
    model_id = MANIFEST["model_id"]
    internal_auc = MANIFEST["internal_validation"]["auc_median"]

    def predict(self, values):
        return PredictionResult(
            VECTORS[0]["expected_probability"], None, dict(values), (),
            self.model_id, MANIFEST["outcome_definition"],
        )
