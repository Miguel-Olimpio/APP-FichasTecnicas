"""Mapa entre linhas da aba IngredientesFicha e o dict usado em cálculo/validação/UI."""

from __future__ import annotations

import uuid
from typing import Any

from app.config.settings import (
    CLASSIFICACAO_INGREDIENTE_SIMPLES,
    CLASSIFICACAO_MATERIA_PRIMA,
    ORIGEM_CADASTRO_MESTRE,
    ORIGEM_FICHA_INTERMEDIARIA,
)
from app.models.enums import IngredienteTipo
from app.repositories.excel_schema import RECIPE_LINE_HEADERS
from app.utils.numbers import to_float


def row_to_service_dict(row: dict[str, Any]) -> dict[str, Any]:
    """Linha Excel IngredientesFicha -> dict unificado para ProductService/recalc."""
    origem = str(row.get("origem_linha", "") or "").strip()
    ref = str(row.get("produto_ref_id", "") or "")
    master_id = str(row.get("ingrediente_id", "") or "")
    q = to_float(row.get("quantidade_utilizada"))
    u = str(row.get("unidade_utilizada", "") or "")
    uc = str(row.get("unidade_custo", "") or "")
    nome = str(row.get("nome_ingrediente", "") or "")
    iid = str(row.get("ingrediente_ficha_id", "") or "")
    if not origem:
        origem = ORIGEM_FICHA_INTERMEDIARIA if ref else ORIGEM_CADASTRO_MESTRE
    if origem == ORIGEM_FICHA_INTERMEDIARIA or (ref and not master_id):
        tipo = IngredienteTipo.PRODUTO_COMPOSTO.value
    else:
        tipo = IngredienteTipo.SIMPLES.value
    return {
        "ingrediente_ficha_id": iid,
        "ingrediente_id": iid,
        "produto_id": str(row.get("produto_id", "") or ""),
        "origem_linha": origem,
        "ingrediente_cadastro_id": master_id if origem == ORIGEM_CADASTRO_MESTRE else "",
        "produto_ref_id": ref,
        "nome": nome,
        "tipo": tipo,
        "quantidade": q,
        "unidade": u,
        "unidade_custo": uc,
        "preco_kg": to_float(row.get("preco_kg_snapshot")),
        "preco_unidade": to_float(row.get("preco_unidade_snapshot")),
        "preco_litro": to_float(row.get("preco_litro_snapshot")),
        "classificacao_ingrediente": str(row.get("classificacao_ingrediente", "") or ""),
        "custo_calculado": to_float(row.get("custo_calculado")),
        "proporcao": to_float(row.get("proporcao")),
        "observacoes": str(row.get("observacoes", "") or ""),
    }


def service_dict_to_row(d: dict[str, Any]) -> dict[str, Any]:
    """Dict unificado -> linha canónica RECIPE_LINE_HEADERS."""
    origem = str(d.get("origem_linha", "") or "").strip()
    if not origem:
        origem = ORIGEM_FICHA_INTERMEDIARIA if d.get("produto_ref_id") else ORIGEM_CADASTRO_MESTRE
    fid = str(d.get("ingrediente_ficha_id") or d.get("ingrediente_id") or "") or str(uuid.uuid4())
    master_id = str(d.get("ingrediente_cadastro_id", "") or "")
    if origem == ORIGEM_FICHA_INTERMEDIARIA:
        master_id = ""
    row: dict[str, Any] = {
        "ingrediente_ficha_id": fid,
        "produto_id": str(d.get("produto_id", "") or ""),
        "origem_linha": origem,
        "ingrediente_id": master_id,
        "produto_ref_id": str(d.get("produto_ref_id", "") or ""),
        "nome_ingrediente": str(d.get("nome", "") or ""),
        "classificacao_ingrediente": str(d.get("classificacao_ingrediente", "") or ""),
        "quantidade_utilizada": to_float(d.get("quantidade")),
        "unidade_utilizada": str(d.get("unidade", "") or ""),
        "unidade_custo": str(d.get("unidade_custo", "") or ""),
        "preco_kg_snapshot": to_float(d.get("preco_kg")),
        "preco_litro_snapshot": to_float(d.get("preco_litro")),
        "preco_unidade_snapshot": to_float(d.get("preco_unidade")),
        "custo_calculado": to_float(d.get("custo_calculado")),
        "proporcao": to_float(d.get("proporcao")),
        "observacoes": str(d.get("observacoes", "") or ""),
    }
    out: dict[str, Any] = {k: row.get(k, "") for k in RECIPE_LINE_HEADERS}
    return out


def build_line_from_master(
    produto_id: str,
    master: dict[str, Any],
    quantidade: float,
    unidade: str,
    ingrediente_ficha_id: str | None = None,
) -> dict[str, Any]:
    """Monta dict de serviço ao adicionar ingrediente do cadastro mestre (preços = snapshot do mestre)."""
    mid = str(master.get("ingrediente_id", "") or "")
    cls = str(master.get("classificacao", "") or CLASSIFICACAO_INGREDIENTE_SIMPLES)
    nome = str(master.get("nome", "") or "")
    uc = str(master.get("unidade_custo", "") or "")
    fid = (ingrediente_ficha_id or "").strip() or str(uuid.uuid4())
    return {
        "ingrediente_ficha_id": fid,
        "produto_id": str(produto_id),
        "origem_linha": ORIGEM_CADASTRO_MESTRE,
        "ingrediente_cadastro_id": mid,
        "produto_ref_id": "",
        "nome": nome,
        "classificacao_ingrediente": cls,
        "tipo": IngredienteTipo.SIMPLES.value,
        "quantidade": quantidade,
        "unidade": unidade,
        "unidade_custo": uc,
        "preco_kg": to_float(master.get("preco_kg")),
        "preco_unidade": to_float(master.get("preco_unidade")),
        "preco_litro": to_float(master.get("preco_litro")),
        "custo_calculado": 0.0,
        "proporcao": 0.0,
        "observacoes": "",
    }


def build_line_from_intermediate_product(
    produto_id: str,
    ref_product_id: str,
    nome_ficha: str,
    quantidade: float,
    unidade: str,
    unidade_custo: str,
    ingrediente_ficha_id: str | None = None,
) -> dict[str, Any]:
    fid = (ingrediente_ficha_id or "").strip() or str(uuid.uuid4())
    return {
        "ingrediente_ficha_id": fid,
        "produto_id": str(produto_id),
        "origem_linha": ORIGEM_FICHA_INTERMEDIARIA,
        "ingrediente_cadastro_id": "",
        "produto_ref_id": str(ref_product_id),
        "nome": nome_ficha,
        "classificacao_ingrediente": "produto_intermediario",
        "tipo": IngredienteTipo.PRODUTO_COMPOSTO.value,
        "quantidade": quantidade,
        "unidade": unidade,
        "unidade_custo": unidade_custo,
        "preco_kg": 0.0,
        "preco_unidade": 0.0,
        "preco_litro": 0.0,
        "custo_calculado": 0.0,
        "proporcao": 0.0,
        "observacoes": "",
    }
