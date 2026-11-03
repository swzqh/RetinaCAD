"""Local inference for the fixed RetinaCAD TabPFN models."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from importlib.metadata import version
from tempfile import TemporaryDirectory
from zipfile import ZipFile, ZIP_STORED
import hashlib
import json
import math
import os

from .paths import model_path

os.environ.update(HF_HUB_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1", TABPFN_DISABLE_TELEMETRY="1")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class PredictionResult:
    probability: float
    linear_predictor: None
    values: dict[str, float | None]
    imputed_fields: tuple[str, ...]
    model_id: str
    outcome_definition: str


class LockedA3Model:
    """Load an approved fixed fit state; no training occurs in this application."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else model_path()
        self.payload = json.loads(self.path.read_text(encoding="utf-8"))
        self.features = tuple(self.payload["feature_order"])
        self.model_id = self.payload["model_id"]
        asset_dir = Path(os.environ.get("RETINACAD_MODEL_DIR", str(self.path.parent)))
        state = asset_dir / self.payload["fit_state_file"]
        if not state.is_file():
            raise FileNotFoundError(
                "The approved TabPFN fit state is required. Request it from the "
                "corresponding author, then set RETINACAD_MODEL_DIR to its folder. "
                "Fit states contain training context and are not included on GitHub."
            )
        checkpoint = Path(os.environ.get("RETINACAD_CHECKPOINT", str(asset_dir / self.payload["checkpoint_file"])))
        if not checkpoint.is_file():
            raise FileNotFoundError(
                "The pinned TabPFN foundation checkpoint is required. Obtain it "
                "from the upstream source in the model manifest and set RETINACAD_CHECKPOINT."
            )
        if _sha256(state) != self.payload["fit_state_sha256"]:
            raise ValueError("Fit state does not match the published model manifest")
        if _sha256(checkpoint) != self.payload["checkpoint_sha256"]:
            raise ValueError("Foundation checkpoint does not match the published model manifest")
        if version("tabpfn") != self.payload["package_version"]:
            raise RuntimeError("Install the pinned TabPFN version from app/requirements.txt")

        import torch
        from tabpfn import TabPFNClassifier

        torch.set_num_threads(4)
        torch.backends.cuda.matmul.allow_tf32 = False
        device = os.environ.get("RETINACAD_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
        # TabPFN 2.1.3 stores the checkpoint's original absolute path. Relocate
        # that path in a private temporary copy, preserving all fitted arrays.
        with TemporaryDirectory(prefix="retinacad-") as folder:
            relocated = Path(folder) / "model.tabpfn_fit"
            with ZipFile(state) as original, ZipFile(relocated, "w", ZIP_STORED) as target:
                for member in original.infolist():
                    data = original.read(member)
                    if member.filename == "init_params.json":
                        params = json.loads(data)
                        params["model_path"] = str(checkpoint.resolve())
                        data = json.dumps(params).encode("utf-8")
                    target.writestr(member.filename, data)
            self.clf = TabPFNClassifier.load_from_fit_state(relocated, device=device)

    def predict(self, values: Mapping[str, Any]) -> PredictionResult:
        import numpy as np

        missing = set(self.features) - set(values)
        unknown = set(values) - set(self.features)
        if missing or unknown:
            raise ValueError(f"Input schema mismatch: missing={sorted(missing)}, unknown={sorted(unknown)}")
        normalized = {}
        absent = []
        row = []
        for feature in self.features:
            value = values[feature]
            if value is None or (isinstance(value, float) and math.isnan(value)):
                if feature not in self.payload["nullable_features"]:
                    raise ValueError(f"{feature} is required")
                row.append(np.nan)
                absent.append(feature)
                normalized[feature] = None
                continue
            number = float(value)
            if not math.isfinite(number):
                raise ValueError(f"{feature} must be finite")
            if feature in ("Male", "HTN", "DM", "Smoke") and number not in (0, 1):
                raise ValueError(f"{feature} must be 0 or 1")
            if feature in ("ratio_AV_DF", "ratio_AV_medianDiameter") and number <= 0:
                raise ValueError(f"{feature} must be positive")
            normalized[feature] = number
            row.append(number)
        probability = float(self.clf.predict_proba(np.asarray(row, float).reshape(1, -1))[0, 1])
        if not 0 <= probability <= 1:
            raise ValueError("Invalid model probability")
        return PredictionResult(probability, None, normalized, tuple(absent), self.model_id, self.payload["outcome_definition"])

    @property
    def internal_auc(self):
        return float(self.payload["internal_validation"]["auc_median"])

    @property
    def apparent_auc(self):
        return float(self.payload["apparent_auc"])
