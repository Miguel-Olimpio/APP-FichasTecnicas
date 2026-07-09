"""Migração e helpers do repositório Excel."""

from app.repositories.excel_database import _migrate_products
from app.utils.tipo_ficha import TIPO_FICHA_PRODUTO_FINAL


def test_migrate_products_fills_tipo_ficha_when_missing():
    rows = [{"produto_id": "a", "nome": "X", "categoria": "Cat"}]
    out = _migrate_products(rows)
    assert len(out) == 1
    assert out[0].get("tipo_ficha") == TIPO_FICHA_PRODUTO_FINAL
