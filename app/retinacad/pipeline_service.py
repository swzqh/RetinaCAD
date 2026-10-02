"""Hidden local WSL adapter for retinal phenotype extraction."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import tempfile
import re
from dataclasses import dataclass
from pathlib import Path

from .paths import resource_path


@dataclass(frozen=True)
class PipelineStatus:
    """Availability of the automatic phenotype extractor."""

    available: bool
    title: str
    detail: str


@dataclass(frozen=True)
class PipelineResult:
    """Automatic retinal phenotype extraction output."""

    vd: float
    ratio: float
    av_map: Path | None = None
    optic_disc_preview: Path | None = None


class LocalPipelineAdapter:
    """Invoke the packaged pipeline through a background WSL process."""

    ENV_NAME = "RETINACAD_PIPELINE_COMMAND"
    DISTRO_ENV_NAME = "RETINACAD_WSL_DISTRIBUTION"
    DEFAULT_DISTRO = "Ubuntu-24.04"

    def __init__(
        self,
        command_template: str | None = None,
        distro: str | None = None,
        engine_script: Path | None = None,
        pipeline_root: Path | None = None,
        check_engine: bool = True,
    ) -> None:
        self.command_template = (
            os.environ.get(self.ENV_NAME, "")
            if command_template is None
            else command_template
        )
        self.distro = distro or os.environ.get(
            self.DISTRO_ENV_NAME, self.DEFAULT_DISTRO
        )
        self.engine_script = engine_script or resource_path("wsl_engine/run_extract.sh")
        self.pipeline_root = pipeline_root or resource_path("retina_pipeline")
        self.check_engine = check_engine
        self._cached_status: PipelineStatus | None = None

    def status(self, refresh: bool = False) -> PipelineStatus:
        if self.command_template.strip():
            return PipelineStatus(
                True,
                "Automatic extraction ready",
                "Using a configured local command; no image is uploaded.",
            )
        if self._cached_status is not None and not refresh:
            return self._cached_status
        status = self._detect_wsl_engine()
        self._cached_status = status
        return status

    def _detect_wsl_engine(self) -> PipelineStatus:
        if os.name != "nt":
            return PipelineStatus(
                False,
                "Windows WSL engine unavailable",
                "Automatic extraction is supported by the Windows build.",
            )
        if not shutil.which("wsl.exe"):
            return PipelineStatus(
                False,
                "WSL is not installed",
                "Install WSL 2 and the Ubuntu-24.04 distribution first.",
            )
        if not self.engine_script.is_file() or not self.pipeline_root.is_dir():
            return PipelineStatus(
                False,
                "Pipeline files are missing",
                "Reinstall RetinaCAD with the bundled WSL engine files.",
            )
        if self.check_engine:
            try:
                command = self._wsl_base_command() + [
                    "bash",
                    self._to_wsl_path(self.engine_script),
                    "--status",
                    "--pipeline-root",
                    self._to_wsl_path(self.pipeline_root),
                ]
                completed = self._run_hidden(command, timeout_seconds=45)
            except Exception as exc:
                return PipelineStatus(
                    False,
                    "WSL engine setup required",
                    f"Run setup_wsl_engine.ps1 once. Engine check: {exc}",
                )
            if completed.returncode != 0:
                detail = self._failure_detail(completed)
                return PipelineStatus(
                    False,
                    "WSL engine setup required",
                    f"Run setup_wsl_engine.ps1 once. {detail}",
                )
        return PipelineStatus(
            True,
            "Automatic extraction ready",
            "Local WSL engine ready. Offline processing.",
        )

    def run(self, image_path: Path, timeout_seconds: int = 1800) -> PipelineResult:
        """Run the local engine and validate its strict JSON output."""
        image_path = Path(image_path).resolve()
        if not image_path.is_file():
            raise FileNotFoundError(f"Image not found: {image_path}")
        if self.command_template.strip():
            return self._run_configured_command(image_path, timeout_seconds)
        status = self.status(refresh=True)
        if not status.available:
            raise RuntimeError(status.detail)

        with tempfile.TemporaryDirectory(prefix="retinacad_") as temp_dir:
            result_path = Path(temp_dir) / "phenotypes.json"
            command = self._wsl_base_command() + [
                "bash",
                self._to_wsl_path(self.engine_script),
                "--input",
                self._to_wsl_path(image_path),
                "--output",
                self._to_wsl_path(result_path),
                "--pipeline-root",
                self._to_wsl_path(self.pipeline_root),
            ]
            completed = self._run_hidden(command, timeout_seconds=timeout_seconds)
            return self._read_result(completed, result_path)

    def _run_configured_command(
        self, image_path: Path, timeout_seconds: int
    ) -> PipelineResult:
        with tempfile.TemporaryDirectory(prefix="retinacad_") as temp_dir:
            result_path = Path(temp_dir) / "phenotypes.json"
            command = self._build_command(image_path, result_path)
            completed = self._run_hidden(command, timeout_seconds=timeout_seconds)
            return self._read_result(completed, result_path)

    def _read_result(
        self, completed: subprocess.CompletedProcess[str], result_path: Path
    ) -> PipelineResult:
        if completed.returncode != 0:
            raise RuntimeError(f"Automatic extraction failed: {self._failure_detail(completed)}")
        if not result_path.exists():
            raise RuntimeError("Automatic extraction did not create phenotypes.json")
        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            vd = float(payload["VD"])
            ratio = float(payload["Ratio"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("Automatic extraction returned invalid JSON") from exc
        if not (0 <= vd <= 1 and 0 < ratio <= 3):
            raise ValueError("Automatic extraction output is outside validation limits")
        return PipelineResult(vd=vd, ratio=ratio)

    def _wsl_base_command(self) -> list[str]:
        return ["wsl.exe", "-d", self.distro, "--"]

    def _to_wsl_path(self, path: Path) -> str:
        windows_path = str(Path(path).resolve())
        drive_match = re.match(r"^([A-Za-z]):[\\/](.*)$", windows_path)
        if drive_match:
            drive = drive_match.group(1).lower()
            remainder = drive_match.group(2).replace("\\", "/")
            return f"/mnt/{drive}/{remainder}"
        completed = self._run_hidden(
            self._wsl_base_command() + ["wslpath", "-a", windows_path],
            timeout_seconds=15,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"Unable to map Windows path into WSL: {self._failure_detail(completed)}")
        mapped = completed.stdout.strip().splitlines()
        if not mapped:
            raise RuntimeError("WSL returned an empty mapped path")
        return mapped[-1]

    @staticmethod
    def _failure_detail(completed: subprocess.CompletedProcess[str]) -> str:
        detail = (completed.stderr or completed.stdout or "No error details").strip()
        return detail[-1600:]

    @staticmethod
    def _run_hidden(
        command: list[str], timeout_seconds: int
    ) -> subprocess.CompletedProcess[str]:
        kwargs: dict[str, object] = {}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        try:
            return subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                shell=False,
                **kwargs,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"The local extraction engine exceeded {timeout_seconds} seconds"
            ) from exc

    def _build_command(self, image_path: Path, result_path: Path) -> list[str]:
        """Build the backward-compatible explicit command adapter."""
        template = self.command_template.strip()
        if template.startswith("["):
            parts = json.loads(template)
        else:
            parts = shlex.split(template, posix=os.name != "nt")
        return [
            str(part).replace("{input}", str(image_path)).replace(
                "{output}", str(result_path)
            )
            for part in parts
        ]
