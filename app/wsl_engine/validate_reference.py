#!/usr/bin/env python3
"""Compare the WSL measurement layer with public reference artifacts."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from extract_retina import (
    compute_ratio,
    compute_vd,
    measure_vessels,
    pipeline_paths,
    prepare_input,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--pipeline-root", type=Path, required=True)
    args = parser.parse_args()

    reference_av = args.reference_dir / "17_test.png"
    reference_stats = args.reference_dir / "17_test_all_segmentStats.tsv"
    if not reference_av.is_file() or not reference_stats.is_file():
        raise FileNotFoundError("Public reference AV map or segment table is missing")

    with tempfile.TemporaryDirectory(prefix="retinacad_reference_", dir="/tmp") as temp:
        job = Path(temp)
        raw_root = job / "raw"
        raw_dir = raw_root / "CLRIS"
        av_dir = job / "av"
        aria_dir = job / "aria"
        for directory in (raw_dir, av_dir, aria_dir):
            directory.mkdir(parents=True)
        raw_image = raw_dir / "case.png"
        av_map = av_dir / "case.png"
        image_list = job / "all_images.txt"
        image_list.write_text("case.png\n", encoding="utf-8")
        prepare_input(args.image, raw_image)
        shutil.copy2(reference_av, av_map)
        measured_stats = measure_vessels(
            pipeline_paths(args.pipeline_root),
            raw_root,
            av_dir,
            aria_dir,
            image_list,
        )
        print(
            json.dumps(
                {
                    "reference_artifact_VD": compute_vd(av_map),
                    "reference_table_Ratio": compute_ratio(reference_stats),
                    "octave_remeasurement_Ratio": compute_ratio(measured_stats),
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
