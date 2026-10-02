"""Console entry point for RetinaCAD."""

from __future__ import annotations

import argparse

from retinacad.ui_workbench import run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local RetinaCAD desktop app")
    parser.add_argument("--screenshot", help="capture the window and exit")
    parser.add_argument("--demo", action="store_true", help="load synthetic demo inputs")
    parser.add_argument("--geometry", help="override window geometry for UI checks")
    parser.add_argument("--model-info", action="store_true", help="open model information")
    parser.add_argument(
        "--page",
        choices=("image", "inputs", "result"),
        help="open a specific workspace for UI checks",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(
        screenshot_path=args.screenshot,
        load_demo=args.demo,
        geometry=args.geometry,
        show_model_info=args.model_info,
        initial_page=args.page,
    )
