"""Modelo de ingrediente de uma ficha."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.models.enums import IngredienteTipo
from app.utils.filenames import normalize_name_key
from app.utils.numbers import to_float


@dataclass
class Ingredient:
    ingrediente_id: str
    produto_id: str
    nome: str = ""
    nome_normalizado: str = ""
    tipo: str = IngredienteTipo.SIMPLES.value
    produto_ref_id: str = ""
    quantidade: float = 0.0
    unidade: str = ""
    preco_unidade: float = 0.0
    preco_kg: float = 0.0
    preco_litro: float = 0.0
    unidade_custo: str = ""
    proporcao: float = 0.0
    custo_calculado: float = 0.0
    observacoes: str = ""

    def sync_derived(self) -> None:
        self.nome_normalizado = normalize_name_key(self.nome)

    def to_row_dict(self) -> dict[str, Any]:
        self.sync_derived()
        return asdict(self)

    @classmethod
    def from_service_dict(cls, d: dict[str, Any]) -> Ingredient:
        return cls(
            ingrediente_id=str(d.get("ingrediente_ficha_id") or d.get("ingrediente_id") or ""),
            produto_id=str(d.get("produto_id", "") or ""),
            nome=str(d.get("nome", "") or ""),
            nome_normalizado=str(d.get("nome_normalizado", "") or ""),
            tipo=str(d.get("tipo", IngredienteTipo.SIMPLES.value) or IngredienteTipo.SIMPLES.value),
            produto_ref_id=str(d.get("produto_ref_id", "") or ""),
            quantidade=to_float(d.get("quantidade")),
            unidade=str(d.get("unidade", "") or ""),
            preco_unidade=to_float(d.get("preco_unidade")),
            preco_kg=to_float(d.get("preco_kg")),
            preco_litro=to_float(d.get("preco_litro")),
            unidade_custo=str(d.get("unidade_custo", "") or ""),
            proporcao=to_float(d.get("proporcao")),
            custo_calculado=to_float(d.get("custo_calculado")),
            observacoes=str(d.get("observacoes", "") or ""),
        )

    @classmethod
    def from_row_dict(cls, row: dict[str, Any]) -> Ingredient:
        if str(row.get("origem_linha", "") or "").strip():
            from app.services.recipe_line_adapter import row_to_service_dict

            s = row_to_service_dict(row) if "nome_ingrediente" in row else row
            return cls.from_service_dict(s)
        return cls(
            ingrediente_id=str(row.get("ingrediente_id", "") or ""),
            produto_id=str(row.get("produto_id", "") or ""),
            nome=str(row.get("nome", "") or ""),
            nome_normalizado=str(row.get("nome_normalizado", "") or ""),
            tipo=str(row.get("tipo", IngredienteTipo.SIMPLES.value) or IngredienteTipo.SIMPLES.value),
            produto_ref_id=str(row.get("produto_ref_id", "") or ""),
            quantidade=to_float(row.get("quantidade")),
            unidade=str(row.get("unidade", "") or ""),
            preco_unidade=to_float(row.get("preco_unidade")),
            preco_kg=to_float(row.get("preco_kg")),
            preco_litro=to_float(row.get("preco_litro")),
            unidade_custo=str(row.get("unidade_custo", "") or ""),
            proporcao=to_float(row.get("proporcao")),
            custo_calculado=to_float(row.get("custo_calculado")),
            observacoes=str(row.get("observacoes", "") or ""),
        )


def ingredient_to_pdf_line(ing: Ingredient) -> dict[str, Any]:
    return {
        "nome": ing.nome,
        "quantidade": ing.quantidade,
        "unidade": ing.unidade,
    }
