"""Cadastro mestre de ingrediente (banco_ingredientes.xlsx)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.utils.filenames import normalize_name_key
from app.utils.numbers import to_float


def _parse_bool(value: object, default: bool = True) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in ("0", "false", "n", "no", "nao", "não"):
        return False
    if s in ("1", "true", "s", "sim", "yes"):
        return True
    return default


@dataclass
class IngredientMaster:
    ingrediente_id: str
    nome: str = ""
    nome_normalizado: str = ""
    classificacao: str = ""
    categoria: str = ""
    unidade_padrao: str = ""
    unidade_custo: str = ""
    preco_kg: float = 0.0
    preco_litro: float = 0.0
    preco_unidade: float = 0.0
    observacoes: str = ""
    data_criacao: str = ""
    data_atualizacao: str = ""
    active: bool = True

    def sync_derived(self) -> None:
        self.nome_normalizado = normalize_name_key(self.nome)

    def to_row_dict(self) -> dict[str, Any]:
        self.sync_derived()
        return asdict(self)

    @classmethod
    def from_row_dict(cls, row: dict[str, Any]) -> IngredientMaster:
        return cls(
            ingrediente_id=str(row.get("ingrediente_id", "") or ""),
            nome=str(row.get("nome", "") or ""),
            nome_normalizado=str(row.get("nome_normalizado", "") or ""),
            classificacao=str(row.get("classificacao", "") or ""),
            categoria=str(row.get("categoria", "") or ""),
            unidade_padrao=str(row.get("unidade_padrao", "") or ""),
            unidade_custo=str(row.get("unidade_custo", "") or ""),
            preco_kg=to_float(row.get("preco_kg")),
            preco_litro=to_float(row.get("preco_litro")),
            preco_unidade=to_float(row.get("preco_unidade")),
            observacoes=str(row.get("observacoes", "") or ""),
            data_criacao=str(row.get("data_criacao", "") or ""),
            data_atualizacao=str(row.get("data_atualizacao", "") or ""),
            active=_parse_bool(row.get("active"), True),
        )
