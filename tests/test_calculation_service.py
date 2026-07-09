from app.services.recipe_calculation_service import calc_ingredient_cost, recalc_product


def test_simple_kg_cost():
    ing = {
        "tipo": "simples",
        "quantidade": 2,
        "unidade": "kg",
        "unidade_custo": "kg",
        "preco_kg": 10,
        "preco_unidade": 0,
    }
    assert calc_ingredient_cost(ing, {}) == 20.0


def test_simple_volume_litro_cost():
    ing = {
        "tipo": "simples",
        "quantidade": 500,
        "unidade": "mL",
        "unidade_custo": "L",
        "preco_kg": 0,
        "preco_unidade": 0,
        "preco_litro": 20.0,
    }
    assert abs(calc_ingredient_cost(ing, {}) - 10.0) < 1e-6


def test_simple_unidade_cost():
    ing = {
        "tipo": "simples",
        "quantidade": 3,
        "unidade": "un",
        "unidade_custo": "unidade",
        "preco_kg": 0,
        "preco_unidade": 5,
    }
    assert calc_ingredient_cost(ing, {}) == 15.0


def test_composto_kg():
    ref = {
        "produto_id": "r1",
        "custo_por_kg": 8,
        "custo_por_unidade": 1,
        "custo_por_porcao": 2,
    }
    by_id = {"r1": ref}
    ing = {
        "tipo": "produto_composto",
        "produto_ref_id": "r1",
        "quantidade": 500,
        "unidade": "g",
        "unidade_custo": "kg",
    }
    assert abs(calc_ingredient_cost(ing, by_id) - 4.0) < 1e-6


def test_composto_porcao():
    ref = {"produto_id": "r1", "custo_por_porcao": 3, "custo_por_kg": 0, "custo_por_unidade": 0}
    ing = {
        "tipo": "produto_composto",
        "produto_ref_id": "r1",
        "quantidade": 2,
        "unidade": "porcao",
        "unidade_custo": "porcao",
    }
    assert calc_ingredient_cost(ing, {"r1": ref}) == 6.0


def test_recalc_custo_por_porcao_produto():
    p = {
        "produto_id": "p1",
        "rendimento": 10,
        "unidade_rendimento": "kg",
        "quantidade_porcoes": 5,
    }
    ings = [
        {
            "tipo": "simples",
            "quantidade": 1,
            "unidade": "kg",
            "unidade_custo": "kg",
            "preco_kg": 20,
            "preco_unidade": 0,
        }
    ]
    pd, _, _ = recalc_product(p, ings, {})
    assert pd["custo_total"] == 20.0
    assert pd["custo_por_unidade"] == 2.0
    assert pd["custo_por_porcao"] == 4.0


def test_custo_por_kg_rendimento_g():
    p = {"produto_id": "p1", "rendimento": 500, "unidade_rendimento": "g", "quantidade_porcoes": 1}
    ings = [
        {
            "tipo": "simples",
            "quantidade": 0.25,
            "unidade": "kg",
            "unidade_custo": "kg",
            "preco_kg": 40,
            "preco_unidade": 0,
        }
    ]
    pd, _, _ = recalc_product(p, ings, {})
    assert abs(pd["custo_por_kg"] - 20.0) < 0.01


def test_warning_rendimento_volume():
    p = {"produto_id": "p1", "rendimento": 1, "unidade_rendimento": "L", "quantidade_porcoes": 1}
    ings = [
        {
            "tipo": "simples",
            "quantidade": 1,
            "unidade": "L",
            "unidade_custo": "un",
            "preco_kg": 0,
            "preco_unidade": 1,
        }
    ]
    _pd, _, warns = recalc_product(p, ings, {})
    assert any("volume" in w.lower() for w in warns)
