"""Visual theme for the RetinaCAD desktop application."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


COLORS = {
    "canvas": "#F2F6F3",
    "surface": "#FFFFFF",
    "surface_alt": "#E8F0EB",
    "ink": "#17221B",
    "muted": "#5C6A61",
    "subtle": "#637168",
    "line": "#D5E1D9",
    "primary": "#33915B",
    "primary_text": "#287A4A",
    "primary_action": "#287A4A",
    "primary_hover": "#1F633C",
    "primary_soft": "#E4F2E9",
    "amber": "#8A5A00",
    "amber_soft": "#FFF6DF",
    "danger": "#B42318",
    "danger_soft": "#FCEBE9",
    "success": "#18794E",
    "success_soft": "#E4F3E9",
    "dark": "#17221B",
    "preview": "#18221D",
    "result_surface": "#F4FAF6",
}

FONT = "Segoe UI"

# A deliberately generous desktop type scale for repeated clinical use.
TYPE = {
    "product": 20,
    "page_title": 25,
    "panel_title": 20,
    "section": 14,
    "body": 12,
    "support": 11,
    "compact": 10,
}


def configure_theme(root: tk.Tk) -> ttk.Style:
    """Configure the restrained green clinical-workbench theme."""
    root.configure(bg=COLORS["canvas"])
    root.option_add("*Font", (FONT, TYPE["body"]))
    root.option_add("*tearOff", False)
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure("App.TFrame", background=COLORS["canvas"])
    style.configure("Surface.TFrame", background=COLORS["surface"])
    style.configure("Header.TFrame", background=COLORS["surface"])
    style.configure(
        "Title.TLabel",
        background=COLORS["surface"],
        foreground=COLORS["ink"],
        font=(FONT, TYPE["panel_title"], "bold"),
    )
    style.configure(
        "HeaderMeta.TLabel",
        background=COLORS["surface"],
        foreground=COLORS["muted"],
        font=(FONT, TYPE["support"]),
    )
    style.configure(
        "Section.TLabel",
        background=COLORS["surface"],
        foreground=COLORS["ink"],
        font=(FONT, TYPE["section"], "bold"),
    )
    style.configure(
        "Body.TLabel",
        background=COLORS["surface"],
        foreground=COLORS["ink"],
        font=(FONT, TYPE["body"]),
    )
    style.configure(
        "Muted.TLabel",
        background=COLORS["surface"],
        foreground=COLORS["muted"],
        font=(FONT, TYPE["support"]),
    )
    style.configure(
        "FieldHint.TLabel",
        background=COLORS["surface"],
        foreground=COLORS["subtle"],
        font=(FONT, TYPE["support"]),
    )
    style.configure(
        "CanvasBody.TLabel",
        background=COLORS["canvas"],
        foreground=COLORS["ink"],
        font=(FONT, TYPE["body"]),
    )
    style.configure(
        "CanvasMuted.TLabel",
        background=COLORS["canvas"],
        foreground=COLORS["muted"],
        font=(FONT, TYPE["support"]),
    )
    style.configure(
        "Primary.TButton",
        background=COLORS["primary_action"],
        foreground="#FFFFFF",
        bordercolor=COLORS["primary_action"],
        lightcolor=COLORS["primary_action"],
        darkcolor=COLORS["primary_action"],
        padding=(18, 11),
        font=(FONT, TYPE["body"], "bold"),
        borderwidth=0,
        relief="flat",
    )
    style.map(
        "Primary.TButton",
        background=[("active", COLORS["primary_hover"]), ("disabled", "#9BB5B3")],
        foreground=[("disabled", "#EDF3F2")],
    )
    style.configure(
        "Secondary.TButton",
        background=COLORS["surface_alt"],
        foreground=COLORS["ink"],
        bordercolor=COLORS["line"],
        padding=(14, 10),
        font=(FONT, TYPE["body"]),
        borderwidth=1,
        relief="flat",
    )
    style.map(
        "Secondary.TButton",
        background=[("active", "#DDE9E1"), ("disabled", "#F4F7F5")],
        foreground=[("disabled", COLORS["subtle"])],
    )
    style.configure(
        "Ghost.TButton",
        background=COLORS["surface"],
        foreground=COLORS["muted"],
        bordercolor=COLORS["line"],
        padding=(8, 7),
        font=(FONT, TYPE["support"]),
        borderwidth=0,
        relief="flat",
    )
    style.map("Ghost.TButton", background=[("active", COLORS["surface_alt"])])
    style.configure(
        "Segment.TRadiobutton",
        background=COLORS["surface_alt"],
        foreground=COLORS["muted"],
        indicatorcolor=COLORS["surface_alt"],
        indicatormargin=0,
        padding=(14, 7),
        font=(FONT, TYPE["support"]),
        bordercolor=COLORS["surface_alt"],
        relief="flat",
    )
    style.layout(
        "Segment.TRadiobutton",
        [
            (
                "Radiobutton.padding",
                {
                    "sticky": "nswe",
                    "children": [("Radiobutton.label", {"sticky": "nswe"})],
                },
            )
        ],
    )
    style.map(
        "Segment.TRadiobutton",
        background=[("selected", COLORS["primary_action"]), ("active", "#DDE8E7")],
        foreground=[("selected", "#FFFFFF")],
        indicatorcolor=[("selected", COLORS["primary_action"])],
    )
    style.configure(
        "Form.TEntry",
        fieldbackground="#FAFAFB",
        foreground=COLORS["ink"],
        bordercolor=COLORS["line"],
        insertcolor=COLORS["ink"],
        padding=(10, 9),
        font=(FONT, TYPE["body"]),
    )
    style.map("Form.TEntry", bordercolor=[("focus", COLORS["primary"])])
    style.configure(
        "Accent.Horizontal.TProgressbar",
        troughcolor="#DCE8DF",
        background=COLORS["primary"],
        bordercolor="#DCE8DF",
        lightcolor=COLORS["primary"],
        darkcolor=COLORS["primary"],
        thickness=7,
    )
    style.configure(
        "Vertical.TScrollbar",
        background="#B8C8BC",
        troughcolor=COLORS["canvas"],
        bordercolor=COLORS["canvas"],
        arrowcolor=COLORS["muted"],
    )
    return style
