from datetime import datetime, timedelta
from pathlib import Path

from app.repositories.excel_database import ExcelDatabase
from app.repositories.excel_schema import FICHAS_SHEETS_CONFIG


def _backup_name(stem: str, when: datetime) -> str:
    return f"{stem}_backup_{when.strftime('%Y%m%d_%H%M%S')}.xlsx"


def _backup_paths(tmp_path, stem: str) -> list:
    return sorted(tmp_path.glob(f"{stem}_backup_*.xlsx"))


def test_create_backup_respects_minimum_interval(tmp_path):
    db_path = tmp_path / "banco_fichas.xlsx"
    db = ExcelDatabase(str(db_path), FICHAS_SHEETS_CONFIG, "banco_fichas")
    db.create_database()

    recent = tmp_path / _backup_name("banco_fichas", datetime.now())
    recent.write_text("backup recente")

    assert db.create_backup() is None
    assert _backup_paths(tmp_path, "banco_fichas") == [recent]


def test_create_backup_keeps_only_last_ten_for_same_database(tmp_path):
    db_path = tmp_path / "banco_fichas.xlsx"
    db = ExcelDatabase(str(db_path), FICHAS_SHEETS_CONFIG, "banco_fichas")
    db.create_database()

    start = datetime.now() - timedelta(hours=3)
    for index in range(12):
        (tmp_path / _backup_name("banco_fichas", start + timedelta(minutes=index))).write_text(str(index))
        (tmp_path / _backup_name("banco_ingredientes", start + timedelta(minutes=index))).write_text(str(index))

    created = db.create_backup()

    assert created is not None
    fichas_backups = _backup_paths(tmp_path, "banco_fichas")
    assert len(fichas_backups) == 10
    assert _backup_name("banco_fichas", start) not in {p.name for p in fichas_backups}
    assert len(_backup_paths(tmp_path, "banco_ingredientes")) == 12


def test_create_backup_uses_configured_backup_directory(tmp_path):
    db_path = tmp_path / "data" / "banco_fichas.xlsx"
    backup_dir = tmp_path / "backups"
    db = ExcelDatabase(str(db_path), FICHAS_SHEETS_CONFIG, "banco_fichas", str(backup_dir))
    db.create_database()

    created = db.create_backup()

    assert created is not None
    assert backup_dir in Path(created).parents
    assert not list((tmp_path / "data").glob("banco_fichas_backup_*.xlsx"))
