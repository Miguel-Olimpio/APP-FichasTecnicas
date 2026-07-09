"""Configurações globais da aplicação."""

APP_TITLE = "Fichas Técnicas Alimentícias"

SHEET_PRODUTOS = "Produtos"
# Uso de ingredientes na ficha (não é cadastro mestre).
SHEET_INGREDIENTES_FICHA = "IngredientesFicha"
SHEET_PASSOS_PREPARO = "PassosPreparo"
SHEET_PRECIFICACAO = "Precificacao"
SHEET_AUDIT = "AuditLog"

# Cadastro mestre (banco_ingredientes.xlsx).
SHEET_INGREDIENTES_MESTRE = "Ingredientes"

# Legado (migração one-shot a partir de banco_fichas.xlsx antigo).
SHEET_INGREDIENTES_LEGACY = "Ingredientes"
SHEET_CATALOGO_LEGACY = "CatalogoIngredientes"

ORIGEM_CADASTRO_MESTRE = "cadastro_mestre"
ORIGEM_FICHA_INTERMEDIARIA = "ficha_intermediaria"

CLASSIFICACAO_INGREDIENTE_SIMPLES = "ingrediente_simples"
CLASSIFICACAO_MATERIA_PRIMA = "materia_prima"

ENABLE_AUDIT_LOG = True

MSG_SAVE_EXCEL_LOCKED = (
    "Não foi possível salvar. Verifique se o arquivo Excel está aberto e tente novamente."
)

MSG_CYCLE_DEPENDENCY = (
    "Não é possível salvar esta ficha, pois ela criaria uma dependência circular "
    "entre produtos compostos."
)
