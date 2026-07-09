import os
import sys

from app.config import paths


def test_packaged_paths_use_executable_folder(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    exe_path = tmp_path / "FichasTecnicas.exe"
    monkeypatch.setattr(sys, "executable", str(exe_path))

    base = paths.get_app_data_dir()

    assert base == str(tmp_path)
    assert paths.get_database_path() == os.path.join(base, "data", "banco_fichas.xlsx")
    assert paths.get_ingredients_database_path() == os.path.join(base, "data", "banco_ingredientes.xlsx")
    assert paths.get_pdfs_dir() == os.path.join(base, "pdfs")
    assert paths.get_backups_dir() == os.path.join(base, "backups")


def test_packaged_icon_path_prefers_pyinstaller_bundle(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "FichasTecnicas.exe"))
    bundle_dir = tmp_path / "_internal"
    icon_path = bundle_dir / "icon" / "icon.ico"
    icon_path.parent.mkdir(parents=True)
    icon_path.write_text("ico")
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)

    assert paths.get_icon_path() == str(icon_path)

