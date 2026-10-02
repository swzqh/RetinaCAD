#!/usr/bin/env python
"""Reference implementation for the locked A3 model."""
from __future__ import annotations
import json
import math
from pathlib import Path

MODEL = json.loads((Path(__file__).parent / "A3_locked_model.json").read_text(encoding="utf-8"))


def predict_a3(values: dict[str, float | int | None]) -> float:
    expected = [row["feature"] for row in MODEL["standardized_formula"]["features"]]
    missing_fields = [name for name in expected if name not in values]
    unknown_fields = [name for name in values if name not in expected]
    if missing_fields or unknown_fields:
        raise ValueError(f"missing={missing_fields}; unknown={unknown_fields}")
    eta = float(MODEL["raw_scale_formula"]["intercept"])
    coefficients = MODEL["raw_scale_formula"]["coefficients"]
    rows = {row["feature"]: row for row in MODEL["standardized_formula"]["features"]}
    for name in expected:
        value = values[name]
        if value is None or (isinstance(value, float) and math.isnan(value)):
            value = rows[name]["missing_value_fill"]
        value = float(value)
        if rows[name]["type"] == "binary" and value not in (0.0, 1.0):
            raise ValueError(f"{name} must be 0 or 1")
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
        eta += float(coefficients[name]) * value
    if eta >= 0:
        return 1.0 / (1.0 + math.exp(-eta))
    exp_eta = math.exp(eta)
    return exp_eta / (1.0 + exp_eta)
