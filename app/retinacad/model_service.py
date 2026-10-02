"""Strict inference service for the locked A3 Ridge model."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .paths import model_path


@dataclass(frozen=True)
class PredictionResult:
    """A single locked-model prediction."""

    probability: float
    linear_predictor: float
    values: dict[str, float]
    imputed_fields: tuple[str, ...]
    model_id: str
    outcome_definition: str


class LockedA3Model:
    """Load and evaluate the immutable A3 model JSON."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or model_path()
        if not self.path.exists():
            raise FileNotFoundError(f"Locked model not found: {self.path}")
        self.payload = json.loads(self.path.read_text(encoding="utf-8"))
        self.rows = self.payload["standardized_formula"]["features"]
        self.features = tuple(row["feature"] for row in self.rows)
        self.row_by_name = {row["feature"]: row for row in self.rows}
        self.coefficients = self.payload["raw_scale_formula"]["coefficients"]
        self.intercept = float(self.payload["raw_scale_formula"]["intercept"])
        self.model_id = str(self.payload["model_id"])

    def predict(self, values: Mapping[str, Any]) -> PredictionResult:
        """Return a probability after strict schema and value validation."""
        missing = [name for name in self.features if name not in values]
        unknown = [name for name in values if name not in self.features]
        if missing or unknown:
            raise ValueError(f"Input schema mismatch: missing {missing}; unknown {unknown}")

        eta = self.intercept
        normalized: dict[str, float] = {}
        imputed: list[str] = []
        for name in self.features:
            row = self.row_by_name[name]
            value = values[name]
            if value is None or (
                isinstance(value, float) and math.isnan(value)
            ):
                value = row["missing_value_fill"]
                imputed.append(name)
            if isinstance(value, bool):
                value = int(value)
            try:
                number = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{name} must be numeric") from exc
            if not math.isfinite(number):
                raise ValueError(f"{name} must be finite")
            if row["type"] == "binary" and number not in (0.0, 1.0):
                raise ValueError(f"{name} must be 0 or 1")
            normalized[name] = number
            eta += float(self.coefficients[name]) * number

        if eta >= 0:
            probability = 1.0 / (1.0 + math.exp(-eta))
        else:
            exp_eta = math.exp(eta)
            probability = exp_eta / (1.0 + exp_eta)

        return PredictionResult(
            probability=probability,
            linear_predictor=eta,
            values=normalized,
            imputed_fields=tuple(imputed),
            model_id=self.model_id,
            outcome_definition=str(self.payload["outcome_definition"]),
        )

    @property
    def internal_auc(self) -> float:
        """Return the repeated nested-CV median AUC."""
        return float(
            self.payload["internal_validation_performance"]["auc_median"]
        )

    @property
    def apparent_auc(self) -> float:
        """Return the apparent development-cohort AUC."""
        return float(self.payload["apparent_full_cohort_performance"]["auc"])
