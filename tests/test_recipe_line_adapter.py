"""Linha de receita ↔ dict de serviço."""

from app.config.settings import ORIGEM_CADASTRO_MESTRE, ORIGEM_FICHA_INTERMEDIARIA
from app.services.recipe_line_adapter import (
    build_line_from_intermediate_product,
    build_line_from_master,
    row_to_service_dict,
    service_dict_to_row,
)


def test_service_roundtrip_preserves_ids():
    d = {
        "ingrediente_ficha_id": "fid-1",
        "produto_id": "p1",
        "origem_linha": ORIGEM_CADASTRO_MESTRE,
        "ingrediente_cadastro_id": "mid-1",
        "produto_ref_id": "",
        "nome": "Farinha",
        "classificacao_ingrediente": "x",
        "tipo": "simples",
        "quantidade": 2,
        "unidade": "kg",
        "unidade_custo": "kg",
        "preco_kg": 5.0,
        "preco_litro": 0.0,
        "preco_unidade": 0.0,
        "custo_calculado": 10.0,
        "proporcao": 50.0,
        "observacoes": "",
    }
    row = service_dict_to_row(d)
    back = row_to_service_dict(row)
    assert back["ingrediente_ficha_id"] == "fid-1"
    assert back["ingrediente_cadastro_id"] == "mid-1"
    assert back["quantidade"] == 2.0
    assert back["preco_kg"] == 5.0


def test_build_line_from_master_reuses_ficha_id():
    master = {
        "ingrediente_id": "m1",
        "nome": "Leite",
        "classificacao": "ingrediente_simples",
        "unidade_custo": "L",
        "preco_kg": 0,
        "preco_litro": 8.0,
        "preco_unidade": 0,
    }
    line = build_line_from_master("p1", master, 0.5, "L", ingrediente_ficha_id="keep-me")
    assert line["ingrediente_ficha_id"] == "keep-me"
    assert line["origem_linha"] == ORIGEM_CADASTRO_MESTRE
    assert line["preco_litro"] == 8.0


def test_build_line_from_inter_reuses_ficha_id():
    line = build_line_from_intermediate_product(
        "p1", "ref1", "Base", 1.0, "kg", "kg", ingrediente_ficha_id="line-99"
    )
    assert line["ingrediente_ficha_id"] == "line-99"
    assert line["origem_linha"] == ORIGEM_FICHA_INTERMEDIARIA
    assert line["produto_ref_id"] == "ref1"
