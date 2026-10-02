from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from retinacad.image_qc import analyze_image


class ImageQCTests(unittest.TestCase):
    def test_reads_supported_image_and_reports_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "synthetic_qc.png"
            image = Image.new("RGB", (1000, 900), "#171717")
            draw = ImageDraw.Draw(image)
            for offset in range(80, 900, 80):
                draw.line((offset, 80, 1000 - offset // 2, 820), fill="#D45A45", width=8)
                draw.line((80, offset, 920, 900 - offset // 3), fill="#4C85B8", width=5)
            image.save(path)
            result = analyze_image(path)
            self.assertEqual((result.width, result.height), (1000, 900))
            self.assertEqual(len(result.items), 4)
            self.assertGreaterEqual(result.contrast, 0)

    def test_flat_image_is_flagged_for_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "flat.png"
            Image.new("RGB", (900, 900), "#777777").save(path)
            result = analyze_image(path)
            self.assertTrue(result.needs_review)

    def test_rejects_unsupported_extension(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "not_image.txt"
            path.write_text("not an image", encoding="utf-8")
            with self.assertRaises(ValueError):
                analyze_image(path)


if __name__ == "__main__":
    unittest.main()

