from __future__ import annotations
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from retinacad.model_service import LockedA3Model
from helpers import MANIFEST, VECTORS


class RecordingPredictor:
    def predict_proba(self, row):
        self.row = row
        return np.array([[0.25, 0.75]])


class ModelBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.model = object.__new__(LockedA3Model)
        self.model.payload = MANIFEST
        self.model.features = tuple(MANIFEST["feature_order"])
        self.model.model_id = MANIFEST["model_id"]
        self.model.clf = RecordingPredictor()
        self.values = dict(VECTORS[0]["inputs"])

    def test_input_order_is_fixed(self):
        self.model.predict(dict(reversed(list(self.values.items()))))
        expected = [self.values[f] for f in self.model.features]
        np.testing.assert_array_equal(self.model.clf.row[0], expected)

    def test_retired_density_schema_is_rejected(self):
        self.values["VD"] = self.values.pop("ratio_AV_DF")
        with self.assertRaisesRegex(ValueError, "schema mismatch"):
            self.model.predict(self.values)

    def test_missing_and_unknown_keys_are_rejected(self):
        for key in ("missing", "unknown"):
            values = dict(self.values)
            if key == "missing":
                values.pop("Age")
            else:
                values["extra"] = 1
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.model.predict(values)

    def test_binary_and_ratio_validation(self):
        for field, invalid in (("Male", 2), ("ratio_AV_DF", 0), ("ratio_AV_medianDiameter", -1), ("Age", float("inf"))):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.model.predict(dict(self.values, **{field: invalid}))

    def test_only_documented_missing_measurements_are_permitted(self):
        values = dict(self.values, LVMI_g_m2=None, RWT=float("nan"))
        result = self.model.predict(values)
        self.assertEqual(set(result.imputed_fields), {"LVMI_g_m2", "RWT"})
        self.assertTrue(np.isnan(self.model.clf.row[0, self.model.features.index("RWT")]))
        with self.assertRaises(ValueError):
            self.model.predict(dict(self.values, Age=None))

    def test_missing_private_fit_has_an_actionable_message(self):
        with tempfile.TemporaryDirectory() as folder:
            manifest = Path(folder) / "manifest.json"
            manifest.write_text(json.dumps(MANIFEST), encoding="utf-8")
            with patch.dict(os.environ, {"RETINACAD_MODEL_DIR": folder}):
                with self.assertRaisesRegex(FileNotFoundError, "corresponding author"):
                    LockedA3Model(manifest)

    def test_modified_fit_state_is_rejected_before_loading(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            manifest = directory / "manifest.json"
            manifest.write_text(json.dumps(MANIFEST), encoding="utf-8")
            (directory / MANIFEST["fit_state_file"]).write_bytes(b"modified")
            checkpoint = directory / MANIFEST["checkpoint_file"]
            checkpoint.write_bytes(b"placeholder")
            with patch.dict(os.environ, {"RETINACAD_MODEL_DIR": folder, "RETINACAD_CHECKPOINT": str(checkpoint)}):
                with self.assertRaisesRegex(ValueError, "Fit state does not match"):
                    LockedA3Model(manifest)


if __name__ == "__main__":
    unittest.main()
