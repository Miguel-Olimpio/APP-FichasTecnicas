"""Persistência da precificação atual por ficha técnica."""

from __future__ import annotations

from typing import Any

from app.config.settings import SHEET_PRECIFICACAO
from app.repositories.excel_database import ExcelDatabase
from app.repositories.excel_schema import PRICING_HEADERS


class PricingRepository:
    def __init__(self, db: ExcelDatabase):
        self._db = db

    def list_all_rows(self) -> list[dict[str, Any]]:
        return self._db.read_sheet(SHEET_PRECIFICACAO)

    def get_by_product(self, product_id: str) -> dict[str, Any] | None:
        pid = str(product_id)
        for row in self.list_all_rows():
            if str(row.get("produto_id")) == pid:
                return normalize_pricing_row(pid, row)
        return None

    def save_all_rows(self, rows: list[dict[str, Any]]) -> None:
        self._db.write_sheet(SHEET_PRECIFICACAO, PRICING_HEADERS, rows)


def normalize_pricing_row(product_id: str, row: dict[str, Any]) -> dict[str, Any]:
    normalized = {header: "" for header in PRICING_HEADERS}
    normalized.update({k: v for k, v in dict(row).items() if k in normalized})
    normalized["produto_id"] = str(product_id)
    return normalized
