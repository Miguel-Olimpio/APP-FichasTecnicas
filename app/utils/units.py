"""Normalização e conversão de unidades (sem misturar grandezas incompatíveis)."""

from __future__ import annotations

import unicodedata

from app.utils.numbers import to_float


def _strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


_MASS = frozenset(
    {
        "kg",
        "g",
        "gr",
        "quilo",
        "quilos",
        "grama",
        "gramas",
    }
)
_VOLUME = frozenset(
    {
        "l",
        "litro",
        "litros",
        "ml",
        "mililitro",
        "mililitros",
    }
)
_COUNT = frozenset(
    {
        "un",
        "unidade",
        "unidades",
        "pacote",
        "pacotes",
        "caixa",
        "caixas",
        "duzia",
        "duzias",
    }
)


def normalize_unit(unit: object) -> str:
    s = str(unit or "").strip().lower()
    return _strip_accents(s)


def is_mass_unit(unit: object) -> bool:
    return normalize_unit(unit) in _MASS


def is_volume_unit(unit: object) -> bool:
    return normalize_unit(unit) in _VOLUME


def is_unit_count(unit: object) -> bool:
    return normalize_unit(unit) in _COUNT


def is_count_unit(unit: object) -> bool:
    """Alias público de is_unit_count (contagem: un, pacote, caixa, dúzia)."""
    return is_unit_count(unit)


def to_kg(quantity: object, unit: object) -> float:
    u = normalize_unit(unit)
    q = to_float(quantity)
    if u in ("kg", "quilo", "quilos"):
        return q
    if u in ("g", "gr", "grama", "gramas"):
        return q / 1000.0
    return q


def to_liter(quantity: object, unit: object) -> float:
    u = normalize_unit(unit)
    q = to_float(quantity)
    if u in ("l", "litro", "litros"):
        return q
    if u in ("ml", "mililitro", "mililitros"):
        return q / 1000.0
    return q


def units_are_compatible(unit_a: object, unit_b: object) -> bool:
    a, b = normalize_unit(unit_a), normalize_unit(unit_b)
    if a == b:
        return True
    if is_mass_unit(a) and is_mass_unit(b):
        return True
    if is_volume_unit(a) and is_volume_unit(b):
        return True
    if is_unit_count(a) and is_unit_count(b):
        return True
    return False


def unit_family(unit: object) -> str | None:
    """Retorna 'mass', 'volume', 'count' ou None se não reconhecido."""
    if is_mass_unit(unit):
        return "mass"
    if is_volume_unit(unit):
        return "volume"
    if is_unit_count(unit):
        return "count"
    u = normalize_unit(unit)
    if u in ("porcao", "porcoes"):
        return "portion"
    return None


# --- Listas padronizadas (UI / validação) ---

MASS_UNITS = ["kg", "g"]
VOLUME_UNITS = ["L", "mL"]
COUNT_UNITS = ["un", "pacote", "caixa", "dúzia"]
PORTION_UNITS = ["porção"]
TIME_UNITS = ["min", "h"]
TEMPERATURE_UNITS = ["°C"]

COST_UNIT_OPTIONS = ["kg", "L", "un", "porção"]
YIELD_UNIT_OPTIONS = ["kg", "L", "un"]

INGREDIENT_TYPE_OPTIONS: list[tuple[str, str]] = [
    ("simples", "Ingrediente simples"),
    ("produto_composto", "Produto/ficha técnica cadastrada"),
]

PRODUCT_CATEGORIES = [
    "Lanche / Sanduíche",
    "Hambúrguer",
    "Hot dog",
    "Wrap / Tapioca",
    "Salgado assado",
    "Salgado frito",
    "Pão / Panificação",
    "Bolo / Torta",
    "Doce / Sobremesa",
    "Biscoito / Cookie",
    "Pizza",
    "Massa / Macarrão",
    "Molho / Base",
    "Recheio / Cobertura",
    "Bebida quente",
    "Bebida gelada / Suco",
    "Açaí / Sorvete",
    "Acompanhamento / Porção",
    "Salada",
    "Café da manhã",
    "Kit / Combo",
    "Outros",
]


def normalize_cost_unit_key(cost_unit: object) -> str:
    """Mapeia unidade de custo para chave lógica (kg | l | un | porção)."""
    u = normalize_unit(cost_unit)
    if u in ("kg",):
        return "kg"
    if u in ("l", "litro", "litros"):
        return "l"
    if u in ("ml", "mililitro", "mililitros"):
        return "ml"
    if u in ("un", "unidade", "unidades"):
        return "un"
    if u in ("porcao", "porcoes"):
        return "porção"
    return u


def get_units_for_cost_unit(cost_unit: object) -> list[str]:
    """Unidades permitidas para 'Unidade usada' conforme a unidade de custo."""
    key = normalize_cost_unit_key(cost_unit)
    if key == "kg":
        return list(MASS_UNITS)
    if key in ("l", "ml"):
        return list(VOLUME_UNITS)
    if key == "un":
        return list(COUNT_UNITS)
    if key == "porção":
        return list(PORTION_UNITS)
    # Legado desconhecido: oferece todas as opções padronizadas para não travar a UI
    return list(MASS_UNITS) + list(COUNT_UNITS) + list(PORTION_UNITS)


def is_valid_unit_for_cost_unit(unit: object, cost_unit: object) -> bool:
    allowed = {normalize_unit(x) for x in get_units_for_cost_unit(cost_unit)}
    return normalize_unit(unit) in allowed


def ensure_in_options(value: object, options: list[str]) -> list[str]:
    """Garante que `value` (ex.: legado) apareça nas opções do combobox."""
    v = str(value or "").strip()
    if not v:
        return list(options)
    norm_opts = {normalize_unit(o): o for o in options}
    nu = normalize_unit(v)
    if nu in norm_opts:
        return list(options)
    return list(options) + [v]


def is_yield_unit_mass(yield_unit: object) -> bool:
    return is_mass_unit(yield_unit)


def is_yield_unit_volume(yield_unit: object) -> bool:
    return is_volume_unit(yield_unit)


def is_yield_unit_count_or_portion(yield_unit: object) -> bool:
    u = normalize_unit(yield_unit)
    return is_unit_count(yield_unit) or u in ("porcao", "porcoes")


def format_quantity_with_unit(quantity: object, unit: object) -> str:
    """Formata quantidades para PDF/etiqueta, usando subunidade quando fizer sentido."""
    unit_text = str(unit or "").strip()
    if unit_text:
        q = to_float(quantity)
        norm_unit = normalize_unit(unit_text)
        if 0 < abs(q) < 1:
            if norm_unit in ("kg", "quilo", "quilos"):
                return f"{_format_display_number(q * 1000)} g"
            if norm_unit in ("l", "litro", "litros"):
                return f"{_format_display_number(q * 1000)} mL"
        quantity_text = _format_display_number(quantity)
        return f"{quantity_text} {unit_text}".strip() if quantity_text else ""
    return _format_display_number(quantity)


def _format_display_number(value: object) -> str:
    if value in (None, ""):
        return ""
    number = to_float(value)
    if isinstance(value, str) and number == 0 and value.strip() not in ("0", "0.0", "0,0"):
        return value.strip()
    text = f"{number:.4f}".rstrip("0").rstrip(".")
    if text == "-0":
        text = "0"
    return text.replace(".", ",")
