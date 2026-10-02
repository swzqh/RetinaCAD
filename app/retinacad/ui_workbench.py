"""Three-stage Tk desktop workbench for RetinaCAD."""

from __future__ import annotations

import threading
import webbrowser
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageGrab, ImageOps, ImageTk

from .image_qc import ImageQCResult, analyze_image
from .model_service import LockedA3Model, PredictionResult
from .paths import resource_path
from .pipeline_service import LocalPipelineAdapter, PipelineResult
from .report_service import export_report
from .theme import COLORS, FONT, TYPE, configure_theme
from .widgets import InfoButton, ScrollFrame, SegmentedControl, StatusBadge, Surface


FIELD_SPECS = {
    "Age": ("Age", "years", 18, 110),
    "LVEF_pct": ("LVEF", "%", 1, 100),
    "LVMI_g_m2": ("LV mass index", "g/m²", 10, 400),
    "RWT": ("Relative wall thickness", "unitless", 0.05, 1.5),
    "LVDdI_mm_m2": ("LVDd index", "mm/m²", 5, 80),
    "L2ParaFovea": ("Deep parafoveal VD", "device output", 0, 100),
    "L2PeriFovea": ("Deep perifoveal VD", "device output", 0, 100),
    "VD": ("Retinal arterial VD", "0–1", 0, 1),
    "Ratio": ("Artery/vein diameter ratio", "unitless", 0.01, 3),
}

BINARY_LABELS = {
    "Male": ("Sex", (("Female", 0), ("Male", 1))),
    "HTN": ("Hypertension", (("No", 0), ("Yes", 1))),
    "DM": ("Diabetes mellitus", (("No", 0), ("Yes", 1))),
    "Smoke": ("Smoking (study definition)", (("No", 0), ("Yes", 1))),
}

PAGE_LABELS = {
    "image": "Image review",
    "inputs": "Study inputs",
    "result": "Result",
}


ImageToken = tuple[str, int, int]


@dataclass(frozen=True)
class CalculationSnapshot:
    """Case and provenance frozen at the moment a result is calculated."""

    result: PredictionResult
    case_code: str
    image_name: str | None
    image_identity: ImageToken | None
    image_qc: tuple[tuple[str, str], ...]
    phenotype_source: str


