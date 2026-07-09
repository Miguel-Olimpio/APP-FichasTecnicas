from app.services.validation_service import find_duplicate_ingredient_warning, validate_ingredient_row, validate_product_for_save
from app.utils.tipo_ficha import TIPO_FICHA_MATERIA_PRIMA, TIPO_FICHA_PRODUTO_FINAL


def test_product_sem_nome():
    p = {
        "nome": "",
        "categoria": "x",
        "tipo_ficha": TIPO_FICHA_PRODUTO_FINAL,
        "rendimento": 1,
        "unidade_rendimento": "kg",
        "quantidade_porcoes": 1,
    }
    r = validate_product_for_save(p, [{"x": 1}], [], "id1")
    assert not r.ok
    assert any("nome" in e.lower() for e in r.errors)


def test_product_sem_ingredientes():
    p = {
        "nome": "P",
        "categoria": "x",
        "tipo_ficha": TIPO_FICHA_PRODUTO_FINAL,
        "rendimento": 1,
        "unidade_rendimento": "kg",
        "quantidade_porcoes": 1,
    }
    r = validate_product_for_save(p, [], [], "id1")
    assert not r.ok
    assert any("ingrediente" in e.lower() for e in r.errors)


def test_yield_nao_padronizado_bloqueia_salvamento():
    p = {
        "nome": "P",
        "categoria": "x",
        "tipo_ficha": TIPO_FICHA_PRODUTO_FINAL,
        "rendimento": 1,
        "unidade_rendimento": "bandeja",
        "quantidade_porcoes": 1,
    }
    r = validate_product_for_save(p, [{"x": 1}], [], "id1")
    assert not r.ok
    assert any("unidade de rendimento válida" in e.lower() for e in r.errors)


def test_product_rendimento_obrigatorio_maior_que_zero():
    for rendimento in ("", 0, -1):
        p = {
            "nome": "P",
            "categoria": "x",
            "tipo_ficha": TIPO_FICHA_PRODUTO_FINAL,
            "rendimento": rendimento,
            "unidade_rendimento": "kg",
            "quantidade_porcoes": 1,
        }
        r = validate_product_for_save(p, [{"x": 1}], [], "id1")
        assert not r.ok
        assert any("rendimento" in e.lower() and "maior que zero" in e.lower() for e in r.errors)


def test_ingrediente_kg_com_unidade_un_invalido():
    ing = {
        "tipo": "simples",
        "nome": "Farinha",
        "quantidade": 1,
        "unidade": "un",
        "unidade_custo": "kg",
        "preco_kg": 5,
        "preco_unidade": 0,
    }
    r = validate_ingredient_row(ing, {})
    assert not r.ok
    assert any("massa" in e.lower() for e in r.errors)


def test_ingrediente_un_com_preco_kg_preenchido():
    ing = {
        "tipo": "simples",
        "nome": "Ovo",
        "quantidade": 6,
        "unidade": "un",
        "unidade_custo": "un",
        "preco_kg": 10,
        "preco_unidade": 1,
    }
    r = validate_ingredient_row(ing, {})
    assert not r.ok
    assert any("preço por kg" in e.lower() for e in r.errors)


def test_ingrediente_simples_porcao_custo():
    ing = {
        "tipo": "simples",
        "nome": "X",
        "quantidade": 1,
        "unidade": "porção",
        "unidade_custo": "porção",
        "preco_kg": 0,
        "preco_unidade": 0,
    }
    r = validate_ingredient_row(ing, {})
    assert not r.ok
    assert any("simples" in e.lower() and "porção" in e.lower() for e in r.errors)


def test_composto_preco_manual_bloqueado():
    ing = {
        "tipo": "produto_composto",
        "nome": "Ref",
        "produto_ref_id": "r1",
        "quantidade": 1,
        "unidade": "kg",
        "unidade_custo": "kg",
        "preco_kg": 5,
        "preco_unidade": 0,
    }
    r = validate_ingredient_row(
        ing,
        {
            "r1": {
                "produto_id": "r1",
                "tipo_ficha": TIPO_FICHA_MATERIA_PRIMA,
                "active": True,
                "custo_por_kg": 8,
            }
        },
    )
    assert not r.ok
    assert any("preço manual" in e.lower() for e in r.errors)


def test_composto_sem_ficha():
    ing = {
        "tipo": "produto_composto",
        "nome": "",
        "produto_ref_id": "",
        "quantidade": 1,
        "unidade": "kg",
        "unidade_custo": "kg",
        "preco_kg": 0,
        "preco_unidade": 0,
    }
    r = validate_ingredient_row(ing, {})
    assert not r.ok
    assert any("referência" in e.lower() for e in r.errors)


def test_product_tipo_ficha_vazio():
    p = {
        "nome": "P",
        "categoria": "x",
        "tipo_ficha": "",
        "rendimento": 1,
        "unidade_rendimento": "kg",
        "quantidade_porcoes": 1,
    }
    r = validate_product_for_save(p, [{"x": 1}], [], "id1")
    assert not r.ok
    assert any("tipo" in e.lower() and "obrigat" in e.lower() for e in r.errors)


def test_simples_litro_sem_preco_litro():
    ing = {
        "tipo": "simples",
        "nome": "Óleo",
        "quantidade": 1,
        "unidade": "L",
        "unidade_custo": "L",
        "preco_kg": 0,
        "preco_unidade": 0,
        "preco_litro": 0,
    }
    r = validate_ingredient_row(ing, {})
    assert not r.ok
    assert any("preço por litro" in e.lower() for e in r.errors)


def test_find_duplicate_ingredient_por_ficha_id():
    existing = [
        {
            "ingrediente_ficha_id": "a",
            "ingrediente_cadastro_id": "m1",
            "nome": "X",
            "tipo": "simples",
            "quantidade": 1,
            "unidade": "kg",
        }
    ]
    cand = {**existing[0], "ingrediente_ficha_id": "a", "quantidade": 2}
    assert not find_duplicate_ingredient_warning(existing, cand)


def test_composto_ref_produto_final_rejeitado():
    ing = {
        "tipo": "produto_composto",
        "nome": "Ref",
        "produto_ref_id": "r1",
        "quantidade": 1,
        "unidade": "kg",
        "unidade_custo": "kg",
        "preco_kg": 0,
        "preco_unidade": 0,
    }
    ref = {
        "produto_id": "r1",
        "tipo_ficha": TIPO_FICHA_PRODUTO_FINAL,
        "active": True,
        "custo_por_kg": 10,
    }
    r = validate_ingredient_row(ing, {"r1": ref})
    assert not r.ok
    assert any("ficha selecionada" in e.lower() for e in r.errors)
