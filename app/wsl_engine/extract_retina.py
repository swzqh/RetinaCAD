#!/usr/bin/env python3
"""Single-image, local-only VD and Ratio extraction engine."""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--pipeline-root", type=Path, required=True)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--quick-check", action="store_true")
    return parser.parse_args()


def pipeline_paths(root: Path) -> dict[str, Path]:
    lwnet = root / "lwnet"
    preprocessing = root / "retina-phenotypes" / "preprocessing"
    aria_base = (
        preprocessing
        / "helpers"
        / "MeasureVessels"
        / "src"
        / "petebankhead-ARIA-328853d"
    )
    return {
        "root": root,
        "lwnet": lwnet,
        "lwnet_predict": lwnet / "predict_one_image_av.py",
        "lwnet_weights": lwnet / "experiments" / "big_wnet_drive_av",
        "od_weights": (
            preprocessing
            / "optic-nerve-cnn"
            / "models_weights"
            / "04.02.18_unet_on_ukbiobank_256px"
            / "last_checkpoint.hdf5"
        ),
        "aria_base": aria_base,
        "aria_tests": aria_base / "ARIA_tests",
        "aria_entry": aria_base / "ARIA_tests" / "ARIA_run_tests.m",
    }


def check_environment(paths: dict[str, Path], import_runtime: bool = True) -> None:
    missing = [str(path) for key, path in paths.items() if key != "root" and not path.exists()]
    if missing:
        raise FileNotFoundError("Missing pipeline asset(s): " + "; ".join(missing))
    octave = shutil.which("octave-cli") or shutil.which("octave")
    if octave is None:
        raise RuntimeError("GNU Octave is not installed")
    octave_check = subprocess.run(
        [
            octave,
            "--quiet",
            "--eval",
            (
                "assert(strcmp(version, '6.4.0')); "
                "pkg load image; pkg load statistics;"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if octave_check.returncode != 0:
        detail = (octave_check.stderr or octave_check.stdout).strip()[-1600:]
        raise RuntimeError(f"The pinned Octave runtime is incomplete: {detail}")

    if not import_runtime:
        return

    import cv2  # noqa: F401
    import h5py  # noqa: F401
    import numpy  # noqa: F401
    import pandas  # noqa: F401
    import skimage  # noqa: F401
    import tensorflow  # noqa: F401
    import torch  # noqa: F401
    import torchvision  # noqa: F401


def run_checked(command: list[str], cwd: Path, stage: str) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        detail = (completed.stdout or "No error details").strip()[-3000:]
        raise RuntimeError(f"{stage} failed: {detail}")
    return completed.stdout or ""


def prepare_input(source: Path, raw_image: Path) -> None:
    from PIL import Image, ImageOps, UnidentifiedImageError

    try:
        with Image.open(source) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
            if min(image.size) < 64:
                raise ValueError("Image dimensions are too small")
            image.save(raw_image, format="PNG")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("The input image cannot be decoded") from exc


def segment_vessels(paths: dict[str, Path], raw_image: Path, av_dir: Path) -> Path:
    import torch

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    command = [
        sys.executable,
        str(paths["lwnet_predict"]),
        "--model_path",
        str(paths["lwnet_weights"]),
        "--im_path",
        str(raw_image),
        "--result_path",
        str(av_dir),
        "--device",
        device,
    ]
    run_checked(command, paths["lwnet"], "Artery/vein segmentation")
    generated = av_dir / f"{raw_image.stem}_bin_seg.png"
    av_map = av_dir / raw_image.name
    if not generated.is_file():
        raise RuntimeError("Artery/vein segmentation did not create a binary AV map")
    generated.replace(av_map)
    if not av_map.is_file() or av_map.stat().st_size == 0:
        raise RuntimeError("Artery/vein segmentation created an empty AV map")
    return av_map


def build_optic_disc_model():
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    import tensorflow as tf

    layers = tf.keras.layers
    inputs = layers.Input((256, 256, 3))
    conv1 = layers.Conv2D(32, 3, activation="relu", padding="same")(inputs)
    conv1 = layers.Dropout(0.3)(conv1)
    conv1 = layers.Conv2D(32, 3, activation="relu", padding="same")(conv1)
    pool1 = layers.MaxPooling2D((2, 2))(conv1)

    conv2 = layers.Conv2D(64, 3, activation="relu", padding="same")(pool1)
    conv2 = layers.Dropout(0.3)(conv2)
    conv2 = layers.Conv2D(64, 3, activation="relu", padding="same")(conv2)
    pool2 = layers.MaxPooling2D((2, 2))(conv2)

    conv3 = layers.Conv2D(64, 3, activation="relu", padding="same")(pool2)
    conv3 = layers.Dropout(0.3)(conv3)
    conv3 = layers.Conv2D(64, 3, activation="relu", padding="same")(conv3)
    pool3 = layers.MaxPooling2D((2, 2))(conv3)

    conv4 = layers.Conv2D(64, 3, activation="relu", padding="same")(pool3)
    conv4 = layers.Dropout(0.3)(conv4)
    conv4 = layers.Conv2D(64, 3, activation="relu", padding="same")(conv4)
    pool4 = layers.MaxPooling2D((2, 2))(conv4)

    conv5 = layers.Conv2D(64, 3, activation="relu", padding="same")(pool4)
    conv5 = layers.Dropout(0.3)(conv5)
    conv5 = layers.Conv2D(64, 3, activation="relu", padding="same")(conv5)

    def up_block(value, skip, filters):
        value = layers.UpSampling2D((2, 2))(value)
        value = layers.Concatenate(axis=-1)([value, skip])
        value = layers.Conv2D(filters, 3, activation="relu", padding="same")(value)
        value = layers.Dropout(0.3)(value)
        return layers.Conv2D(filters, 3, activation="relu", padding="same")(value)

    conv6 = up_block(conv5, conv4, 64)
    conv7 = up_block(conv6, conv3, 64)
    conv8 = up_block(conv7, conv2, 64)
    conv9 = up_block(conv8, conv1, 32)
    output = layers.Conv2D(1, 1, activation="sigmoid", padding="same")(conv9)
    return tf.keras.Model(inputs, output)


def locate_optic_disc(raw_image: Path, weights: Path, output_csv: Path) -> None:
    import cv2
    import numpy as np
    import pandas as pd
    from skimage.exposure import equalize_adapthist

    image = cv2.imread(str(raw_image), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Optic-disc stage could not decode the image")
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    height, width = image.shape[:2]
    difference = width - height
    if difference > 0:
        left = int(np.floor(difference / 2))
        right = int(np.ceil(difference / 2))
        top = bottom = 0
        square = image[:, left : width - right]
    elif difference < 0:
        top = int(np.floor(abs(difference) / 2))
        bottom = int(np.ceil(abs(difference) / 2))
        left = right = 0
        square = image[top : height - bottom, :]
    else:
        top = bottom = left = right = 0
        square = image

    resized = cv2.resize(square, (256, 256), interpolation=cv2.INTER_LINEAR)
    normalized = equalize_adapthist(resized.astype(np.float32) / 255.0)
    model = build_optic_disc_model()
    try:
        model.load_weights(weights)
    except Exception as exc:
        raise RuntimeError(f"Optic-disc model weights are incompatible: {exc}") from exc
    prediction = model.predict(normalized[None, ...], verbose=0)[0, :, :, 0]
    binary = (prediction > 0.5).astype(np.uint8) * 255
    count, _labels, stats, _centroids = cv2.connectedComponentsWithStats(binary)
    candidates: list[tuple[float, int, int, int, int]] = []
    for x, y, box_width, box_height, area in stats[1:count]:
        center_y = y + box_height / 2
        if 256 / 3 < center_y < 512 / 3:
            candidates.append((float(area), int(x), int(y), int(box_width), int(box_height)))
    if not candidates:
        raise RuntimeError("Optic-disc localization found no plausible disc candidate")
    _area, x, y, box_width, box_height = max(candidates)
    scale = square.shape[0] / 256.0
    center_x = (x + box_width / 2) * scale + left
    center_y = (y + box_height / 2) * scale + top
    measured_width = box_width * scale
    measured_height = box_height * scale
    measured_area = _area * scale * scale
    frame = pd.DataFrame(
        [
            {
                "image": raw_image.name,
                "width": measured_width,
                "height": measured_height,
                "area": measured_area,
                "center_x_y": f"({center_x}, {center_y})",
                "x": center_x,
                "y": center_y,
            }
        ]
    ).set_index("image")
    frame.to_csv(output_csv)


def octave_quote(path: Path) -> str:
    return str(path).replace("'", "''")


def measure_vessels(
    paths: dict[str, Path], raw_root: Path, av_dir: Path, aria_output: Path, image_list: Path
) -> Path:
    aria_tests = paths["aria_tests"]
    arguments = (
        "pkg load image; pkg load statistics; "
        f"addpath(genpath('{octave_quote(paths['aria_base'])}')); "
        "ARIA_run_tests(0, 'REVIEW', "
        f"'{octave_quote(raw_root)}', '{octave_quote(av_dir)}', 'all', 0.79, "
        f"'{octave_quote(aria_tests)}', 1, 1, -1, 999999, -1, 999999, "
        f"'{octave_quote(aria_output)}', 'CLRIS', '{octave_quote(image_list)}');"
    )
    octave_log = run_checked(
        ["octave", "--no-gui", "--quiet", "--eval", arguments],
        aria_tests,
        "ARIA vessel measurement",
    )
    stats_file = aria_output / "case_all_segmentStats.tsv"
    if not stats_file.is_file() or stats_file.stat().st_size == 0:
        detail = octave_log.strip()[-3000:] or "No Octave output"
        raise RuntimeError(
            "ARIA did not create case_all_segmentStats.tsv. Octave output: " + detail
        )
    return stats_file


def compute_vd(av_map: Path, mask_radius: int = 660) -> float:
    import numpy as np
    from PIL import Image

    with Image.open(av_map) as opened:
        rgb = np.asarray(opened.convert("RGB"), dtype=np.float64)
    height, width = rgb.shape[:2]
    yy, xx = np.ogrid[:height, :width]
    mask = (xx - width // 2) ** 2 + (yy - height // 2) ** 2 <= mask_radius**2
    if not np.any(mask):
        raise RuntimeError("The vascular-density mask is empty")
    return float(np.mean(rgb[:, :, 0][mask]) / 255.0)


def compute_ratio(stats_file: Path) -> float:
    import pandas as pd

    frame = pd.read_csv(stats_file, delimiter="\t")
    required = {"medianDiameter", "AVScore"}
    if not required.issubset(frame.columns):
        raise RuntimeError("ARIA segment statistics have an unexpected schema")
    positive = frame.loc[frame["AVScore"] > 0, "medianDiameter"].median()
    negative = frame.loc[frame["AVScore"] < 0, "medianDiameter"].median()
    ratio = float(positive / negative)
    if not math.isfinite(ratio):
        score = frame["AVScore"]
        raise RuntimeError(
            "ARIA did not yield finite artery and vein diameter medians "
            f"(positive={int((score > 0).sum())}, negative={int((score < 0).sum())}, "
            f"zero={int((score == 0).sum())}, missing={int(score.isna().sum())}, "
            f"range={score.min()}..{score.max()})"
        )
    return ratio


def extract(source: Path, output: Path, paths: dict[str, Path]) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"Input image not found: {source}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="retinacad_", dir="/tmp") as temporary:
        job = Path(temporary)
        raw_root = job / "raw"
        raw_dir = raw_root / "CLRIS"
        av_dir = job / "av"
        aria_output = job / "aria"
        optic_dir = job / "optic_disc"
        for directory in (raw_dir, av_dir, aria_output, optic_dir):
            directory.mkdir(parents=True, exist_ok=True)
        raw_image = raw_dir / "case.png"
        image_list = job / "all_images.txt"
        image_list.write_text("case.png\n", encoding="utf-8")

        prepare_input(source, raw_image)
        av_map = segment_vessels(paths, raw_image, av_dir)
        locate_optic_disc(raw_image, paths["od_weights"], optic_dir / "od_all.csv")
        stats_file = measure_vessels(paths, raw_root, av_dir, aria_output, image_list)
        vd = compute_vd(av_map)
        ratio = compute_ratio(stats_file)
        if not (0 <= vd <= 1 and 0 < ratio <= 3):
            raise RuntimeError("Extracted phenotype values are outside validation limits")
        payload = {
            "schema_version": "1.0",
            "VD": vd,
            "Ratio": ratio,
            "source_variables": {
                "VD": "VD_orig_artery",
                "Ratio": "ratio_AV_medianDiameter",
            },
        }
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    paths = pipeline_paths(args.pipeline_root.resolve())
    check_environment(paths, import_runtime=not args.quick_check)
    if args.self_check:
        print("RetinaCAD WSL engine: ready")
        return 0
    if args.input is None or args.output is None:
        raise ValueError("--input and --output are required")
    extract(args.input.resolve(), args.output.resolve(), paths)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"RetinaCAD engine error: {exc}", file=sys.stderr)
        raise SystemExit(1)