class RetinaCADApp:
    """Main desktop application controller."""

    def __init__(self, root: tk.Tk, load_demo: bool = False) -> None:
        self.root = root
        self.model = LockedA3Model()
        self.pipeline = LocalPipelineAdapter()
        self.image_path: Path | None = None
        self.image_qc: ImageQCResult | None = None
        self.preview_source: Image.Image | None = None
        self.preview_photo: ImageTk.PhotoImage | None = None
        self.last_result: PredictionResult | None = None
        self.last_snapshot: CalculationSnapshot | None = None
        self.phenotype_source = "manual"
        self._active_extraction_token: ImageToken | None = None
        self._applying_pipeline_result = False
        self._tracking_ready = False
        self.number_vars: dict[str, tk.StringVar] = {}
        self.binary_vars: dict[str, tk.IntVar] = {
            name: tk.IntVar(value=-1) for name in BINARY_LABELS
        }
        self.case_code_var = tk.StringVar()
        self.app_icon: ImageTk.PhotoImage | None = None
        self.header_icon: ImageTk.PhotoImage | None = None
        self.pages: dict[str, tk.Frame] = {}
        self.nav_buttons: dict[str, tk.Button] = {}
        self.nav_bars: dict[str, tk.Frame] = {}

        configure_theme(root)
        self._configure_window()
        self._load_brand_assets()
        self._build_header()
        self._build_navigation()
        self._build_pages()
        self._bind_change_tracking()
        self._tracking_ready = True
        self._set_icon()
        self._show_page("image")
        self._render_empty_preview()
        if load_demo:
            self.root.after(150, self._load_demo)

    def _configure_window(self) -> None:
        self.root.title("RetinaCAD - Local research workspace")
        self.root.geometry("1280x840")
        self.root.minsize(1040, 700)
        self.root.grid_rowconfigure(2, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
        self.root.bind("<Control-Key-1>", lambda _event: self._show_page("image"))
        self.root.bind("<Control-Key-2>", lambda _event: self._show_page("inputs"))
        self.root.bind("<Control-Key-3>", lambda _event: self._show_page("result"))

    def _load_brand_assets(self) -> None:
        icon_path = resource_path("assets/retinacad_icon.png")
        if not icon_path.is_file():
            return
        with Image.open(icon_path) as source:
            rgba = source.convert("RGBA")
            self.app_icon = ImageTk.PhotoImage(
                rgba.resize((64, 64), Image.Resampling.LANCZOS)
            )
            self.header_icon = ImageTk.PhotoImage(
                rgba.resize((38, 38), Image.Resampling.LANCZOS)
            )

    def _set_icon(self) -> None:
        if self.app_icon is not None:
            self.root.iconphoto(True, self.app_icon)

    def _build_header(self) -> None:
        header = tk.Frame(self.root, bg=COLORS["surface"], height=76)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)

        if self.header_icon is not None:
            tk.Label(
                header, image=self.header_icon, bg=COLORS["surface"], bd=0
            ).grid(row=0, column=0, rowspan=2, padx=(28, 13), pady=18)

        text_pad = (28 if self.header_icon is None else 0, 0)
        tk.Label(
            header,
            text="RetinaCAD",
            bg=COLORS["surface"],
            fg=COLORS["ink"],
            font=(FONT, TYPE["product"], "bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="sw", padx=text_pad, pady=(13, 0))
        tk.Label(
            header,
            text="Retinal-coronary research assessment",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=(FONT, TYPE["support"]),
            anchor="w",
        ).grid(row=1, column=1, sticky="nw", padx=text_pad, pady=(2, 12))

        controls = tk.Frame(header, bg=COLORS["surface"])
        controls.grid(row=0, column=2, rowspan=2, padx=(12, 28), pady=20)
        StatusBadge(controls, "Local only", "success").pack(side="left", padx=(0, 11))
        InfoButton(controls, self._show_model_info).pack(side="left")
        tk.Frame(header, bg=COLORS["line"], height=1).grid(
            row=2, column=0, columnspan=3, sticky="ew"
        )

    def _build_navigation(self) -> None:
        nav = tk.Frame(self.root, bg=COLORS["surface"], height=58)
        nav.grid(row=1, column=0, sticky="ew")
        nav.grid_propagate(False)
        nav.grid_columnconfigure(0, weight=1)

        tabs = tk.Frame(nav, bg=COLORS["surface"])
        tabs.grid(row=0, column=0, sticky="w", padx=28)
        for index, (page_name, label) in enumerate(PAGE_LABELS.items()):
            cell = tk.Frame(tabs, bg=COLORS["surface"])
            cell.grid(row=0, column=index, sticky="ns", padx=(0, 34))
            button = tk.Button(
                cell,
                text=label,
                command=lambda name=page_name: self._show_page(name),
                bg=COLORS["surface"],
                fg=COLORS["muted"],
                activebackground=COLORS["surface"],
                activeforeground=COLORS["primary_text"],
                font=(FONT, TYPE["body"], "bold"),
                relief="flat",
                bd=0,
                highlightbackground=COLORS["surface"],
                highlightcolor=COLORS["primary_text"],
                highlightthickness=2,
                padx=0,
                pady=14,
                cursor="hand2",
                takefocus=True,
            )
            button.pack(fill="x")
            bar = tk.Frame(cell, bg=COLORS["surface"], height=3)
            bar.pack(fill="x")
            self.nav_buttons[page_name] = button
            self.nav_bars[page_name] = bar

        tk.Label(
            nav,
            text="Research use only",
            bg=COLORS["surface"],
            fg=COLORS["subtle"],
            font=(FONT, TYPE["compact"]),
        ).grid(row=0, column=1, sticky="e", padx=28)
        tk.Frame(nav, bg=COLORS["line"], height=1).grid(
            row=1, column=0, columnspan=2, sticky="ew"
        )

    def _build_pages(self) -> None:
        container = tk.Frame(self.root, bg=COLORS["canvas"])
        container.grid(row=2, column=0, sticky="nsew")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        self._build_image_page(container)
        self._build_inputs_page(container)
        self._build_result_page(container)
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")

    def _show_page(self, page_name: str) -> None:
        page = self.pages.get(page_name)
        if page is None:
            return
        page.tkraise()
        for name, button in self.nav_buttons.items():
            selected = name == page_name
            button.configure(fg=COLORS["primary_text"] if selected else COLORS["muted"])
            self.nav_bars[name].configure(
                bg=COLORS["primary"] if selected else COLORS["surface"]
            )

    def _build_image_page(self, container: tk.Misc) -> None:
        page = tk.Frame(container, bg=COLORS["canvas"])
        page.grid_rowconfigure(0, weight=1)
        page.grid_columnconfigure(0, weight=1)
        page.grid_columnconfigure(1, minsize=370)
        self.pages["image"] = page

        stage = tk.Frame(page, bg=COLORS["preview"])
        stage.grid(row=0, column=0, sticky="nsew", padx=(28, 13), pady=24)
        stage.grid_rowconfigure(1, weight=1)
        stage.grid_columnconfigure(0, weight=1)

        stage_header = tk.Frame(stage, bg=COLORS["preview"], height=60)
        stage_header.grid(row=0, column=0, sticky="ew")
        stage_header.grid_propagate(False)
        stage_header.grid_columnconfigure(0, weight=1)
        tk.Label(
            stage_header,
            text="Fundus image",
            bg=COLORS["preview"],
            fg="#F4F7F5",
            font=(FONT, 15, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=17)
        self.image_meta = tk.Label(
            stage_header,
            text="No image selected",
            bg=COLORS["preview"],
            fg="#A9B7AE",
            font=(FONT, TYPE["compact"]),
            anchor="e",
        )
        self.image_meta.grid(row=0, column=1, sticky="e", padx=20, pady=17)

        self.preview = tk.Canvas(
            stage, bg=COLORS["preview"], highlightthickness=0, bd=0
        )
        self.preview.grid(row=1, column=0, sticky="nsew")
        self.preview.bind("<Configure>", lambda _event: self._draw_preview())

        inspector = Surface(page)
        inspector.grid(row=0, column=1, sticky="nsew", padx=(13, 28), pady=24)
        inspector.grid_columnconfigure(0, weight=1)
        inspector.grid_rowconfigure(7, weight=1)

        tk.Label(
            inspector,
            text="Image review",
            bg=COLORS["surface"],
            fg=COLORS["ink"],
            font=(FONT, TYPE["panel_title"], "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=22, pady=(16, 3))
        tk.Label(
            inspector,
            text="Inspect the image before phenotype extraction.",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=(FONT, TYPE["support"]),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 10))
        self.choose_image_button = ttk.Button(
            inspector,
            text="Choose fundus image",
            style="Primary.TButton",
            command=self._choose_image,
        )
        self.choose_image_button.grid(row=2, column=0, sticky="ew", padx=22)

        self.qc_header = tk.Frame(inspector, bg=COLORS["surface"])
        self.qc_header.grid(row=3, column=0, sticky="ew", padx=22, pady=(16, 7))
        self.qc_header.grid_columnconfigure(0, weight=1)
        tk.Label(
            self.qc_header,
            text="Technical checks",
            bg=COLORS["surface"],
            fg=COLORS["ink"],
            font=(FONT, TYPE["section"], "bold"),
        ).grid(row=0, column=0, sticky="w")
        self.qc_badge = StatusBadge(self.qc_header, "Awaiting image", "neutral")
        self.qc_badge.grid(row=0, column=1, sticky="e")

        self.qc_grid = tk.Frame(inspector, bg=COLORS["surface"])
        self.qc_grid.grid(row=4, column=0, sticky="ew", padx=22)
        self.qc_grid.grid_columnconfigure(0, weight=1)
        self._render_empty_qc()

        tk.Frame(inspector, bg=COLORS["line"], height=1).grid(
            row=5, column=0, sticky="ew", padx=22, pady=(12, 12)
        )
        status = self.pipeline.status()
        self.pipeline_title = tk.Label(
            inspector,
            text="Automatic VD and Ratio",
            bg=COLORS["surface"],
            fg=COLORS["primary_text"] if status.available else COLORS["amber"],
            font=(FONT, TYPE["section"], "bold"),
            anchor="w",
        )
        self.pipeline_title.grid(row=6, column=0, sticky="ew", padx=22)

        actions = tk.Frame(inspector, bg=COLORS["surface"])
        actions.grid(row=7, column=0, sticky="sew", padx=22, pady=(5, 14))
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)
        self.pipeline_detail = tk.Label(
            actions,
            text=status.detail,
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=(FONT, TYPE["support"]),
            anchor="nw",
            justify="left",
            wraplength=300,
        )
        self.pipeline_detail.grid(row=0, column=0, columnspan=2, sticky="new")
        self.pipeline_button = ttk.Button(
            actions,
            text="Extract VD + Ratio",
            style="Primary.TButton" if status.available else "Secondary.TButton",
            command=self._run_pipeline,
        )
        self.pipeline_button.grid(row=1, column=0, sticky="ew", pady=(14, 0), padx=(0, 5))
        ttk.Button(
            actions,
            text="Continue",
            style="Secondary.TButton",
            command=lambda: self._show_page("inputs"),
        ).grid(row=1, column=1, sticky="ew", pady=(14, 0), padx=(5, 0))

    def _build_inputs_page(self, container: tk.Misc) -> None:
        page = tk.Frame(container, bg=COLORS["canvas"])
        page.grid_rowconfigure(1, weight=1)
        page.grid_columnconfigure(0, weight=1)
        self.pages["inputs"] = page

        header = tk.Frame(page, bg=COLORS["canvas"])
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(22, 14))
        header.grid_columnconfigure(0, weight=1)
        tk.Label(
            header,
            text="Study inputs",
            bg=COLORS["canvas"],
            fg=COLORS["ink"],
            font=(FONT, TYPE["page_title"], "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            header,
            text="Use the definitions and units from the locked study dataset.",
            bg=COLORS["canvas"],
            fg=COLORS["muted"],
            font=(FONT, TYPE["support"]),
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(5, 0))
        ttk.Button(
            header,
            text="Back to image",
            style="Secondary.TButton",
            command=lambda: self._show_page("image"),
        ).grid(row=0, column=1, rowspan=2, sticky="e")

        scroll = ScrollFrame(page)
        scroll.grid(row=1, column=0, sticky="nsew", padx=(30, 22))
        self.form_scroll = scroll
        form = Surface(scroll.inner)
        form.pack(fill="both", expand=True, padx=(0, 8))
        form.grid_columnconfigure(0, weight=1, uniform="field")
        form.grid_columnconfigure(1, weight=1, uniform="field")

        row = 0
        row = self._section_heading(form, row, "Case and clinical data")
        self._add_text_field(form, row, 0, "Case code (optional)", self.case_code_var)
        self._add_number_field(form, row, 1, "Age")
        row += 1
        self._add_binary_field(form, row, 0, "Male")
        self._add_binary_field(form, row, 1, "HTN")
        row += 1
        self._add_binary_field(form, row, 0, "DM")
        self._add_binary_field(form, row, 1, "Smoke")
        row += 1

        row = self._section_heading(form, row, "Echocardiography")
        for index, key in enumerate(("LVEF_pct", "LVMI_g_m2", "RWT", "LVDdI_mm_m2")):
            self._add_number_field(form, row + index // 2, index % 2, key)
        row += 2

        row = self._section_heading(form, row, "OCTA parameters")
        self._add_number_field(form, row, 0, "L2ParaFovea")
        self._add_number_field(form, row, 1, "L2PeriFovea")
        row += 1
        tk.Label(
            form,
            text="Keep the original study scale. Do not multiply or divide OCTA values by 100.",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=(FONT, TYPE["support"]),
            anchor="w",
        ).grid(row=row, column=0, columnspan=2, sticky="ew", padx=24, pady=(0, 9))
        row += 1

        row = self._section_heading(
            form, row, "Retinal phenotypes", badge="Automatic or manual"
        )
        self._add_number_field(form, row, 0, "VD")
        self._add_number_field(form, row, 1, "Ratio")
        row += 1
        tk.Label(
            form,
            text="VD maps to VD_orig_artery. Ratio maps to ratio_AV_medianDiameter.",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=(FONT, TYPE["support"]),
            anchor="w",
        ).grid(row=row, column=0, columnspan=2, sticky="ew", padx=24, pady=(0, 22))
        scroll.track_focus(form)

        footer = tk.Frame(page, bg=COLORS["canvas"])
        footer.grid(row=2, column=0, sticky="ew", padx=30, pady=(15, 23))
        footer.grid_columnconfigure(0, weight=1)
        self.action_status = tk.Label(
            footer,
            text="Local processing. No data upload.",
            bg=COLORS["canvas"],
            fg=COLORS["muted"],
            font=(FONT, TYPE["support"]),
            anchor="w",
        )
        self.action_status.grid(row=0, column=0, sticky="w")
        ttk.Button(
            footer,
            text="Clear case",
            style="Secondary.TButton",
            command=self._clear_case,
        ).grid(row=0, column=1, padx=(10, 10))
        ttk.Button(
            footer,
            text="Calculate probability",
            style="Primary.TButton",
            command=self._calculate,
        ).grid(row=0, column=2)

    def _build_result_page(self, container: tk.Misc) -> None:
        page = tk.Frame(container, bg=COLORS["canvas"])
        page.grid_rowconfigure(1, weight=1)
        page.grid_columnconfigure(0, weight=1)
        self.pages["result"] = page

        header = tk.Frame(page, bg=COLORS["canvas"])
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(22, 14))
        header.grid_columnconfigure(0, weight=1)
        tk.Label(
            header,
            text="Reference result",
            bg=COLORS["canvas"],
            fg=COLORS["ink"],
            font=(FONT, TYPE["page_title"], "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            header,
            text="Cross-sectional model output under the study definition.",
            bg=COLORS["canvas"],
            fg=COLORS["muted"],
            font=(FONT, TYPE["support"]),
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(5, 0))
        ttk.Button(
            header,
            text="Edit inputs",
            style="Secondary.TButton",
            command=lambda: self._show_page("inputs"),
        ).grid(row=0, column=1, rowspan=2, sticky="e")

        panel = Surface(page)
        panel.grid(row=1, column=0, sticky="nsew", padx=30)
        panel.grid_rowconfigure(0, weight=1)
        panel.grid_columnconfigure(0, weight=3)
        panel.grid_columnconfigure(1, weight=2)

        core = tk.Frame(panel, bg=COLORS["primary_soft"])
        core.grid(row=0, column=0, sticky="nsew")
        core.grid_rowconfigure(0, weight=1)
        core.grid_rowconfigure(4, weight=1)
        core.grid_columnconfigure(0, weight=1)
        tk.Label(
            core,
            text="CAD reference probability",
            bg=COLORS["primary_soft"],
            fg=COLORS["primary_text"],
            font=(FONT, TYPE["section"], "bold"),
            anchor="w",
        ).grid(row=1, column=0, sticky="sw", padx=46)
        self.probability_label = tk.Label(
            core,
            text="--",
            bg=COLORS["primary_soft"],
            fg=COLORS["ink"],
            font=(FONT, 64, "bold"),
            anchor="w",
        )
        self.probability_label.grid(row=2, column=0, sticky="w", padx=43, pady=(4, 2))
        self.result_state = tk.Label(
            core,
            text="No calculation yet",
            bg=COLORS["primary_soft"],
            fg=COLORS["muted"],
            font=(FONT, TYPE["body"]),
            anchor="w",
        )
        self.result_state.grid(row=3, column=0, sticky="nw", padx=46)

        details = tk.Frame(panel, bg=COLORS["surface"])
        details.grid(row=0, column=1, sticky="nsew")
        details.grid_columnconfigure(0, weight=1)
        tk.Label(
            details,
            text="Result details",
            bg=COLORS["surface"],
            fg=COLORS["ink"],
            font=(FONT, TYPE["panel_title"], "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=34, pady=(20, 4))
        tk.Label(
            details,
            text="Locked A3 Ridge model",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=(FONT, TYPE["support"]),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=34)
        tk.Frame(details, bg=COLORS["line"], height=1).grid(
            row=2, column=0, sticky="ew", padx=34, pady=12
        )
        self.result_case_label = self._result_detail_row(details, 3, "Case", "Not specified")
        self.result_vd_label = self._result_detail_row(details, 4, "VD", "--")
        self.result_ratio_label = self._result_detail_row(details, 5, "Ratio", "--")
        self.result_source_label = self._result_detail_row(details, 6, "Phenotypes", "--")
        details.grid_rowconfigure(7, weight=1)
        tk.Label(
            details,
            text=(
                "Research use only. This output does not replace coronary angiography, "
                "clinical judgment, or future-event risk assessment."
            ),
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=(FONT, TYPE["support"]),
            anchor="sw",
            justify="left",
            wraplength=350,
        ).grid(row=7, column=0, sticky="sew", padx=34, pady=(10, 18))

        footer = tk.Frame(page, bg=COLORS["canvas"])
        footer.grid(row=2, column=0, sticky="ew", padx=30, pady=(15, 23))
        footer.grid_columnconfigure(0, weight=1)
        tk.Label(
            footer,
            text="No diagnostic threshold is applied.",
            bg=COLORS["canvas"],
            fg=COLORS["muted"],
            font=(FONT, TYPE["support"]),
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(
            footer,
            text="New case",
            style="Secondary.TButton",
            command=self._clear_case,
        ).grid(row=0, column=1, padx=(10, 10))
        self.export_button = ttk.Button(
            footer,
            text="Export report",
            style="Primary.TButton",
            command=self._export_report,
            state="disabled",
        )
        self.export_button.grid(row=0, column=2)

    def _result_detail_row(self, master: tk.Misc, row: int, label: str, value: str) -> tk.Label:
        line = tk.Frame(master, bg=COLORS["surface"])
        line.grid(row=row, column=0, sticky="ew", padx=34, pady=4)
        line.grid_columnconfigure(1, weight=1)
        tk.Label(
            line,
            text=label,
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=(FONT, TYPE["support"]),
        ).grid(row=0, column=0, sticky="w")
        value_label = tk.Label(
            line,
            text=value,
            bg=COLORS["surface"],
            fg=COLORS["ink"],
            font=(FONT, TYPE["body"], "bold"),
            anchor="e",
        )
        value_label.grid(row=0, column=1, sticky="e")
        return value_label

    def _section_heading(
        self, master: tk.Misc, row: int, title: str, badge: str | None = None
    ) -> int:
        if row > 0:
            tk.Frame(master, height=1, bg=COLORS["line"]).grid(
                row=row, column=0, columnspan=2, sticky="ew", padx=24, pady=(17, 0)
            )
            row += 1
        header = tk.Frame(master, bg=COLORS["surface"])
        header.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=24,
            pady=(22 if row == 0 else 19, 11),
        )
        header.grid_columnconfigure(0, weight=1)
        tk.Label(
            header,
            text=title,
            bg=COLORS["surface"],
            fg=COLORS["ink"],
            font=(FONT, TYPE["section"], "bold"),
        ).grid(row=0, column=0, sticky="w")
        if badge:
            StatusBadge(header, badge, "neutral").grid(row=0, column=1, sticky="e")
        return row + 1

    def _field_frame(self, master: tk.Misc, row: int, column: int) -> tk.Frame:
        frame = tk.Frame(master, bg=COLORS["surface"])
        frame.grid(
            row=row,
            column=column,
            sticky="ew",
            padx=(24 if column == 0 else 12, 12 if column == 0 else 24),
            pady=8,
        )
        frame.grid_columnconfigure(0, weight=1)
        return frame

    def _add_text_field(
        self, master: tk.Misc, row: int, column: int, label: str, variable: tk.StringVar
    ) -> None:
        frame = self._field_frame(master, row, column)
        ttk.Label(frame, text=label, style="Body.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=variable, style="Form.TEntry").grid(
            row=1, column=0, sticky="ew", pady=(7, 0)
        )

    def _add_number_field(self, master: tk.Misc, row: int, column: int, key: str) -> None:
        label, unit, _minimum, _maximum = FIELD_SPECS[key]
        variable = tk.StringVar()
        self.number_vars[key] = variable
        frame = self._field_frame(master, row, column)
        ttk.Label(frame, text=label, style="Body.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(frame, text=unit, style="FieldHint.TLabel").grid(row=0, column=1, sticky="e")
        ttk.Entry(frame, textvariable=variable, style="Form.TEntry").grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(7, 0)
        )

    def _add_binary_field(self, master: tk.Misc, row: int, column: int, key: str) -> None:
        label, choices = BINARY_LABELS[key]
        frame = self._field_frame(master, row, column)
        ttk.Label(frame, text=label, style="Body.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 7)
        )
        SegmentedControl(frame, self.binary_vars[key], choices).grid(row=1, column=0, sticky="ew")

    def _bind_change_tracking(self) -> None:
        self.case_code_var.trace_add(
            "write", lambda *_args: self._on_case_changed(None)
        )
        for key, variable in self.number_vars.items():
            variable.trace_add(
                "write", lambda *_args, field=key: self._on_case_changed(field)
            )
        for key, variable in self.binary_vars.items():
            variable.trace_add(
                "write", lambda *_args, field=key: self._on_case_changed(field)
            )

    def _on_case_changed(self, field: str | None) -> None:
        if field in {"VD", "Ratio"} and not self._applying_pipeline_result:
            self.phenotype_source = "manual"
        if self._tracking_ready:
            self._invalidate_result()

    def _invalidate_result(self) -> None:
        if self.last_result is None and self.last_snapshot is None:
            return
        self.last_result = None
        self.last_snapshot = None
        self.probability_label.configure(text="--", fg=COLORS["ink"])
        self.result_state.configure(text="Inputs changed - recalculate", fg=COLORS["amber"])
        self.result_case_label.configure(text="Not calculated")
        self.result_vd_label.configure(text="--")
        self.result_ratio_label.configure(text="--")
        self.result_source_label.configure(text="--")
        self.export_button.configure(state="disabled")
        self.action_status.configure(
            text="Inputs changed. Recalculate before exporting.", fg=COLORS["amber"]
        )

    @staticmethod
    def _image_identity(path: Path | None) -> ImageToken | None:
        if path is None:
            return None
        try:
            stat = path.stat()
            return (str(path.resolve()), stat.st_size, stat.st_mtime_ns)
        except OSError:
            return None

    def _render_empty_preview(self) -> None:
        self.preview_source = None
        self.preview_photo = None
        self._draw_preview()

    def _draw_preview(self) -> None:
        if not hasattr(self, "preview"):
            return
        width = max(self.preview.winfo_width(), 500)
        height = max(self.preview.winfo_height(), 350)
        self.preview.delete("all")
        self.preview.create_rectangle(0, 0, width, height, fill=COLORS["preview"], outline="")
        if self.preview_source is not None:
            image = self.preview_source.copy()
            image.thumbnail((width - 48, height - 48), Image.Resampling.LANCZOS)
            self.preview_photo = ImageTk.PhotoImage(image)
            self.preview.create_image(width // 2, height // 2, image=self.preview_photo)
            return
        self.preview.create_text(
            width // 2,
            height // 2 - 13,
            text="Choose a color fundus photograph",
            fill="#E7EEE9",
            font=(FONT, 17, "bold"),
        )
        self.preview.create_text(
            width // 2,
            height // 2 + 22,
            text="JPG · PNG · TIF/TIFF",
            fill="#8FA097",
            font=(FONT, TYPE["support"]),
        )

    def _render_empty_qc(self) -> None:
        labels = ("Resolution", "Brightness", "Contrast", "Edge detail")
        self._render_qc_rows([(label, "--", None) for label in labels])

    def _render_qc_rows(self, rows: list[tuple[str, str, bool | None]]) -> None:
        for child in self.qc_grid.winfo_children():
            child.destroy()
        for row_index, (name, value, passed) in enumerate(rows):
            row = tk.Frame(self.qc_grid, bg=COLORS["surface_alt"], height=38)
            row.grid(row=row_index, column=0, sticky="ew", pady=(0, 3))
            row.grid_propagate(False)
            row.grid_columnconfigure(1, weight=1)
            color = COLORS["line"]
            if passed is True:
                color = COLORS["success"]
            elif passed is False:
                color = COLORS["amber"]
            marker = tk.Frame(row, bg=color, width=8, height=8)
            marker.grid(row=0, column=0, padx=(11, 10))
            marker.grid_propagate(False)
            tk.Label(
                row,
                text=name,
                bg=COLORS["surface_alt"],
                fg=COLORS["muted"],
                font=(FONT, TYPE["support"]),
            ).grid(row=0, column=1, sticky="w")
            tk.Label(
                row,
                text=value,
                bg=COLORS["surface_alt"],
                fg=COLORS["ink"],
                font=(FONT, TYPE["support"], "bold"),
            ).grid(row=0, column=2, sticky="e", padx=(8, 11))

    def _choose_image(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select fundus image",
            filetypes=[
                ("Fundus images", "*.jpg *.jpeg *.png *.tif *.tiff"),
                ("All files", "*.*"),
            ],
        )
        if selected:
            self._load_image(Path(selected))

    def _load_image(self, path: Path) -> None:
        try:
            qc = analyze_image(path)
            with Image.open(path) as raw:
                image = ImageOps.exif_transpose(raw).convert("RGB")
        except Exception as exc:
            messagebox.showerror("Unable to load image", str(exc), parent=self.root)
            return
        self._active_extraction_token = None
        self.choose_image_button.configure(state="normal")
        self._invalidate_result()
        if self.phenotype_source == "automatic":
            self._applying_pipeline_result = True
            try:
                self.number_vars["VD"].set("")
                self.number_vars["Ratio"].set("")
            finally:
                self._applying_pipeline_result = False
            self.phenotype_source = "manual"
        self.image_path = path
        self.image_qc = qc
        self.preview_source = image
        size_mb = path.stat().st_size / (1024 * 1024)
        self.image_meta.configure(
            text=f"{path.name}  ·  {qc.width} × {qc.height}  ·  {size_mb:.1f} MB"
        )
        self._draw_preview()
        self._render_qc(qc)

    def _render_qc(self, qc: ImageQCResult) -> None:
        self._render_qc_rows([(item.name, item.value, item.passed) for item in qc.items])
        self.qc_badge.destroy()
        tone = "warning" if qc.needs_review else "success"
        text = "Review needed" if qc.needs_review else "Checks passed"
        self.qc_badge = StatusBadge(self.qc_header, text, tone)
        self.qc_badge.grid(row=0, column=1, sticky="e")

    def _run_pipeline(self) -> None:
        status = self.pipeline.status()
        if not status.available:
            messagebox.showinfo(
                status.title,
                status.detail
                + "\n\nRun setup_wsl_engine.ps1 once to install the local computation environment.",
                parent=self.root,
            )
            return
        if not self.image_path:
            messagebox.showwarning("Image required", "Select a fundus image first.", parent=self.root)
            return
        image_path = self.image_path
        image_token = self._image_identity(image_path)
        if image_token is None:
            messagebox.showerror(
                "Image unavailable",
                "The selected image could not be read. Choose it again.",
                parent=self.root,
            )
            return
        self._active_extraction_token = image_token
        self.choose_image_button.configure(state="disabled")
        self.pipeline_button.configure(text="Extracting...", state="disabled")

        def worker() -> None:
            try:
                result = self.pipeline.run(image_path)
            except Exception as exc:
                self.root.after(
                    0,
                    lambda detail=str(exc), token=image_token: self._pipeline_failed(
                        detail, token
                    ),
                )
            else:
                self.root.after(
                    0,
                    lambda output=result, token=image_token: self._pipeline_completed(
                        output, token
                    ),
                )

        threading.Thread(target=worker, daemon=True).start()

    def _pipeline_completed(self, result: PipelineResult, image_token: ImageToken) -> None:
        if image_token != self._active_extraction_token:
            return
        if image_token != self._image_identity(self.image_path):
            self._active_extraction_token = None
            self.choose_image_button.configure(state="normal")
            self.pipeline_button.configure(text="Extract VD + Ratio", state="normal")
            self.pipeline_title.configure(text="Image changed", fg=COLORS["amber"])
            self.pipeline_detail.configure(
                text="The extraction result was discarded. Run it again for the current image."
            )
            return
        self._active_extraction_token = None
        self.choose_image_button.configure(state="normal")
        self._applying_pipeline_result = True
        try:
            self.number_vars["VD"].set(f"{result.vd:.12g}")
            self.number_vars["Ratio"].set(f"{result.ratio:.12g}")
        finally:
            self._applying_pipeline_result = False
        self.phenotype_source = "automatic"
        self.pipeline_button.configure(text="Phenotypes extracted", state="normal")
        self.pipeline_title.configure(text="VD and Ratio ready", fg=COLORS["success"])
        self.pipeline_detail.configure(text="The extracted values are available in Study inputs.")
        self.action_status.configure(
            text="VD and Ratio are ready. Complete the remaining inputs.", fg=COLORS["success"]
        )
        self._show_page("inputs")

    def _pipeline_failed(self, detail: str, image_token: ImageToken) -> None:
        if image_token != self._active_extraction_token:
            return
        self._active_extraction_token = None
        self.choose_image_button.configure(state="normal")
        self.pipeline_button.configure(text="Extract VD + Ratio", state="normal")
        self.pipeline_title.configure(text="Extraction failed", fg=COLORS["danger"])
        self.pipeline_detail.configure(text="Review the error and try again.")
        messagebox.showerror("Extraction failed", detail, parent=self.root)

    def _collect_values(self) -> dict[str, float]:
        values: dict[str, float] = {}
        errors: list[str] = []
        for key, variable in self.number_vars.items():
            raw = variable.get().strip()
            label, _unit, minimum, maximum = FIELD_SPECS[key]
            if not raw:
                errors.append(f"{label} is required")
                continue
            try:
                value = float(raw)
            except ValueError:
                errors.append(f"{label} is not a valid number")
                continue
            if not minimum <= value <= maximum:
                errors.append(f"{label} must be between {minimum:g} and {maximum:g}")
                continue
            values[key] = value
        for key, variable in self.binary_vars.items():
            value = variable.get()
            if value not in (0, 1):
                errors.append(f"{BINARY_LABELS[key][0]} is not selected")
            else:
                values[key] = float(value)
        if errors:
            summary = "\n".join(f"• {item}" for item in errors[:8])
            if len(errors) > 8:
                summary += f"\n• {len(errors) - 8} more item(s)"
            raise ValueError(summary)
        return values

    def _calculate(self, skip_qc_prompt: bool = False) -> None:
        try:
            values = self._collect_values()
            if (
                self.image_qc
                and self.image_qc.needs_review
                and not skip_qc_prompt
                and not messagebox.askyesno(
                    "Image review required",
                    "The technical check found one or more warnings. Continue after manually reviewing the image and phenotype values?",
                    parent=self.root,
                )
            ):
                return
            result = self.model.predict(values)
        except Exception as exc:
            self.action_status.configure(
                text="Some required inputs need attention.", fg=COLORS["danger"]
            )
            messagebox.showwarning("Check input", str(exc), parent=self.root)
            return
        self.last_result = result
        qc_items: list[tuple[str, str]] = []
        if self.image_qc:
            qc_items.extend((item.name, item.value) for item in self.image_qc.items)
            qc_items.append(
                ("Manual review flag", "Yes" if self.image_qc.needs_review else "No")
            )
        source = (
            "Automatic image extraction"
            if self.phenotype_source == "automatic"
            else "Manual entry"
        )
        self.last_snapshot = CalculationSnapshot(
            result=result,
            case_code=self.case_code_var.get().strip(),
            image_name=self.image_path.name if self.image_path else None,
            image_identity=self._image_identity(self.image_path),
            image_qc=tuple(qc_items),
            phenotype_source=source,
        )
        percent = result.probability * 100
        self.probability_label.configure(text=f"{percent:.1f}%", fg=COLORS["primary_text"])
        self.result_state.configure(text=f"Phenotypes: {source}", fg=COLORS["success"])
        self.result_case_label.configure(text=self.last_snapshot.case_code or "Not specified")
        self.result_vd_label.configure(text=f"{result.values['VD']:g}")
        self.result_ratio_label.configure(text=f"{result.values['Ratio']:g}")
        self.result_source_label.configure(text=source)
        self.export_button.configure(state="normal")
        self.action_status.configure(
            text="Calculation complete. The report is ready to export.", fg=COLORS["success"]
        )
        self._show_page("result")

    def _export_report(self) -> None:
        snapshot = self.last_snapshot
        if snapshot is None:
            return
        directory = filedialog.askdirectory(title="Select report folder")
        if not directory:
            return
        qc_payload = dict(snapshot.image_qc) if snapshot.image_qc else None
        try:
            html_path, json_path = export_report(
                directory=directory,
                result=snapshot.result,
                case_code=snapshot.case_code,
                image_name=snapshot.image_name,
                image_qc=qc_payload,
                phenotype_source=snapshot.phenotype_source,
            )
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc), parent=self.root)
            return
        open_now = messagebox.askyesno(
            "Report exported",
            f"Created:\n{html_path.name}\n{json_path.name}\n\nOpen the HTML report now?",
            parent=self.root,
        )
        if open_now:
            webbrowser.open(html_path.as_uri())

    def _clear_case(self) -> None:
        if self.last_result and not messagebox.askyesno(
            "Clear current case",
            "Clear the image, inputs, and calculated result?",
            parent=self.root,
        ):
            return
        self.case_code_var.set("")
        for variable in self.number_vars.values():
            variable.set("")
        for variable in self.binary_vars.values():
            variable.set(-1)
        self.image_path = None
        self.image_qc = None
        self.last_result = None
        self.last_snapshot = None
        self.phenotype_source = "manual"
        self._active_extraction_token = None
        self.choose_image_button.configure(state="normal")
        self.image_meta.configure(text="No image selected")
        self._render_empty_preview()
        self._render_empty_qc()
        self.qc_badge.destroy()
        self.qc_badge = StatusBadge(self.qc_header, "Awaiting image", "neutral")
        self.qc_badge.grid(row=0, column=1, sticky="e")
        status = self.pipeline.status()
        self.pipeline_title.configure(
            text="Automatic VD and Ratio",
            fg=COLORS["primary_text"] if status.available else COLORS["amber"],
        )
        self.pipeline_detail.configure(text=status.detail)
        self.pipeline_button.configure(text="Extract VD + Ratio", state="normal")
        self.probability_label.configure(text="--", fg=COLORS["ink"])
        self.result_state.configure(text="No calculation yet", fg=COLORS["muted"])
        self.result_case_label.configure(text="Not specified")
        self.result_vd_label.configure(text="--")
        self.result_ratio_label.configure(text="--")
        self.result_source_label.configure(text="--")
        self.export_button.configure(state="disabled")
        self.action_status.configure(
            text="Local processing. No data upload.", fg=COLORS["muted"]
        )
        self._show_page("image")

    def _show_model_info(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Model information")
        dialog.geometry("500x330")
        dialog.minsize(460, 310)
        dialog.configure(bg=COLORS["canvas"])
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        body = tk.Frame(dialog, bg=COLORS["surface"], padx=28, pady=26)
        body.pack(fill="both", expand=True, padx=18, pady=18)
        tk.Label(
            body,
            text="Locked A3 Ridge model",
            bg=COLORS["surface"],
            fg=COLORS["ink"],
            font=(FONT, 18, "bold"),
        ).pack(anchor="w")
        tk.Label(
            body,
            text=f"Internal repeated nested-CV AUC (median): {self.model.internal_auc:.3f}",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=(FONT, TYPE["support"]),
        ).pack(anchor="w", pady=(7, 0))
        tk.Frame(body, bg=COLORS["line"], height=1).pack(fill="x", pady=19)
        tk.Label(
            body,
            text=(
                "Fixed model for local research inference. The software does not "
                "retrain the model or apply a diagnostic threshold."
            ),
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=(FONT, TYPE["support"]),
            justify="left",
            wraplength=365,
        ).pack(anchor="w")
        done_button = ttk.Button(
            body, text="Done", style="Primary.TButton", command=dialog.destroy
        )
        done_button.pack(anchor="e", pady=(20, 0))
        done_button.focus_set()

    def _load_demo(self) -> None:
        demo = {
            "Age": 63,
            "Male": 1,
            "HTN": 1,
            "DM": 0,
            "Smoke": 0,
            "LVEF_pct": 68,
            "LVMI_g_m2": 95,
            "RWT": 0.38,
            "LVDdI_mm_m2": 28,
            "L2ParaFovea": 53,
            "L2PeriFovea": 49,
            "VD": 0.037,
            "Ratio": 1.09,
        }
        self.case_code_var.set("DEMO-001")
        for key, value in demo.items():
            if key in self.number_vars:
                self.number_vars[key].set(str(value))
            elif key in self.binary_vars:
                self.binary_vars[key].set(int(value))
        self._calculate(skip_qc_prompt=True)


def run(
    screenshot_path: str | Path | None = None,
    load_demo: bool = False,
    geometry: str | None = None,
    show_model_info: bool = False,
    initial_page: str | None = None,
) -> None:
    """Start the application and optionally capture a verification screenshot."""
    root = tk.Tk()
    app = RetinaCADApp(root, load_demo=load_demo)
    if geometry:
        root.geometry(geometry)
    if initial_page:
        root.after(300, lambda: app._show_page(initial_page))
    if show_model_info:
        root.after(350, app._show_model_info)
    if screenshot_path:
        destination = Path(screenshot_path)

        def capture() -> None:
            root.update_idletasks()
            root.lift()
            root.update()
            target: tk.Misc = root
            if show_model_info:
                dialogs = [
                    child
                    for child in root.winfo_children()
                    if isinstance(child, tk.Toplevel)
                ]
                if dialogs:
                    target = dialogs[-1]
            target.lift()
            target.update()
            x = target.winfo_rootx()
            y = target.winfo_rooty()
            width = target.winfo_width()
            height = target.winfo_height()
            ImageGrab.grab(bbox=(x, y, x + width, y + height)).save(destination)
            root.destroy()

        root.after(1200, capture)
    root.mainloop()
