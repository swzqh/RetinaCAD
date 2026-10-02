from __future__ import annotations

import json
import unittest
from pathlib import Path

from retinacad.model_service import LockedA3Model


ROOT = Path(__file__).resolve().parents[2]


class LockedA3ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = LockedA3Model(ROOT / "model" / "A3_locked_model.json")
        cls.vectors = json.loads(
            (ROOT / "model" / "A3_test_vectors.json").read_text(encoding="utf-8")
        )

    def test_synthetic_vectors_match(self) -> None:
        for vector in self.vectors:
            with self.subTest(vector=vector["case_id"]):
                observed = self.model.predict(vector["inputs"]).probability
                self.assertLessEqual(
                    abs(observed - vector["expected_probability"]), 1e-12
                )

    def test_missing_key_is_rejected(self) -> None:
        values = dict(self.vectors[0]["inputs"])
        values.pop("Age")
        with self.assertRaises(ValueError):
            self.model.predict(values)

    def test_unknown_key_is_rejected(self) -> None:
        values = dict(self.vectors[0]["inputs"])
        values["unexpected"] = 1
        with self.assertRaises(ValueError):
            self.model.predict(values)

    def test_invalid_binary_is_rejected(self) -> None:
        values = dict(self.vectors[0]["inputs"])
        values["Male"] = 2
        with self.assertRaises(ValueError):
            self.model.predict(values)

    def test_null_uses_locked_fill(self) -> None:
        result = self.model.predict(self.vectors[3]["inputs"])
        self.assertEqual(set(result.imputed_fields), set(self.model.features))


if __name__ == "__main__":
    unittest.main()

