"""Compatibilidade: catalogo antigo agora usa o cadastro mestre de ingredientes."""

from __future__ import annotations

import uuid
from typing import Any

from app.config.settings import CLASSIFICACAO_INGREDIENTE_SIMPLES, SHEET_INGREDIENTES_MESTRE
from app.repositories.excel_database import ExcelDatabase
from app.repositories.excel_schema import MASTER_INGREDIENT_HEADERS
from app.utils.dates import now_str
from app.utils.filenames import normalize_name_key


class IngredientCatalogRepository:
    """API antiga do catalogo, mantida sobre a aba atual de ingredientes."""

    def __init__(self, db: ExcelDatabase):
        self._db = db

    def list_active_rows(self) -> list[dict[str, Any]]:
        rows = self.list_all_rows()
        out = []
        for row in rows:
            active = row.get("active")
            if active in (False, "false", "FALSE", 0, "0"):
                continue
            out.append(row)
        return out

    def list_all_rows(self) -> list[dict[str, Any]]:
        return self._db.read_sheet(SHEET_INGREDIENTES_MESTRE)

    def save_all(self, rows: list[dict[str, Any]]) -> None:
        normalized = [_to_master_row(row) for row in rows]
        self._db.write_sheet(SHEET_INGREDIENTES_MESTRE, MASTER_INGREDIENT_HEADERS, normalized)

    def add_item(
        self,
        nome: str,
        unidade_padrao: str,
        preco_unidade_padrao: float,
        preco_kg_padrao: float,
        unidade_custo_padrao: str,
    ) -> dict[str, Any]:
        rows = self.list_all_rows()
        row = {
            "ingrediente_id": str(uuid.uuid4()),
            "nome": nome.strip(),
            "nome_normalizado": normalize_name_key(nome),
            "classificacao": CLASSIFICACAO_INGREDIENTE_SIMPLES,
            "categoria": "Outros",
            "unidade_padrao": unidade_padrao.strip(),
            "unidade_custo": unidade_custo_padrao.strip(),
            "preco_kg": preco_kg_padrao,
            "preco_litro": 0.0,
            "preco_unidade": preco_unidade_padrao,
            "observacoes": "",
            "data_criacao": now_str(),
            "data_atualizacao": now_str(),
            "active": True,
        }
        rows.append(row)
        self.save_all(rows)
        return row


def _to_master_row(row: dict[str, Any]) -> dict[str, Any]:
    out = {header: row.get(header, "") for header in MASTER_INGREDIENT_HEADERS}
    out["ingrediente_id"] = out.get("ingrediente_id") or row.get("ingrediente_catalogo_id", "")
    out["nome"] = out.get("nome", "")
    out["nome_normalizado"] = out.get("nome_normalizado") or normalize_name_key(out.get("nome"))
    out["classificacao"] = out.get("classificacao") or CLASSIFICACAO_INGREDIENTE_SIMPLES
    out["categoria"] = out.get("categoria") or "Outros"
    out["unidade_padrao"] = out.get("unidade_padrao") or row.get("unidade_padrao", "")
    out["unidade_custo"] = out.get("unidade_custo") or row.get("unidade_custo_padrao", "")
    out["preco_kg"] = out.get("preco_kg") or row.get("preco_kg_padrao", 0.0)
    out["preco_litro"] = out.get("preco_litro") or 0.0
    out["preco_unidade"] = out.get("preco_unidade") or row.get("preco_unidade_padrao", 0.0)
    out["data_criacao"] = out.get("data_criacao") or now_str()
    out["data_atualizacao"] = out.get("data_atualizacao") or now_str()
    if out.get("active") in (None, ""):
        out["active"] = True
    return out
