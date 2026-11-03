"""Verify approved private fit states against the public synthetic test vectors."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from retinacad.model_service import LockedA3Model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=("A3", "A1F", "all"), default="A3")
    args = parser.parse_args()
    results = []
    for name in (("A3", "A1F") if args.model == "all" else (args.model,)):
        model = LockedA3Model(ROOT / "model" / f"{name}_TabPFN_manifest.json")
        vectors = json.loads((ROOT / "model" / f"{name}_test_vectors.json").read_text(encoding="utf-8"))
        errors = [abs(model.predict(v["inputs"]).probability - v["expected_probability"]) for v in vectors]
        assert max(errors) <= 1e-5, (name, max(errors))
        results.append({"model": name, "cases": len(vectors), "maximum_absolute_error": max(errors)})
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
