"""Validações de produto e ingrediente."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models.enums import IngredienteTipo
from app.utils.numbers import to_float
from app.utils.tipo_ficha import (
    TIPO_FICHA_MATERIA_PRIMA,
    TIPO_FICHA_PRODUTO_FINAL,
    normalize_tipo_ficha,
)
from app.utils.units import (
    YIELD_UNIT_OPTIONS,
    is_valid_unit_for_cost_unit,
    normalize_cost_unit_key,
    normalize_unit as nu,
)


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


def validate_product_for_save(
    product: dict[str, Any],
    ingredients: list[dict[str, Any]],
    existing_active_products: list[dict[str, Any]],
    current_product_id: str,
) -> ValidationResult:
    res = ValidationResult()
    nome = str(product.get("nome", "") or "").strip()
    if not nome:
        res.errors.append("O nome do produto é obrigatório.")

    cat = str(product.get("categoria", "") or "").strip()
    if not cat:
        res.errors.append("A categoria é obrigatória.")

    raw_tf = str(product.get("tipo_ficha", "") or "").strip().lower()
    if not raw_tf:
        res.errors.append("O tipo da ficha técnica é obrigatório.")
    elif raw_tf not in (TIPO_FICHA_PRODUTO_FINAL, TIPO_FICHA_MATERIA_PRIMA):
        res.errors.append(
            "O tipo da ficha técnica é inválido. Selecione Produto final ou Matéria-prima / produto intermediário."
        )

    rend = to_float(product.get("rendimento"))
    if rend <= 0:
        res.errors.append(
            "Informe a quantidade de rendimento da receita. Ela é obrigatória e deve ser maior que zero."
        )

    ur = str(product.get("unidade_rendimento", "") or "").strip()
    if not ur:
        res.errors.append("A unidade de rendimento é obrigatória.")
    else:
        norm_allowed = {nu(x) for x in YIELD_UNIT_OPTIONS}
        if nu(ur) not in norm_allowed:
            allowed = ", ".join(YIELD_UNIT_OPTIONS)
            res.errors.append(
                f"Selecione uma unidade de rendimento válida: {allowed}. "
                f"O valor informado foi '{ur}'."
            )

    qp = to_float(product.get("quantidade_porcoes"))
    if qp < 0:
        res.errors.append("A quantidade de porções não pode ser negativa.")

    if not ingredients:
        res.errors.append("É necessário informar pelo menos um ingrediente.")

    key = nome.strip().lower()
    for p in existing_active_products:
        if str(p.get("produto_id")) == str(current_product_id):
            continue
        if str(p.get("nome", "")).strip().lower() == key and key:
            res.errors.append("Já existe uma ficha técnica ativa com esse nome.")
            break

    tempo = str(product.get("tempo_preparo", "") or "").strip()
    if tempo and len(tempo) < 2:
        res.errors.append("Informe um tempo de preparo válido ou deixe em branco.")

    temp = str(product.get("temperatura", "") or "").strip()
    if temp and len(temp) < 2:
        res.errors.append("Informe uma temperatura clara ou deixe em branco.")

    return res


def validate_ingredient_row(
    ing: dict[str, Any],
    products_by_id: dict[str, dict[str, Any]],
) -> ValidationResult:
    res = ValidationResult()
    tipo = str(ing.get("tipo", IngredienteTipo.SIMPLES.value))
    q = to_float(ing.get("quantidade"))
    unidade = str(ing.get("unidade", "") or "").strip()
    uc_raw = str(ing.get("unidade_custo", "") or "").strip()
    uc_key = normalize_cost_unit_key(uc_raw)
    preco_kg = to_float(ing.get("preco_kg"))
    preco_un = to_float(ing.get("preco_unidade"))
    preco_li = to_float(ing.get("preco_litro"))

    if tipo == IngredienteTipo.SIMPLES.value:
        nome = str(ing.get("nome", "") or "").strip()
        if not nome:
            res.errors.append("Ingrediente simples: o nome é obrigatório.")
    else:
        ref = str(ing.get("produto_ref_id", "") or "").strip()
        if not ref:
            res.errors.append("Produto composto: selecione a ficha de referência.")

    if q <= 0:
        res.errors.append("A quantidade do ingrediente deve ser maior que zero.")
    if not unidade:
        res.errors.append("A unidade do ingrediente é obrigatória.")

    if unidade and uc_raw:
        if not is_valid_unit_for_cost_unit(unidade, uc_raw):
            if uc_key == "kg":
                res.errors.append(
                    "Unidade de custo 'kg' só aceita unidades de massa (kg, g). Ajuste a unidade usada."
                )
            elif uc_key == "un":
                res.errors.append(
                    "Unidade de custo 'un' só aceita unidades de contagem "
                    "(un, pacote, caixa, dúzia). Ajuste a unidade usada."
                )
            elif uc_key == "porção":
                res.errors.append(
                    "Unidade de custo 'porção' só aceita a unidade 'porção' na quantidade usada."
                )
            elif uc_key in ("l", "ml"):
                res.errors.append(
                    "Unidade de custo em volume (L) só aceita L ou mL na quantidade usada."
                )
            else:
                res.errors.append(
                    "A unidade usada não combina com a unidade de custo informada. Revise os dois campos."
                )

    if tipo == IngredienteTipo.SIMPLES.value:
        if uc_key == "porção":
            res.errors.append(
                "Ingredientes simples não podem usar unidade de custo 'porção'. "
                "Use 'kg' ou 'un', ou cadastre como produto composto."
            )
        elif uc_key == "kg":
            if preco_kg < 0:
                res.errors.append("O preço por kg não pode ser negativo.")
            elif preco_kg <= 0:
                res.errors.append("Informe o Preço por kg (deve ser maior que zero) quando a unidade de custo for 'kg'.")
            if preco_un > 0:
                res.errors.append(
                    "Com unidade de custo 'kg', o Preço por unidade deve ficar zerado (use apenas Preço por kg)."
                )
            if preco_li > 0:
                res.errors.append("Com unidade de custo 'kg', o preço por litro deve ficar zerado.")
        elif uc_key == "un":
            if preco_un < 0:
                res.errors.append("O preço por unidade não pode ser negativo.")
            elif preco_un <= 0:
                res.errors.append(
                    "Informe o Preço por unidade (maior que zero) quando a unidade de custo for 'un'."
                )
            if preco_kg > 0:
                res.errors.append(
                    "Com unidade de custo 'un', o Preço por kg deve ficar zerado (use apenas Preço por unidade)."
                )
            if preco_li > 0:
                res.errors.append("Com unidade de custo 'un', o preço por litro deve ficar zerado.")
        elif uc_key in ("l", "ml"):
            if preco_li < 0:
                res.errors.append("O preço por litro não pode ser negativo.")
            elif preco_li <= 0:
                res.errors.append(
                    "Informe o Preço por litro (maior que zero) quando a unidade de custo for volume (L)."
                )
            if preco_kg > 0 or preco_un > 0:
                res.errors.append(
                    "Com unidade de custo em volume (L), deixe preço por kg e por unidade zerados."
                )
        else:
            if preco_kg < 0:
                res.errors.append("O preço por kg não pode ser negativo.")
            if preco_un < 0:
                res.errors.append("O preço por unidade não pode ser negativo.")

    if tipo == IngredienteTipo.PRODUTO_COMPOSTO.value:
        if preco_kg > 0 or preco_un > 0 or preco_li > 0:
            res.errors.append(
                "Produto composto não aceita preço manual: o custo vem da ficha selecionada. "
                "Deixe preços manuais zerados."
            )
        ref = str(ing.get("produto_ref_id", "") or "")
        ref_p = products_by_id.get(ref)
        if ref_p:
            if normalize_tipo_ficha(ref_p.get("tipo_ficha")) != TIPO_FICHA_MATERIA_PRIMA:
                res.errors.append(
                    "Produto composto: a ficha selecionada precisa estar marcada como "
                    "\"Matéria-prima / produto intermediário\" para ser usada como ingrediente."
                )
            a = ref_p.get("active")
            if a in (False, "false", "FALSE", 0, "0"):
                res.errors.append("Produto composto: a ficha referenciada está inativa.")
            if uc_key == "kg":
                if to_float(ref_p.get("custo_por_kg")) <= 0:
                    res.errors.append(
                        "Para custo por kg, a ficha referenciada precisa ter custo por kg calculado."
                    )
            elif uc_key == "porção":
                cpp = to_float(ref_p.get("custo_por_porcao"))
                qpr = to_float(ref_p.get("quantidade_porcoes"))
                if cpp <= 0 and qpr <= 0:
                    res.errors.append(
                        "Para custo por porção, a ficha referenciada precisa de porções e custo por porção válidos."
                    )
            else:
                if to_float(ref_p.get("custo_por_unidade")) <= 0:
                    res.errors.append(
                        "Para custo por unidade, a ficha referenciada precisa ter custo por unidade calculado."
                    )

    return res


def _line_id(ing: dict[str, Any]) -> str:
    return str(ing.get("ingrediente_ficha_id") or ing.get("ingrediente_id") or "")


def find_duplicate_ingredient_warning(ingredients: list[dict[str, Any]], candidate: dict[str, Any]) -> bool:
    """Duplicação grosseira: mesmo nome (simples) ou mesmo ref (composto)."""
    tipo = str(candidate.get("tipo"))
    nome = str(candidate.get("nome", "") or "").strip().lower()
    ref = str(candidate.get("produto_ref_id", "") or "")
    cid = str(candidate.get("ingrediente_cadastro_id", "") or "")
    iid = _line_id(candidate)
    for ing in ingredients:
        if _line_id(ing) == iid and iid:
            continue
        if str(ing.get("tipo")) != tipo:
            continue
        if tipo == IngredienteTipo.SIMPLES.value:
            if cid and str(ing.get("ingrediente_cadastro_id", "") or "") == cid and cid:
                return True
            if str(ing.get("nome", "")).strip().lower() == nome and nome:
                return True
        else:
            if str(ing.get("produto_ref_id", "") or "") == ref and ref:
                return True
    return False
