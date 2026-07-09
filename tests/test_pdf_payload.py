import pytest

from app.config.settings import ORIGEM_CADASTRO_MESTRE
from app.models.ingredient import Ingredient, ingredient_to_pdf_line
from app.models.pdf_payload import FichaTecnicaPdfPayload, build_pdf_payload_from_public_dict


def test_payload_rejects_financial_keys():
    with pytest.raises(ValueError):
        FichaTecnicaPdfPayload.from_dict({"nome": "x", "custo_total": 1})


def test_build_from_public():
    pub = {"nome": "Bolo", "categoria": "Doce", "rendimento": 1, "unidade_rendimento": "kg"}
    lines = [{"nome": "Farinha", "quantidade": 1, "unidade": "kg"}]
    p = build_pdf_payload_from_public_dict(pub, lines)
    assert p.nome == "Bolo"
    assert len(p.ingredientes) == 1


def test_build_from_public_with_prep_steps():
    pub = {
        "nome": "Bolo",
        "categoria": "Doce",
        "rendimento": 1,
        "unidade_rendimento": "kg",
        "passos_preparo": [
            {"ordem": 2, "descricao": "Assar até dourar."},
            {"ordem": 1, "descricao": "Misturar os ingredientes."},
        ],
    }
    p = build_pdf_payload_from_public_dict(pub, [])
    assert p.passos_preparo == ("Misturar os ingredientes.", "Assar até dourar.")


def test_ingredient_to_pdf_line_from_ingredientes_ficha_row():
    """PDF usa nome / quantidade / unidade a partir da linha persistida (snapshots)."""
    row = {
        "ingrediente_ficha_id": "x1",
        "produto_id": "p1",
        "origem_linha": ORIGEM_CADASTRO_MESTRE,
        "ingrediente_id": "m1",
        "produto_ref_id": "",
        "nome_ingrediente": "Açúcar",
        "classificacao_ingrediente": "",
        "quantidade_utilizada": 200,
        "unidade_utilizada": "g",
        "unidade_custo": "kg",
        "preco_kg_snapshot": 5,
        "preco_litro_snapshot": 0,
        "preco_unidade_snapshot": 0,
        "custo_calculado": 1,
        "proporcao": 10,
        "observacoes": "",
    }
    ing = Ingredient.from_row_dict(row)
    line = ingredient_to_pdf_line(ing)
    assert line["nome"] == "Açúcar"
    assert line["quantidade"] == 200
    assert line["unidade"] == "g"
