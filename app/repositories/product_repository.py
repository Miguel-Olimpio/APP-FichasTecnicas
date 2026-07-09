"""Persistência de produtos."""

from __future__ import annotations

from typing import Any

from app.config.settings import SHEET_PRODUTOS
from app.models.product import Product
from app.repositories.excel_database import ExcelDatabase
from app.repositories.excel_schema import PRODUCT_HEADERS
from app.utils.filenames import normalize_name_key


class ProductRepository:
    def __init__(self, db: ExcelDatabase):
        self._db = db

    def list_all_rows(self) -> list[dict[str, Any]]:
        return self._db.read_sheet(SHEET_PRODUTOS)

    def list_active(self) -> list[Product]:
        rows = self.list_all_rows()
        out: list[Product] = []
        for r in rows:
            p = Product.from_row_dict(r)
            if p.active:
                out.append(p)
        return out

    def get_by_id_any(self, product_id: str) -> Product | None:
        for r in self.list_all_rows():
            if str(r.get("produto_id")) == str(product_id):
                return Product.from_row_dict(r)
        return None

    def get_by_id_active(self, product_id: str) -> Product | None:
        p = self.get_by_id_any(product_id)
        if p and p.active:
            return p
        return None

    def find_active_by_name(self, name: str) -> Product | None:
        key = normalize_name_key(name)
        for p in self.list_active():
            if p.nome_normalizado == key:
                return p
        return None

    def save_all_products(self, products: list[dict[str, Any]]) -> None:
        self._db.write_sheet(SHEET_PRODUTOS, PRODUCT_HEADERS, products)
