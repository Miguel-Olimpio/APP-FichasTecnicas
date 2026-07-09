from enum import Enum


class IngredienteTipo(str, Enum):
    SIMPLES = "simples"
    PRODUTO_COMPOSTO = "produto_composto"
