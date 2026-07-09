"""Cálculo de precificação e comparação de lucro."""

from __future__ import annotations

from typing import Any

from app.utils.numbers import to_float


STATUS_PREJUIZO = "Produto com prejuízo"
STATUS_ABAIXO = "Lucro abaixo do desejado"
STATUS_SAUDAVEL = "Produto saudável"


def percent_to_decimal(value: object) -> float:
    return to_float(value) / 100.0


def calculate_pricing(product: dict[str, Any], manual: dict[str, Any]) -> dict[str, Any]:
    custo_total_ingredientes = to_float(product.get("custo_total"))
    rendimento = to_float(product.get("rendimento"))
    unidade_rendimento = str(product.get("unidade_rendimento", "") or "")
    margem_pct = to_float(manual.get("margem_desejada_percentual"))
    taxa_cartao_pct = to_float(manual.get("taxa_cartao_percentual"))
    taxa_app_pct = to_float(manual.get("taxa_aplicativo_percentual"))
    margem = percent_to_decimal(margem_pct)
    taxa_app = percent_to_decimal(taxa_app_pct)
    taxas = percent_to_decimal(taxa_cartao_pct + taxa_app_pct)

    result = _blank_result()
    result.update(
        {
            "nome": str(product.get("nome", "") or ""),
            "categoria": str(product.get("categoria", "") or ""),
            "custo_total_ingredientes": custo_total_ingredientes,
            "rendimento": rendimento,
            "unidade_rendimento": unidade_rendimento,
            "taxas_percentuais": taxas,
            "margem_desejada_decimal": margem,
            "alerts": [],
            "ok": False,
        }
    )

    if rendimento <= 0:
        result["alerts"].append("Informe rendimento maior que zero para calcular a precificação.")
        return result
    if custo_total_ingredientes <= 0:
        result["alerts"].append("Informe ingredientes com custo calculado para precificar.")
        return result
    if margem < 0:
        result["alerts"].append("Margem desejada sobre o custo não pode ser negativa.")
        return result
    if taxas < 0:
        result["alerts"].append("Taxas percentuais não podem ser negativas.")
        return result
    if taxa_app >= 1:
        result["alerts"].append("Taxa de aplicativo deve ser menor que 100%.")
        return result
    if taxas >= 1:
        result["alerts"].append("Taxas percentuais devem ser menores que 100%.")
        return result

    embalagem = to_float(manual.get("embalagem_unitaria"))
    outros = to_float(manual.get("gas_energia_outros_unitario"))
    custo_entrega_propria = to_float(
        manual.get("custo_entrega_propria", manual.get("custo_entrega_unitario"))
    )
    custo_entrega_aplicativo = to_float(manual.get("custo_entrega_aplicativo"))
    preco_atual_raw = str(manual.get("preco_atual_venda", "") or "").strip()
    preco_atual = to_float(preco_atual_raw)

    custo_materia_prima_unitario = custo_total_ingredientes / rendimento
    custo_complementar = embalagem + outros
    custo_total_base = custo_materia_prima_unitario + custo_complementar
    preco_sem_taxas = custo_total_base * (1 + margem)
    preco_ideal = preco_sem_taxas / (1 - taxas)
    preco_presencial = preco_sem_taxas
    preco_entrega_propria = (custo_total_base + custo_entrega_propria) * (1 + margem)
    preco_aplicativo = ((custo_total_base + custo_entrega_aplicativo) * (1 + margem)) / (1 - taxa_app)
    taxas_sobre_venda = preco_ideal * taxas
    lucro_estimado = preco_ideal - custo_total_base - taxas_sobre_venda
    margem_estimada = lucro_estimado / preco_ideal if preco_ideal > 0 else 0.0
    cmv = custo_materia_prima_unitario / preco_ideal if preco_ideal > 0 else 0.0
    markup = preco_ideal / custo_total_base if custo_total_base > 0 else 0.0

    result.update(
        {
            "ok": True,
            "custo_materia_prima_unitario": custo_materia_prima_unitario,
            "custo_complementar": custo_complementar,
            "custo_total_base": custo_total_base,
            "custo_entrega_unitario": custo_entrega_propria,
            "custo_entrega_propria": custo_entrega_propria,
            "custo_entrega_aplicativo": custo_entrega_aplicativo,
            "preco_sem_taxas": preco_sem_taxas,
            "preco_ideal": preco_ideal,
            "preco_presencial": preco_presencial,
            "preco_entrega": preco_entrega_propria,
            "preco_entrega_propria": preco_entrega_propria,
            "preco_app": preco_aplicativo,
            "preco_aplicativo": preco_aplicativo,
            "taxas_sobre_venda": taxas_sobre_venda,
            "lucro_estimado": lucro_estimado,
            "margem_estimada": margem_estimada,
            "cmv": cmv,
            "markup": markup,
        }
    )

    if cmv > 0.35:
        result["alerts"].append("CMV acima de 35%.")

    if not preco_atual_raw:
        return result
    if preco_atual <= 0:
        result["alerts"].append("Preço atual deve ser maior que zero para comparação.")
        return result

    taxas_preco_atual = preco_atual * taxas
    lucro_real = preco_atual - custo_total_base - taxas_preco_atual
    margem_real = lucro_real / preco_atual if preco_atual > 0 else 0.0
    diferenca_valor = preco_atual - preco_ideal
    diferenca_percentual = diferenca_valor / preco_ideal if preco_ideal > 0 else 0.0
    cmv_real = custo_materia_prima_unitario / preco_atual if preco_atual > 0 else 0.0

    if lucro_real < 0:
        status = STATUS_PREJUIZO
        result["alerts"].append("O preço atual gera prejuízo.")
    elif lucro_real < custo_total_base * margem:
        status = STATUS_ABAIXO
        result["alerts"].append("Lucro real abaixo da margem desejada sobre o custo.")
    else:
        status = STATUS_SAUDAVEL

    result.update(
        {
            "preco_atual_venda": preco_atual,
            "taxas_preco_atual": taxas_preco_atual,
            "lucro_real": lucro_real,
            "margem_real": margem_real,
            "diferenca_valor": diferenca_valor,
            "diferenca_percentual": diferenca_percentual,
            "cmv_real": cmv_real,
            "status_financeiro": status,
        }
    )
    return result


def _blank_result() -> dict[str, Any]:
    return {
        "custo_materia_prima_unitario": "",
        "custo_complementar": "",
        "custo_total_base": "",
        "custo_entrega_unitario": "",
        "custo_entrega_propria": "",
        "custo_entrega_aplicativo": "",
        "preco_sem_taxas": "",
        "preco_ideal": "",
        "preco_presencial": "",
        "preco_entrega": "",
        "preco_entrega_propria": "",
        "preco_app": "",
        "preco_aplicativo": "",
        "taxas_sobre_venda": "",
        "lucro_estimado": "",
        "margem_estimada": "",
        "cmv": "",
        "markup": "",
        "preco_atual_venda": "",
        "taxas_preco_atual": "",
        "lucro_real": "",
        "margem_real": "",
        "diferenca_valor": "",
        "diferenca_percentual": "",
        "cmv_real": "",
        "status_financeiro": "",
    }
