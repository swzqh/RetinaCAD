#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ENGINE_HOME="${RETINACAD_ENGINE_HOME:-$HOME/.local/share/retinacad}"
VENV="$ENGINE_HOME/venv"
MICROMAMBA_DIR="$ENGINE_HOME/micromamba-bin"
MICROMAMBA="$MICROMAMBA_DIR/micromamba"
OCTAVE_PREFIX="$ENGINE_HOME/octave64"

download_and_verify() {
    local url="$1"
    local expected_sha256="$2"
    local destination="$3"
    curl --location --fail --retry 3 --silent --show-error \
        --output "$destination" "$url"
    printf '%s  %s\n' "$expected_sha256" "$destination" | sha256sum --check --status
}

install_octave_package() {
    local package_name="$1"
    local archive_name="$2"
    local url="$3"
    local expected_sha256="$4"
    local archive="/tmp/$archive_name"
    if "$MICROMAMBA" run -p "$OCTAVE_PREFIX" octave-cli --quiet \
        --eval "pkg load $package_name" >/dev/null 2>&1; then
        return
    fi
    download_and_verify "$url" "$expected_sha256" "$archive"
    CC=/usr/bin/gcc CXX=/usr/bin/g++ \
        "$MICROMAMBA" run -p "$OCTAVE_PREFIX" octave-cli --quiet \
        --eval "pkg('install', '$archive')"
    rm -f "$archive"
}

mkdir -p "$ENGINE_HOME" "$MICROMAMBA_DIR"

if [[ ! -x "$MICROMAMBA" ]]; then
    curl --location --fail --retry 3 --silent --show-error \
        https://micro.mamba.pm/api/micromamba/linux-64/latest \
        | tar --extract --bzip2 --directory "$MICROMAMBA_DIR" \
            --strip-components=1 bin/micromamba
fi

if [[ ! -x "$OCTAVE_PREFIX/bin/octave-cli" ]]; then
    "$MICROMAMBA" create --yes --prefix "$OCTAVE_PREFIX" \
        --channel conda-forge "octave=6.4.0"
fi

install_octave_package \
    image image-2.14.0.tar.gz \
    https://downloads.sourceforge.net/octave/image-2.14.0.tar.gz \
    7515ea211a8cb8ef5d9d3bab85a36e9df5475e8b05a919a078e0d52746077133
install_octave_package \
    io io-2.6.4.tar.gz \
    https://downloads.sourceforge.net/octave/io-2.6.4.tar.gz \
    a74a400bbd19227f6c07c585892de879cd7ae52d820da1f69f1a3e3e89452f5a
install_octave_package \
    statistics statistics-1.4.3.tar.gz \
    https://downloads.sourceforge.net/octave/statistics-1.4.3.tar.gz \
    9801b8b4feb26c58407c136a9379aba1e6a10713829701bb3959d9473a67fa05

python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip setuptools wheel
"$VENV/bin/python" -m pip install --requirement "$SCRIPT_DIR/requirements-wsl.txt"
"$VENV/bin/python" -m pip install \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.8.0 torchvision==0.23.0

TF_CPP_MIN_LOG_LEVEL=3 CUDA_VISIBLE_DEVICES=-1 TF_ENABLE_ONEDNN_OPTS=0 \
    "$MICROMAMBA" run -p "$OCTAVE_PREFIX" \
    "$VENV/bin/python" "$SCRIPT_DIR/extract_retina.py" \
    --self-check --pipeline-root "$1"
touch "$ENGINE_HOME/READY"
echo "RetinaCAD WSL engine setup completed."
