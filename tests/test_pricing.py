import pytest

from app.repositories.excel_database import ExcelDatabase
from app.repositories.excel_schema import FICHAS_SHEETS_CONFIG
from app.repositories.prep_step_repository import PrepStepRepository
from app.repositories.pricing_repository import PricingRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.recipe_ingredient_repository import RecipeIngredientRepository
from app.services.pricing_service import STATUS_SAUDAVEL, calculate_pricing
from app.services.product_service import ProductService
from app.services.recipe_line_adapter import build_line_from_master


def test_calculate_pricing_converts_percentages_and_compares_current_price():
    product = {"nome": "Pão", "categoria": "Padaria", "custo_total": 10, "rendimento": 2, "unidade_rendimento": "kg"}
    manual = {
        "embalagem_unitaria": 1,
        "gas_energia_outros_unitario": 1,
        "taxa_cartao_percentual": 5,
        "taxa_aplicativo_percentual": 0,
        "margem_desejada_percentual": 30,
        "preco_atual_venda": 11,
    }

    result = calculate_pricing(product, manual)

    assert result["custo_materia_prima_unitario"] == 5
    assert result["custo_total_base"] == 7
    assert result["preco_ideal"] == pytest.approx(9.57894, rel=1e-4)
    assert result["preco_presencial"] == pytest.approx(9.1, rel=1e-4)
    assert result["preco_entrega"] == pytest.approx(9.1, rel=1e-4)
    assert result["preco_app"] == pytest.approx(9.1, rel=1e-4)
    assert result["lucro_estimado"] == pytest.approx(2.1, rel=1e-4)
    assert result["margem_estimada"] == pytest.approx(0.21923, rel=1e-4)
    assert result["status_financeiro"] == STATUS_SAUDAVEL


def test_calculate_pricing_allows_margin_above_100_percent_on_cost():
    product = {"nome": "Docinho", "categoria": "Doce", "custo_total": 1, "rendimento": 1, "unidade_rendimento": "un"}
    manual = {
        "margem_desejada_percentual": 400,
        "taxa_cartao_percentual": 0,
        "taxa_aplicativo_percentual": 0,
    }

    result = calculate_pricing(product, manual)

    assert result["preco_ideal"] == pytest.approx(5)
    assert result["preco_presencial"] == pytest.approx(5)
    assert result["preco_entrega"] == pytest.approx(5)
    assert result["preco_app"] == pytest.approx(5)
    assert result["lucro_estimado"] == pytest.approx(4)


def test_calculate_pricing_sale_scenarios_use_delivery_and_app_fee():
    product = {"nome": "Lanche", "categoria": "Salgado", "custo_total": 1, "rendimento": 1, "unidade_rendimento": "un"}
    manual = {
        "margem_desejada_percentual": 100,
        "taxa_cartao_percentual": 0,
        "taxa_aplicativo_percentual": 20,
        "custo_entrega_propria": 2,
        "custo_entrega_aplicativo": 3,
    }

    result = calculate_pricing(product, manual)

    assert result["preco_presencial"] == pytest.approx(2)
    assert result["preco_entrega"] == pytest.approx(6)
    assert result["preco_app"] == pytest.approx(10)
    assert result["preco_aplicativo"] == pytest.approx(10)


def test_calculate_pricing_uses_legacy_delivery_as_own_delivery():
    product = {"nome": "Lanche", "categoria": "Salgado", "custo_total": 1, "rendimento": 1, "unidade_rendimento": "un"}
    manual = {
        "margem_desejada_percentual": 100,
        "taxa_cartao_percentual": 0,
        "taxa_aplicativo_percentual": 0,
        "custo_entrega_unitario": 2,
    }

    result = calculate_pricing(product, manual)

    assert result["custo_entrega_propria"] == 2
    assert result["preco_entrega"] == pytest.approx(6)


def test_product_service_saves_and_replaces_pricing(tmp_path):
    db_path = tmp_path / "banco_fichas.xlsx"
    db = ExcelDatabase(str(db_path), FICHAS_SHEETS_CONFIG, "banco_fichas")
    db.ensure_database()
    pricing_repo = PricingRepository(db)
    service = ProductService(
        db,
        ProductRepository(db),
        RecipeIngredientRepository(db),
        prep_step_repo=PrepStepRepository(db),
        pricing_repo=pricing_repo,
    )
    product = {
        "produto_id": "p1",
        "nome": "Pão",
        "nome_normalizado": "",
        "categoria": "Padaria",
        "tipo_ficha": "produto_final",
        "rendimento": 1,
        "unidade_rendimento": "kg",
        "quantidade_porcoes": 1,
        "tempo_preparo": "",
        "temperatura": "",
        "modo_preparo": "",
        "observacoes": "",
        "custo_total": 0,
        "custo_por_unidade": 0,
        "custo_por_porcao": 0,
        "custo_por_kg": 0,
        "data_criacao": "",
        "data_atualizacao": "",
        "active": True,
    }
    ingredient = build_line_from_master(
        "p1",
        {
            "ingrediente_id": "i1",
            "nome": "Farinha",
            "classificacao": "ingrediente_simples",
            "unidade_custo": "kg",
            "preco_kg": 4,
            "preco_litro": 0,
            "preco_unidade": 0,
        },
        1,
        "kg",
    )

    service.save_product(
        product,
        [ingredient],
        [],
        {
            "embalagem_unitaria": 1,
            "custo_entrega_unitario": 3,
            "custo_entrega_propria": 3,
            "custo_entrega_aplicativo": 5,
            "preco_ideal": 8,
        },
    )
    assert service.get_pricing("p1")["embalagem_unitaria"] == 1
    assert service.get_pricing("p1")["custo_entrega_unitario"] == 3
    assert service.get_pricing("p1")["custo_entrega_propria"] == 3
    assert service.get_pricing("p1")["custo_entrega_aplicativo"] == 5

    service.save_product(
        product,
        [ingredient],
        [],
        {
            "embalagem_unitaria": 2,
            "custo_entrega_unitario": 4,
            "custo_entrega_propria": 4,
            "custo_entrega_aplicativo": 6,
            "preco_ideal": 9,
        },
    )
    rows = pricing_repo.list_all_rows()
    assert len(rows) == 1
    assert rows[0]["embalagem_unitaria"] == 2
    assert rows[0]["custo_entrega_unitario"] == 4
    assert rows[0]["custo_entrega_propria"] == 4
    assert rows[0]["custo_entrega_aplicativo"] == 6
