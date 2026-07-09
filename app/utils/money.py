"""Formatação monetária para interface (não usar em PDF)."""


def format_money_br(value: object) -> str:
    try:
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "R$ 0,00"
