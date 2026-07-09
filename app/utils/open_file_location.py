"""Helpers para abrir arquivos gerados e suas pastas."""

from __future__ import annotations

import os
import subprocess
import sys
from tkinter import messagebox
from typing import Any


def _normalized_path(path: os.PathLike[str] | str) -> str:
    return os.path.abspath(os.path.normpath(os.fspath(path)))


def open_path(path: os.PathLike[str] | str) -> bool:
    """Abre um arquivo ou pasta com o aplicativo padrao do sistema."""
    normalized = _normalized_path(path)
    try:
        if os.name == "nt":
            os.startfile(normalized)  # type: ignore[attr-defined]
            return True
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.Popen([opener, normalized])
        return True
    except OSError:
        return False


def reveal_file_in_explorer(path: os.PathLike[str] | str) -> bool:
    """Abre a pasta do arquivo, selecionando-o no Explorer quando possivel."""
    normalized = _normalized_path(path)
    if os.name == "nt":
        try:
            subprocess.Popen(["explorer.exe", "/select,", normalized])
            return True
        except OSError:
            if os.path.isfile(normalized):
                return open_path(normalized)
    folder = os.path.dirname(normalized) or "."
    return open_path(folder)


def prompt_open_generated_file(
    parent: Any,
    path: os.PathLike[str] | str,
    *,
    title: str = "Arquivo gerado",
    message_prefix: str = "Arquivo salvo em:",
) -> None:
    """Pergunta se o usuario quer abrir o arquivo gerado ou sua pasta."""
    normalized = _normalized_path(path)
    choice = messagebox.askyesnocancel(
        title,
        f"{message_prefix}\n{normalized}\n\nSim: abrir arquivo\nNao: abrir pasta\nCancelar: fechar",
        parent=parent,
    )
    if choice is True:
        if not open_path(normalized):
            messagebox.showinfo(title, f"Arquivo salvo em:\n{normalized}", parent=parent)
    elif choice is False:
        if not reveal_file_in_explorer(normalized):
            messagebox.showinfo(title, f"Arquivo salvo em:\n{normalized}", parent=parent)
