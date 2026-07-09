"""Cabeçalhos e nomes de abas — fonte única (fichas vs cadastro mestre)."""

from app.config import settings as cfg

PRODUCT_HEADERS = [
    "produto_id",
    "nome",
    "nome_normalizado",
    "categoria",
    "tipo_ficha",
    "rendimento",
    "unidade_rendimento",
    "quantidade_porcoes",
    "tempo_preparo",
    "temperatura",
    "modo_preparo",
    "observacoes",
    "custo_total",
    "custo_por_unidade",
    "custo_por_porcao",
    "custo_por_kg",
    "data_criacao",
    "data_atualizacao",
    "active",
]

# Linhas de receita na ficha (banco_fichas.xlsx — aba IngredientesFicha).
RECIPE_LINE_HEADERS = [
    "ingrediente_ficha_id",
    "produto_id",
    "origem_linha",
    "ingrediente_id",
    "produto_ref_id",
    "nome_ingrediente",
    "classificacao_ingrediente",
    "quantidade_utilizada",
    "unidade_utilizada",
    "unidade_custo",
    "preco_kg_snapshot",
    "preco_litro_snapshot",
    "preco_unidade_snapshot",
    "custo_calculado",
    "proporcao",
    "observacoes",
]

PREP_STEP_HEADERS = [
    "produto_id",
    "ordem",
    "descricao",
]

PRICING_HEADERS = [
    "produto_id",
    "embalagem_unitaria",
    "gas_energia_outros_unitario",
    "custo_entrega_unitario",
    "custo_entrega_propria",
    "custo_entrega_aplicativo",
    "taxa_cartao_percentual",
    "taxa_aplicativo_percentual",
    "margem_desejada_percentual",
    "preco_atual_venda",
    "canal_venda",
    "preco_ideal",
    "lucro_estimado",
    "margem_estimada",
    "lucro_real",
    "margem_real",
    "cmv",
    "markup",
    "status_financeiro",
    "data_atualizacao",
]

# Cadastro mestre (banco_ingredientes.xlsx).
MASTER_INGREDIENT_HEADERS = [
    "ingrediente_id",
    "nome",
    "nome_normalizado",
    "classificacao",
    "categoria",
    "unidade_padrao",
    "unidade_custo",
    "preco_kg",
    "preco_litro",
    "preco_unidade",
    "observacoes",
    "data_criacao",
    "data_atualizacao",
    "active",
]

AUDIT_HEADERS = [
    "log_id",
    "entidade",
    "entidade_id",
    "acao",
    "descricao",
    "data_hora",
]

# Formato legado em banco_fichas.xlsx antes da v2 (aba "Ingredientes").
LEGACY_INGREDIENT_HEADERS = [
    "ingrediente_id",
    "produto_id",
    "nome",
    "nome_normalizado",
    "tipo",
    "produto_ref_id",
    "quantidade",
    "unidade",
    "preco_unidade",
    "preco_kg",
    "unidade_custo",
    "proporcao",
    "custo_calculado",
    "observacoes",
]

LEGACY_CATALOG_HEADERS = [
    "ingrediente_catalogo_id",
    "nome",
    "nome_normalizado",
    "unidade_padrao",
    "preco_unidade_padrao",
    "preco_kg_padrao",
    "unidade_custo_padrao",
    "data_criacao",
    "data_atualizacao",
    "active",
]

FICHAS_SHEETS_CONFIG: dict[str, list[str]] = {
    cfg.SHEET_PRODUTOS: PRODUCT_HEADERS,
    cfg.SHEET_INGREDIENTES_FICHA: RECIPE_LINE_HEADERS,
    cfg.SHEET_PASSOS_PREPARO: PREP_STEP_HEADERS,
    cfg.SHEET_PRECIFICACAO: PRICING_HEADERS,
    cfg.SHEET_AUDIT: AUDIT_HEADERS,
}

MASTER_SHEETS_CONFIG: dict[str, list[str]] = {
    cfg.SHEET_INGREDIENTES_MESTRE: MASTER_INGREDIENT_HEADERS,
}
