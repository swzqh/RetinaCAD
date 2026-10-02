"""Reusable Tk widgets used by the desktop interface."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .theme import COLORS, FONT, TYPE


class Surface(tk.Frame):
    """A flat white work surface with one structural edge."""

    def __init__(self, master: tk.Misc, **kwargs) -> None:
        super().__init__(
            master,
            bg=COLORS["surface"],
            highlightbackground=COLORS["line"],
            highlightcolor=COLORS["line"],
            highlightthickness=1,
            bd=0,
            **kwargs,
        )


class ScrollFrame(ttk.Frame):
    """A vertical scroll container whose inner width follows the viewport."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, style="App.TFrame")
        self.canvas = tk.Canvas(
            self,
            bg=COLORS["canvas"],
            highlightbackground=COLORS["canvas"],
            highlightcolor=COLORS["primary_text"],
            highlightthickness=1,
            bd=0,
            takefocus=True,
        )
        self.scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview
        )
        self.inner = ttk.Frame(self.canvas, style="App.TFrame")
        self.window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.inner.bind("<Configure>", self._update_scrollregion)
        self.canvas.bind("<Configure>", self._update_width)
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)
        self.canvas.bind("<Up>", lambda _event: self._key_scroll(-1, "units"))
        self.canvas.bind("<Down>", lambda _event: self._key_scroll(1, "units"))
        self.canvas.bind("<Prior>", lambda _event: self._key_scroll(-1, "pages"))
        self.canvas.bind("<Next>", lambda _event: self._key_scroll(1, "pages"))
        self.canvas.bind("<Home>", lambda _event: self._key_home_end(0.0))
        self.canvas.bind("<End>", lambda _event: self._key_home_end(1.0))

    def _update_scrollregion(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _update_width(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.window, width=event.width)

    def _bind_wheel(self, _event: tk.Event) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)

    def _unbind_wheel(self, _event: tk.Event) -> None:
        self.canvas.unbind_all("<MouseWheel>")

    def _on_wheel(self, event: tk.Event) -> None:
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def _key_scroll(self, amount: int, unit: str) -> str:
        self.canvas.yview_scroll(amount, unit)
        return "break"

    def _key_home_end(self, fraction: float) -> str:
        self.canvas.yview_moveto(fraction)
        return "break"

    def track_focus(self, widget: tk.Widget) -> None:
        """Keep keyboard-focused descendants visible inside the viewport."""
        widget.bind("<FocusIn>", self._ensure_visible, add="+")
        for child in widget.winfo_children():
            self.track_focus(child)

    def _ensure_visible(self, event: tk.Event) -> None:
        widget = event.widget
        self.update_idletasks()
        content_height = max(self.inner.winfo_reqheight(), 1)
        viewport_height = self.canvas.winfo_height()
        top = self.canvas.canvasy(0)
        widget_top = widget.winfo_rooty() - self.inner.winfo_rooty()
        widget_bottom = widget_top + widget.winfo_height()
        if widget_top < top:
            self.canvas.yview_moveto(max(widget_top - 12, 0) / content_height)
        elif widget_bottom > top + viewport_height:
            target = widget_bottom - viewport_height + 12
            self.canvas.yview_moveto(max(target, 0) / content_height)


class StatusBadge(tk.Label):
    """Compact status label using a semantic palette."""

    PALETTES = {
        "success": (COLORS["success_soft"], COLORS["success"]),
        "warning": (COLORS["amber_soft"], COLORS["amber"]),
        "neutral": (COLORS["surface_alt"], COLORS["muted"]),
        "danger": (COLORS["danger_soft"], COLORS["danger"]),
        "dark": (COLORS["surface_alt"], COLORS["muted"]),
    }

    def __init__(self, master: tk.Misc, text: str, tone: str = "neutral") -> None:
        bg, fg = self.PALETTES[tone]
        super().__init__(
            master,
            text=text,
            bg=bg,
            fg=fg,
            font=(FONT, TYPE["compact"], "bold"),
            padx=8,
            pady=4,
            bd=0,
        )


class ToolTip:
    """Small hover label for icon-only controls."""

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.window: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _event: tk.Event) -> None:
        if self.window is not None:
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 7
        self.window = tk.Toplevel(self.widget)
        self.window.wm_overrideredirect(True)
        self.window.wm_geometry(f"+{x}+{y}")
        tk.Label(
            self.window,
            text=self.text,
            bg=COLORS["ink"],
            fg="#FFFFFF",
            font=(FONT, TYPE["compact"]),
            padx=8,
            pady=5,
            bd=0,
        ).pack()

    def _hide(self, _event: tk.Event) -> None:
        if self.window is not None:
            self.window.destroy()
            self.window = None


class InfoButton(tk.Button):
    """Native information button with keyboard and assistive-technology semantics."""

    def __init__(self, master: tk.Misc, command) -> None:
        super().__init__(
            master,
            text="i",
            command=command,
            width=2,
            height=1,
            bg=COLORS["surface_alt"],
            fg=COLORS["ink"],
            activebackground=COLORS["primary_soft"],
            activeforeground=COLORS["primary_text"],
            highlightbackground=COLORS["surface"],
            highlightcolor=COLORS["primary_text"],
            highlightthickness=2,
            relief="flat",
            bd=0,
            font=(FONT, TYPE["body"], "bold"),
            cursor="hand2",
            takefocus=True,
        )
        ToolTip(self, "Model information")


class SegmentedControl(ttk.Frame):
    """Indicator-free radio buttons for a binary model input."""

    def __init__(
        self,
        master: tk.Misc,
        variable: tk.IntVar,
        choices: tuple[tuple[str, int], ...],
    ) -> None:
        super().__init__(master, style="Surface.TFrame")
        for index, (label, value) in enumerate(choices):
            button = ttk.Radiobutton(
                self,
                text=label,
                value=value,
                variable=variable,
                style="Segment.TRadiobutton",
            )
            button.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 2, 0))
            self.columnconfigure(index, weight=1, uniform="segment")
