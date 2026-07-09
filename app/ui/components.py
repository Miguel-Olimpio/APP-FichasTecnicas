"""Componentes reutilizáveis (apenas UI)."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

import ttkbootstrap as ttb
from ttkbootstrap.constants import PRIMARY, SECONDARY

from app.ui.styles import (
    FONT_SMALL,
    FONT_SUBTITLE,
    FONT_TITLE,
    MUTED_TEXT_COLOR,
    PRIMARY_COLOR,
    SPACING_LG,
    SPACING_MD,
    SPACING_SM,
    SPACING_XL,
    style_button,
)


def clear_tree(tree: ttb.Treeview | tk.Widget) -> None:
    for item in tree.get_children():
        tree.delete(item)


def scrollable_text(parent: tk.Widget, height: int = 6) -> tk.Text:
    frame = ttb.Frame(parent)
    text = tk.Text(frame, height=height, wrap="word")
    scroll = ttb.Scrollbar(frame, command=text.yview)
    text.configure(yscrollcommand=scroll.set)
    text.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    frame.pack(fill="both", expand=True)
    return text


def section_header(parent: tk.Widget, title: str, subtitle: str | None = None) -> ttb.Frame:
    """Título de página + subtítulo opcional."""
    f = ttb.Frame(parent)
    ttb.Label(f, text=title, font=FONT_TITLE, foreground=PRIMARY_COLOR).pack(anchor="w")
    if subtitle:
        ttb.Label(f, text=subtitle, font=FONT_SMALL, foreground=MUTED_TEXT_COLOR).pack(anchor="w", pady=(SPACING_SM, 0))
    return f


def create_metric_card(
    parent: tk.Widget,
    title: str,
    description: str,
    value_var: tk.StringVar,
    bootstyle: str = SECONDARY,
) -> ttb.Labelframe:
    """Card de métrica (Labelframe estilo card) com valor ligado a StringVar."""
    card = ttb.Labelframe(parent, text=title, padding=SPACING_MD)
    ttb.Label(card, textvariable=value_var, font=("Segoe UI", 16, "bold"), foreground=PRIMARY_COLOR).pack(anchor="w")
    ttb.Label(card, text=description, font=FONT_SMALL, foreground=MUTED_TEXT_COLOR, bootstyle=bootstyle).pack(
        anchor="w", pady=(SPACING_SM, 0)
    )
    return card


def create_empty_state(
    parent: tk.Widget,
    title: str,
    description: str,
    action_text: str | None = None,
    command: Callable[[], None] | None = None,
) -> ttb.Frame:
    f = ttb.Frame(parent, padding=SPACING_LG)
    ttb.Label(f, text=title, font=FONT_SUBTITLE, foreground=PRIMARY_COLOR).pack(anchor="center", pady=(SPACING_MD, SPACING_SM))
    ttb.Label(f, text=description, font=FONT_SMALL, foreground=MUTED_TEXT_COLOR, wraplength=480).pack(anchor="center")
    if action_text and command:
        b = ttb.Button(f, text=action_text, command=command, width=28)
        b.pack(pady=(SPACING_MD, 0))
        style_button(b, "primary")
    return f


def create_search_row(
    parent: tk.Widget,
    label: str,
    variable: tk.StringVar,
    on_change: Callable[[], None] | None = None,
    width: int = 36,
) -> ttb.Frame:
    row = ttb.Frame(parent)
    ttb.Label(row, text=label).pack(side="left", padx=(0, SPACING_SM))
    ent = ttb.Entry(row, textvariable=variable, width=width)
    ent.pack(side="left", fill="x", expand=True)
    if on_change:
        ent.bind("<KeyRelease>", lambda _e: on_change())
    return row


def create_primary_button(parent: tk.Widget, text: str, command: Callable[[], None]) -> ttb.Button:
    b = ttb.Button(parent, text=text, command=command, bootstyle=PRIMARY)
    style_button(b, "primary")
    return b


def create_secondary_button(parent: tk.Widget, text: str, command: Callable[[], None]) -> ttb.Button:
    b = ttb.Button(parent, text=text, command=command)
    style_button(b, "secondary")
    return b


def create_danger_button(parent: tk.Widget, text: str, command: Callable[[], None]) -> ttb.Button:
    b = ttb.Button(parent, text=text, command=command)
    style_button(b, "danger")
    return b
