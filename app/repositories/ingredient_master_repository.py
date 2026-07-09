"""Persistência do cadastro mestre (banco_ingredientes.xlsx)."""

from __future__ import annotations

from typing import Any

from app.config.settings import SHEET_INGREDIENTES_MESTRE
from app.models.ingredient_master import IngredientMaster
from app.repositories.excel_database import ExcelDatabase
from app.repositories.excel_schema import MASTER_INGREDIENT_HEADERS


class IngredientMasterRepository:
    def __init__(self, db: ExcelDatabase):
        self._db = db

    def list_all_rows(self) -> list[dict[str, Any]]:
        return self._db.read_sheet(SHEET_INGREDIENTES_MESTRE)

    def list_active(self) -> list[IngredientMaster]:
        out: list[IngredientMaster] = []
        for r in self.list_all_rows():
            m = IngredientMaster.from_row_dict(r)
            if m.active:
                out.append(m)
        return out

    def get_by_id(self, ingrediente_id: str) -> IngredientMaster | None:
        for r in self.list_all_rows():
            if str(r.get("ingrediente_id")) == str(ingrediente_id):
                return IngredientMaster.from_row_dict(r)
        return None

    def find_by_nome_normalizado(self, key: str) -> IngredientMaster | None:
        k = key.strip().lower()
        for r in self.list_all_rows():
            if str(r.get("nome_normalizado", "") or "").strip().lower() == k:
                return IngredientMaster.from_row_dict(r)
        return None

    def save_all(self, rows: list[dict[str, Any]]) -> None:
        self._db.write_sheet(SHEET_INGREDIENTES_MESTRE, MASTER_INGREDIENT_HEADERS, rows)
