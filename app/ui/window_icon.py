"""Aplicacao do icone padrao nas janelas."""

from __future__ import annotations

import ctypes
import os
import tkinter as tk

from app.config.paths import get_icon_path

APP_USER_MODEL_ID = "MiguelOlimpio.FichasTecnicas"


def set_windows_app_id() -> None:
    """Evita que o Windows agrupe o app com o icone padrao do Python."""
    if os.name != "nt":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass


def _apply_iconbitmap(window: tk.Misc, icon_path: str) -> bool:
    applied = False
    for kwargs in ({"default": icon_path}, {}):
        try:
            if kwargs:
                window.iconbitmap(**kwargs)
            else:
                window.iconbitmap(icon_path)
            applied = True
        except Exception:
            pass
    try:
        window.tk.call("wm", "iconbitmap", window._w, icon_path)
        applied = True
    except Exception:
        pass
    return applied


def apply_window_icon(window: tk.Misc) -> None:
    """Aplica icon/icon.ico na janela, sem interromper a abertura se falhar."""
    icon_path = get_icon_path()
    if not os.path.isfile(icon_path):
        return
    _apply_iconbitmap(window, icon_path)
    try:
        window.after(50, lambda: _apply_iconbitmap(window, icon_path))
    except Exception:
        pass

