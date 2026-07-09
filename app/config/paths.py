"""Caminhos estaveis para desenvolvimento e PyInstaller."""

from __future__ import annotations

import os
import sys


def is_packaged() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_project_root() -> str:
    """Raiz do projeto durante desenvolvimento."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", ".."))


def get_app_data_dir() -> str:
    """Pasta base gravavel: pasta do .exe no executavel, raiz do projeto em dev."""
    if is_packaged():
        path = os.path.dirname(os.path.abspath(sys.executable))
    else:
        path = get_project_root()
    os.makedirs(path, exist_ok=True)
    return path


def get_app_base_path() -> str:
    """Pasta base usada por dados, PDFs, backups e icone."""
    return get_app_data_dir()


def get_base_dir() -> str:
    """Diretorio base usado por dados, PDFs e backups."""
    return get_app_base_path()


def get_data_dir() -> str:
    path = os.path.join(get_base_dir(), "data")
    os.makedirs(path, exist_ok=True)
    return path


def get_pdfs_dir() -> str:
    path = os.path.join(get_base_dir(), "pdfs")
    os.makedirs(path, exist_ok=True)
    return path


def get_labels_dir() -> str:
    path = os.path.join(get_pdfs_dir(), "etiquetas")
    os.makedirs(path, exist_ok=True)
    return path


def get_backups_dir() -> str:
    path = os.path.join(get_base_dir(), "backups")
    os.makedirs(path, exist_ok=True)
    return path


def get_icon_dir() -> str:
    path = os.path.join(get_app_base_path(), "icon")
    os.makedirs(path, exist_ok=True)
    return path


def get_icon_path() -> str:
    """Caminho do icone da janela, em desenvolvimento ou empacotado."""
    icon_names = ("icon.ico",)
    roots: list[str] = []
    if is_packaged():
        roots.append(os.path.dirname(os.path.abspath(sys.executable)))
        bundle_dir = getattr(sys, "_MEIPASS", None)
        if bundle_dir:
            roots.append(str(bundle_dir))
    else:
        roots.append(get_project_root())

    candidates = [os.path.join(root, "icon", icon_name) for root in roots for icon_name in icon_names]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return candidates[0]

def get_database_path() -> str:
    return os.path.join(get_data_dir(), "banco_fichas.xlsx")


def get_ingredients_database_path() -> str:
    return os.path.join(get_data_dir(), "banco_ingredientes.xlsx")


def ensure_legacy_database_copied() -> None:
    """Copia banco_fichas.xlsx legado para data/ quando ainda nao existir."""
    target = get_database_path()
    if os.path.isfile(target):
        return
    import shutil

    for base in _legacy_base_candidates():
        legacy = os.path.join(base, "banco_fichas.xlsx")
        if os.path.isfile(legacy):
            shutil.copy2(legacy, target)
            return


def ensure_legacy_ingredients_copied() -> None:
    """Copia banco_ingredientes.xlsx legado para data/ quando ainda nao existir."""
    target = get_ingredients_database_path()
    if os.path.isfile(target):
        return
    import shutil

    for base in _legacy_base_candidates():
        legacy = os.path.join(base, "banco_ingredientes.xlsx")
        if os.path.isfile(legacy):
            shutil.copy2(legacy, target)
            return


def _legacy_base_candidates() -> list[str]:
    candidates = [get_project_root()]
    if is_packaged():
        candidates.append(os.path.dirname(os.path.abspath(sys.executable)))
        bundle_dir = getattr(sys, "_MEIPASS", None)
        if bundle_dir:
            candidates.append(str(bundle_dir))

    seen: set[str] = set()
    unique: list[str] = []
    for path in candidates:
        norm = os.path.abspath(path)
        if norm not in seen:
            seen.add(norm)
            unique.append(norm)
    return unique



