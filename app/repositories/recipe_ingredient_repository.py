"""Linhas de ingrediente por ficha (aba IngredientesFicha em banco_fichas.xlsx)."""

from __future__ import annotations

from typing import Any

from app.config.settings import SHEET_INGREDIENTES_FICHA
from app.repositories.excel_database import ExcelDatabase
from app.repositories.excel_schema import RECIPE_LINE_HEADERS
from app.services.recipe_line_adapter import row_to_service_dict


class RecipeIngredientRepository:
    def __init__(self, db: ExcelDatabase):
        self._db = db

    def list_all_rows(self) -> list[dict[str, Any]]:
        return self._db.read_sheet(SHEET_INGREDIENTES_FICHA)

    def list_all_service_dicts(self) -> list[dict[str, Any]]:
        return [row_to_service_dict(r) for r in self.list_all_rows()]

    def list_by_product(self, product_id: str) -> list[dict[str, Any]]:
        pid = str(product_id)
        return [row_to_service_dict(r) for r in self.list_all_rows() if str(r.get("produto_id")) == pid]

    def save_all_ingredients(self, rows: list[dict[str, Any]]) -> None:
        """rows já no formato de aba (RECIPE_LINE_HEADERS)."""
        self._db.write_sheet(SHEET_INGREDIENTES_FICHA, RECIPE_LINE_HEADERS, rows)
