from app.repositories.excel_database import ExcelDatabase
from app.repositories.excel_schema import FICHAS_SHEETS_CONFIG
from app.repositories.prep_step_repository import PrepStepRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.recipe_ingredient_repository import RecipeIngredientRepository
from app.services.product_service import ProductService
from app.services.recipe_line_adapter import build_line_from_master


def test_product_service_saves_loads_and_replaces_prep_steps(tmp_path):
    db_path = tmp_path / "banco_fichas.xlsx"
    db = ExcelDatabase(str(db_path), FICHAS_SHEETS_CONFIG, "banco_fichas")
    db.ensure_database()
    prep_repo = PrepStepRepository(db)
    service = ProductService(
        db,
        ProductRepository(db),
        RecipeIngredientRepository(db),
        prep_step_repo=prep_repo,
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

    service.save_product(product, [ingredient], ["Misturar.", "Assar."])
    assert [r["descricao"] for r in service.get_prep_steps("p1")] == ["Misturar.", "Assar."]

    service.save_product(product, [ingredient], ["Assar novamente."])
    assert [r["descricao"] for r in service.get_prep_steps("p1")] == ["Assar novamente."]
