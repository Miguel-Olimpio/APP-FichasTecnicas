"""Tema visual centralizado — tokens + Style (ttkbootstrap); apenas UI."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from typing import Any

import ttkbootstrap as tb
from ttkbootstrap import Style
from ttkbootstrap.constants import DANGER, LINK, OUTLINE, PRIMARY, SECONDARY, SUCCESS
from tkinter import ttk

# Paleta (design system) inspirada na identidade SEBRAE: azul + branco.
BACKGROUND = "#F3F7FB"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F8FBFF"
PRIMARY_COLOR = "#005CA9"
PRIMARY_DARK = "#003F7D"
SECONDARY_COLOR = BACKGROUND
TEXT_COLOR = "#0F172A"
MUTED_TEXT_COLOR = "#5E6B7A"
SUCCESS_COLOR = "#16A34A"
WARNING_COLOR = "#F59E0B"
DANGER_COLOR = "#DC2626"
BORDER_COLOR = "#D8E4F0"
CARD_BORDER = "#D5E2F0"

# Aliases usados por código legado / referências
BACKGROUND_COLOR = SURFACE
CARD_BACKGROUND = SURFACE

SPACING_XS = 4
SPACING_SM = 6
SPACING_MD = 10
SPACING_LG = 14
SPACING_XL = 18
SPACING_XXL = 24


def _font_family(root: tk.Misc | None) -> str:
    fam = "Segoe UI"
    try:
        if root is not None:
            if fam not in tkfont.families(root):
                return str(tkfont.nametofont("TkDefaultFont", root).cget("family"))
        elif fam not in tkfont.families():
            return "Helvetica"
    except (tk.TclError, ValueError, RuntimeError):
        pass
    return fam


def fonts_for(root: tk.Misc) -> dict[str, tuple]:
    f = _font_family(root)
    return {
        "title": (f, 16, "bold"),
        "subtitle": (f, 10, "bold"),
        "normal": (f, 9),
        "small": (f, 8),
    }


FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_SUBTITLE = ("Segoe UI", 10, "bold")
FONT_NORMAL = ("Segoe UI", 9)
FONT_SMALL = ("Segoe UI", 8)


def apply_app_theme(root: tk.Misc) -> None:
    """Refina o tema litera (ttkbootstrap): fontes, Treeview, labels nomeados."""
    global FONT_TITLE, FONT_SUBTITLE, FONT_NORMAL, FONT_SMALL
    fn = fonts_for(root)
    FONT_TITLE = fn["title"]
    FONT_SUBTITLE = fn["subtitle"]
    FONT_NORMAL = fn["normal"]
    FONT_SMALL = fn["small"]

    style = Style()

    style.configure(".", font=FONT_NORMAL)
    style.configure("TFrame", background=BACKGROUND)
    style.configure("Sidebar.TFrame", background=PRIMARY_DARK)
    style.configure("SidebarCredit.TFrame", background=PRIMARY_DARK)
    style.configure("Card.TFrame", background=SURFACE, relief="flat")
    style.configure("TLabel", background=BACKGROUND, foreground=TEXT_COLOR)
    style.configure("Muted.TLabel", foreground=MUTED_TEXT_COLOR, font=FONT_SMALL, background=BACKGROUND)
    style.configure("Title.TLabel", font=FONT_TITLE, foreground=PRIMARY_COLOR, background=BACKGROUND)
    style.configure("Subtitle.TLabel", font=FONT_SUBTITLE, foreground=TEXT_COLOR, background=BACKGROUND)
    style.configure("SidebarTitle.TLabel", background=PRIMARY_DARK, foreground="#FFFFFF", font=(FONT_TITLE[0], 13, "bold"))
    style.configure("SidebarSub.TLabel", background=PRIMARY_DARK, foreground="#DCEBFA", font=FONT_SMALL)
    style.configure("SidebarCredit.TLabel", background=PRIMARY_DARK, foreground="#DCEBFA", font=FONT_SMALL)
    style.configure("SidebarCreditName.TLabel", background=PRIMARY_DARK, foreground="#FFFFFF", font=FONT_SUBTITLE)

    style.configure(
        "Treeview",
        background=SURFACE,
        fieldbackground=SURFACE,
        foreground=TEXT_COLOR,
        rowheight=24,
        font=FONT_NORMAL,
        borderwidth=0,
    )
    style.configure(
        "Treeview.Heading",
        background=PRIMARY_COLOR,
        foreground="#FFFFFF",
        font=FONT_SUBTITLE,
        relief="flat",
        padding=(SPACING_SM, SPACING_XS),
    )
    style.map("Treeview.Heading", background=[("active", PRIMARY_DARK)])

    style.configure("TButton", padding=(SPACING_MD, SPACING_XS), font=FONT_NORMAL)
    style.configure("TEntry", padding=(SPACING_SM, SPACING_XS))
    style.configure("TCombobox", padding=(SPACING_SM, SPACING_XS))
    style.configure("TNotebook", background=BACKGROUND)
    style.configure("TNotebook.Tab", padding=(SPACING_MD, SPACING_XS), font=FONT_NORMAL)
    style.configure("TLabelframe", background=BACKGROUND, relief="solid", borderwidth=1)
    style.configure("TLabelframe.Label", background=BACKGROUND, foreground=PRIMARY_COLOR, font=FONT_SUBTITLE)

    try:
        root.configure(bg=BACKGROUND)
    except tk.TclError:
        pass

    # Fallback ttk puro (diálogos / testes sem Bootstrap Button)
    style.configure(
        "AppPrimary.TButton",
        background=PRIMARY_COLOR,
        foreground="#FFFFFF",
        font=FONT_SUBTITLE,
        padding=(SPACING_MD, SPACING_XS),
    )
    style.map("AppPrimary.TButton", background=[("active", PRIMARY_DARK), ("disabled", "#9CA3AF")])

    style.configure("AppSecondary.TButton", background=SURFACE_ALT, foreground=PRIMARY_DARK, padding=(SPACING_MD, SPACING_XS))
    style.map("AppSecondary.TButton", background=[("active", BORDER_COLOR)])

    style.configure("AppGhost.TButton", background=BACKGROUND, foreground=MUTED_TEXT_COLOR, padding=(SPACING_SM, SPACING_XS))
    style.map("AppGhost.TButton", background=[("active", SURFACE_ALT)])

    style.configure("AppDanger.TButton", background=DANGER_COLOR, foreground="#FFFFFF", padding=(SPACING_MD, SPACING_XS))
    style.map("AppDanger.TButton", background=[("active", "#B91C1C")])

    style.configure("AppSuccess.TButton", background=SUCCESS_COLOR, foreground="#FFFFFF", padding=(SPACING_MD, SPACING_XS))
    style.map("AppSuccess.TButton", background=[("active", "#15803D")])


def style_button(widget: tk.Widget, role: str) -> None:
    """Primário / secundário / ghost / danger / success — ttkbootstrap.Button ou ttk.Button."""
    if isinstance(widget, tb.Button):
        boot_map: dict[str, Any] = {
            "primary": PRIMARY,
            "secondary": (SECONDARY, OUTLINE),
            "ghost": LINK,
            "danger": DANGER,
            "success": SUCCESS,
        }
        try:
            widget.configure(bootstyle=boot_map.get(role, (SECONDARY, OUTLINE)))
        except tk.TclError:
            pass
        return

    if isinstance(widget, ttk.Button):
        role_map = {
            "primary": "AppPrimary.TButton",
            "secondary": "AppSecondary.TButton",
            "ghost": "AppGhost.TButton",
            "danger": "AppDanger.TButton",
            "success": "AppSuccess.TButton",
        }
        st = role_map.get(role, "TButton")
        try:
            widget.configure(style=st)
        except tk.TclError:
            pass


def configure_treeview_zebra(tree: ttk.Treeview | Any) -> None:
    """Listras alternadas."""
    tree.tag_configure("odd", background=SURFACE)
    tree.tag_configure("even", background=SURFACE_ALT)
