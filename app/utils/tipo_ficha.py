"""Tipo de ficha técnica: produto final vs matéria-prima (valores internos e rótulos na UI)."""

from __future__ import annotations

TIPO_FICHA_PRODUTO_FINAL = "produto_final"
TIPO_FICHA_MATERIA_PRIMA = "materia_prima"

_LABELS: dict[str, str] = {
    TIPO_FICHA_PRODUTO_FINAL: "Produto final",
    TIPO_FICHA_MATERIA_PRIMA: "Matéria-prima / produto intermediário",
}
_LABEL_TO_VALUE = {v: k for k, v in _LABELS.items()}


def tipo_ficha_options() -> list[str]:
    """Rótulos para combobox readonly."""
    return [_LABELS[TIPO_FICHA_PRODUTO_FINAL], _LABELS[TIPO_FICHA_MATERIA_PRIMA]]


def tipo_ficha_label(value: object) -> str:
    """Valor interno -> rótulo amigável."""
    v = normalize_tipo_ficha(value)
    return _LABELS.get(v, _LABELS[TIPO_FICHA_PRODUTO_FINAL])


def tipo_ficha_from_label(label: str) -> str:
    """Rótulo da UI -> valor interno."""
    s = str(label or "").strip()
    return _LABEL_TO_VALUE.get(s, TIPO_FICHA_PRODUTO_FINAL)


def normalize_tipo_ficha(value: object) -> str:
    """Garante produto_final ou materia_prima (legado vazio -> produto_final)."""
    s = str(value or "").strip().lower()
    if s == TIPO_FICHA_MATERIA_PRIMA:
        return TIPO_FICHA_MATERIA_PRIMA
    return TIPO_FICHA_PRODUTO_FINAL


def is_materia_prima(value: object) -> bool:
    return normalize_tipo_ficha(value) == TIPO_FICHA_MATERIA_PRIMA
