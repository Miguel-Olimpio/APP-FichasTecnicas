"""Cálculo de custos e proporções de receita."""

from __future__ import annotations

from typing import Any

from app.models.enums import IngredienteTipo
from app.models.ingredient import Ingredient
from app.models.product import Product
from app.utils.numbers import to_float
from app.utils.units import (
    is_mass_unit,
    is_volume_unit,
    is_yield_unit_count_or_portion,
    normalize_cost_unit_key,
    normalize_unit,
    to_kg,
    to_liter,
    unit_family,
)


def _uc(ing: Ingredient | dict[str, Any]) -> str:
    if isinstance(ing, Ingredient):
        return normalize_unit(ing.unidade_custo)
    return normalize_unit(ing.get("unidade_custo"))


def _ref_dict(products_by_id: dict[str, dict[str, Any]], ref_id: str) -> dict[str, Any] | None:
    key = str(ref_id)
    p = products_by_id.get(key)
    return p


def calc_ingredient_cost(
    ingredient: Ingredient | dict[str, Any],
    products_by_id: dict[str, dict[str, Any]],
) -> float:
    """Calcula custo de um ingrediente (simples ou composto)."""
    if isinstance(ingredient, Ingredient):
        tipo = ingredient.tipo
        q = ingredient.quantidade
        unidade = ingredient.unidade
        uc_raw = str(ingredient.unidade_custo or "")
        preco_kg = ingredient.preco_kg
        preco_unidade = ingredient.preco_unidade
        preco_litro = getattr(ingredient, "preco_litro", 0.0) or 0.0
        ref_id = ingredient.produto_ref_id
    else:
        tipo = str(ingredient.get("tipo", IngredienteTipo.SIMPLES.value))
        q = to_float(ingredient.get("quantidade"))
        unidade = ingredient.get("unidade", "")
        uc_raw = str(ingredient.get("unidade_custo", "") or "")
        preco_kg = to_float(ingredient.get("preco_kg"))
        preco_unidade = to_float(ingredient.get("preco_unidade"))
        preco_litro = to_float(ingredient.get("preco_litro"))
        ref_id = str(ingredient.get("produto_ref_id", "") or "")

    uc_key = normalize_cost_unit_key(uc_raw)

    if tipo == IngredienteTipo.PRODUTO_COMPOSTO.value:
        ref = _ref_dict(products_by_id, ref_id)
        if not ref:
            return 0.0
        if uc_key == "kg":
            custo_ref = to_float(ref.get("custo_por_kg"))
            return to_kg(q, unidade) * custo_ref
        if uc_key == "porção":
            custo_ref = to_float(ref.get("custo_por_porcao"))
            return q * custo_ref
        custo_ref = to_float(ref.get("custo_por_unidade"))
        return q * custo_ref

    if uc_key == "kg":
        return to_kg(q, unidade) * preco_kg
    if uc_key in ("l", "ml"):
        return to_liter(q, unidade) * preco_litro
    return q * preco_unidade


def _ing_as_dict(ing: Ingredient | dict[str, Any]) -> dict[str, Any]:
    if isinstance(ing, Ingredient):
        return ing.to_row_dict()
    return dict(ing)


def recalc_product(
    product: Product | dict[str, Any],
    ingredients: list[Ingredient | dict[str, Any]],
    products_by_id: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    """
    Recalcula custos e proporções.
    Retorna (product_dict, ingredient_dicts, warnings).
    """
    warnings: list[str] = []

    if isinstance(product, Product):
        pdict = product.to_row_dict()
    else:
        pdict = dict(product)

    ing_dicts = [_ing_as_dict(i) for i in ingredients]

    families = [unit_family(ing.get("unidade")) for ing in ing_dicts]
    known = [f for f in families if f is not None]
    uniform = bool(known) and len(known) == len(ing_dicts) and len(set(known)) == 1

    total_mass_kg = 0.0
    total_volume_l = 0.0
    total_count = 0.0
    total_portion = 0.0
    ref_unit_for_count: str | None = None

    for ing in ing_dicts:
        u = ing.get("unidade")
        q = to_float(ing.get("quantidade"))
        fam = unit_family(u)
        if fam == "mass":
            total_mass_kg += to_kg(q, u)
        elif fam == "volume":
            total_volume_l += to_liter(q, u)
        elif fam == "count":
            nu = normalize_unit(u)
            if ref_unit_for_count is None:
                ref_unit_for_count = nu
            elif ref_unit_for_count != nu:
                uniform = False
            total_count += q
        elif fam == "portion":
            total_portion += q

    if uniform and known and known[0] == "portion" and total_portion <= 0:
        uniform = False

    total_cost = 0.0
    for ing in ing_dicts:
        cost = calc_ingredient_cost(ing, products_by_id)
        ing["custo_calculado"] = round(cost, 4)
        total_cost += cost

        fam = unit_family(ing.get("unidade"))
        q = to_float(ing.get("quantidade"))
        prop = 0.0
        if uniform and fam == "mass" and total_mass_kg > 0:
            prop = round(to_kg(q, ing.get("unidade")) / total_mass_kg * 100, 4)
        elif uniform and fam == "volume" and total_volume_l > 0:
            prop = round(to_liter(q, ing.get("unidade")) / total_volume_l * 100, 4)
        elif uniform and fam == "count" and total_count > 0:
            prop = round(q / total_count * 100, 4)
        elif uniform and fam == "portion" and total_portion > 0:
            prop = round(q / total_portion * 100, 4)
        elif len(ing_dicts) == 1:
            prop = 100.0 if fam is not None else 0.0
        ing["proporcao"] = prop

    if len(ing_dicts) > 1 and not uniform:
        warnings.append(
            "Unidades mistas na receita: a proporção foi zerada para ingredientes incompatíveis "
            "(não se misturam kg, litro e unidade como mesma grandeza)."
        )

    rendimento = to_float(pdict.get("rendimento"))
    q_porcoes = to_float(pdict.get("quantidade_porcoes"))
    if q_porcoes <= 0:
        q_porcoes = 0.0

    pdict["custo_total"] = round(total_cost, 4)
    pdict["custo_por_unidade"] = round(total_cost / rendimento, 4) if rendimento > 0 else 0.0
    pdict["custo_por_porcao"] = round(total_cost / q_porcoes, 4) if q_porcoes > 0 else 0.0

    unidade_rendimento = normalize_unit(pdict.get("unidade_rendimento"))
    ur_raw = pdict.get("unidade_rendimento")
    if unidade_rendimento in ("kg", "quilo", "quilos"):
        pdict["custo_por_kg"] = round(total_cost / rendimento, 4) if rendimento > 0 else 0.0
    elif unidade_rendimento in ("g", "gr", "grama", "gramas"):
        kg = rendimento / 1000.0
        pdict["custo_por_kg"] = round(total_cost / kg, 4) if kg > 0 else 0.0
    else:
        pdict["custo_por_kg"] = 0.0

    if not is_mass_unit(ur_raw):
        if is_volume_unit(ur_raw):
            warnings.append(
                "Custo por kg não é implementado para unidade de rendimento em volume (L/mL)."
            )
        elif is_yield_unit_count_or_portion(ur_raw):
            warnings.append(
                "Custo por kg não é aplicável quando o rendimento é em unidade ou porção."
            )
        elif ur_raw and str(ur_raw).strip():
            warnings.append(
                "Custo por kg não foi calculado para a unidade de rendimento informada."
            )

    return pdict, ing_dicts, warnings


def build_products_by_id_from_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(r.get("produto_id")): dict(r) for r in rows if r.get("produto_id")}
