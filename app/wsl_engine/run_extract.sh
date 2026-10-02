#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ENGINE_HOME="${RETINACAD_ENGINE_HOME:-$HOME/.local/share/retinacad}"
PYTHON="$ENGINE_HOME/venv/bin/python"
MICROMAMBA="$ENGINE_HOME/micromamba-bin/micromamba"
OCTAVE_PREFIX="$ENGINE_HOME/octave64"
READY_MARKER="$ENGINE_HOME/READY"

check_runtime_files() {
    [[ -f "$READY_MARKER" ]] || return 1
    [[ -x "$PYTHON" ]] || return 1
    [[ -x "$MICROMAMBA" ]] || return 1
    [[ -x "$OCTAVE_PREFIX/bin/octave-cli" ]] || return 1
}

run_engine() {
    TF_CPP_MIN_LOG_LEVEL=3 CUDA_VISIBLE_DEVICES=-1 TF_ENABLE_ONEDNN_OPTS=0 \
        "$MICROMAMBA" run -p "$OCTAVE_PREFIX" \
        "$PYTHON" "$SCRIPT_DIR/extract_retina.py" "$@"
}

if [[ "${1:-}" == "--status" ]]; then
    shift
    if ! check_runtime_files; then
        echo "The RetinaCAD WSL environment is incomplete." >&2
        exit 11
    fi
    exec env TF_CPP_MIN_LOG_LEVEL=3 CUDA_VISIBLE_DEVICES=-1 TF_ENABLE_ONEDNN_OPTS=0 \
        "$MICROMAMBA" run -p "$OCTAVE_PREFIX" \
        "$PYTHON" "$SCRIPT_DIR/extract_retina.py" --self-check --quick-check "$@"
fi

if ! check_runtime_files; then
    echo "The RetinaCAD WSL environment is not installed. Run setup_wsl_engine.ps1." >&2
    exit 11
fi

run_engine "$@"
