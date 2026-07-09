"""Persistência dos passos de preparo por ficha técnica."""

from __future__ import annotations

from typing import Any

from app.config.settings import SHEET_PASSOS_PREPARO
from app.repositories.excel_database import ExcelDatabase
from app.repositories.excel_schema import PREP_STEP_HEADERS
from app.utils.numbers import to_float


class PrepStepRepository:
    def __init__(self, db: ExcelDatabase):
        self._db = db

    def list_all_rows(self) -> list[dict[str, Any]]:
        return self._db.read_sheet(SHEET_PASSOS_PREPARO)

    def list_by_product(self, product_id: str) -> list[dict[str, Any]]:
        pid = str(product_id)
        rows = [r for r in self.list_all_rows() if str(r.get("produto_id")) == pid]
        rows.sort(key=lambda r: int(to_float(r.get("ordem")) or 0))
        return [
            {
                "produto_id": pid,
                "ordem": int(to_float(r.get("ordem")) or idx),
                "descricao": str(r.get("descricao", "") or ""),
            }
            for idx, r in enumerate(rows, start=1)
        ]

    def save_all_rows(self, rows: list[dict[str, Any]]) -> None:
        self._db.write_sheet(SHEET_PASSOS_PREPARO, PREP_STEP_HEADERS, rows)


def normalize_prep_steps(product_id: str, steps: list[dict[str, Any]] | list[str]) -> list[dict[str, Any]]:
    pid = str(product_id)
    normalized: list[dict[str, Any]] = []
    for item in steps:
        if isinstance(item, dict):
            descricao = str(item.get("descricao", "") or "").strip()
        else:
            descricao = str(item or "").strip()
        if not descricao:
            continue
        normalized.append(
            {
                "produto_id": pid,
                "ordem": len(normalized) + 1,
                "descricao": descricao,
            }
        )
    return normalized
