from __future__ import annotations

import tkinter as tk
import unittest
from unittest.mock import patch

from retinacad.pipeline_service import PipelineResult, PipelineStatus
from retinacad.ui_workbench import RetinaCADApp


class UIStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.status_patch = patch(
            "retinacad.ui_workbench.LocalPipelineAdapter.status",
            return_value=PipelineStatus(True, "Ready", "Local engine ready."),
        )
        self.status_patch.start()
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = RetinaCADApp(self.root)
        self.app._load_demo()

    def tearDown(self) -> None:
        self.root.destroy()
        self.status_patch.stop()

    def test_input_change_invalidates_calculated_result(self) -> None:
        self.assertIsNotNone(self.app.last_snapshot)
        self.assertEqual(str(self.app.export_button.cget("state")), "normal")

        self.app.number_vars["Age"].set("64")

        self.assertIsNone(self.app.last_snapshot)
        self.assertIsNone(self.app.last_result)
        self.assertEqual(str(self.app.export_button.cget("state")), "disabled")
        self.assertEqual(self.app.probability_label.cget("text"), "--")

    def test_stale_extraction_result_is_discarded(self) -> None:
        token = ("stale-image", 100, 123456)
        self.app._active_extraction_token = token
        before = (
            self.app.number_vars["VD"].get(),
            self.app.number_vars["Ratio"].get(),
        )

        self.app._pipeline_completed(PipelineResult(vd=0.05, ratio=1.2), token)

        after = (
            self.app.number_vars["VD"].get(),
            self.app.number_vars["Ratio"].get(),
        )
        self.assertEqual(after, before)
        self.assertIsNone(self.app._active_extraction_token)
        self.assertEqual(str(self.app.choose_image_button.cget("state")), "normal")


if __name__ == "__main__":
    unittest.main()
