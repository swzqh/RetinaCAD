#!/usr/bin/env python
"""Verify the locked JSON and reference Python implementation."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("a3_predict", HERE / "a3_predict.py")
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
vectors = json.loads((HERE / "A3_test_vectors.json").read_text(encoding="utf-8"))
errors = []
for vector in vectors:
    observed = module.predict_a3(vector["inputs"])
    error = abs(observed - vector["expected_probability"])
    errors.append(error)
    if error > 1e-12:
        raise AssertionError(f"{vector['case_id']}: {error}")
print(f"PASS: {len(vectors)} vectors; max absolute error={max(errors):.3g}")
