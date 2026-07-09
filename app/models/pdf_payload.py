"""DTO público para PDF (sem campos financeiros)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PdfIngredientLine:
    nome: str
    quantidade: object
    unidade: str


@dataclass(frozen=True)
class FichaTecnicaPdfPayload:
    nome: str
    categoria: str
    rendimento: object
    unidade_rendimento: str
    ingredientes: tuple[PdfIngredientLine, ...]
    passos_preparo: tuple[str, ...]
    modo_preparo: str
    tempo_preparo: str
    temperatura: str
    observacoes: str

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "FichaTecnicaPdfPayload":
        allowed = {
            "nome",
            "categoria",
            "rendimento",
            "unidade_rendimento",
            "ingredientes",
            "passos_preparo",
            "modo_preparo",
            "tempo_preparo",
            "temperatura",
            "observacoes",
        }
        extra = set(data.keys()) - allowed
        if extra:
            raise ValueError(f"Campos não permitidos no PDF: {sorted(extra)}")
        ings_raw = data.get("ingredientes") or ()
        ings = tuple(
            PdfIngredientLine(
                nome=str(x.get("nome", "")),
                quantidade=x.get("quantidade", ""),
                unidade=str(x.get("unidade", "")),
            )
            for x in ings_raw
        )
        passos = _normalize_passos_preparo(data.get("passos_preparo"), data.get("modo_preparo"))
        return FichaTecnicaPdfPayload(
            nome=str(data.get("nome", "")),
            categoria=str(data.get("categoria", "")),
            rendimento=data.get("rendimento", ""),
            unidade_rendimento=str(data.get("unidade_rendimento", "")),
            ingredientes=ings,
            passos_preparo=passos,
            modo_preparo=str(data.get("modo_preparo", "")),
            tempo_preparo=str(data.get("tempo_preparo", "")),
            temperatura=str(data.get("temperatura", "")),
            observacoes=str(data.get("observacoes", "")),
        )


def build_pdf_payload_from_public_dict(
    product_public: dict[str, Any],
    ingredient_lines: list[dict[str, Any]],
) -> FichaTecnicaPdfPayload:
    payload_dict = {
        "nome": product_public.get("nome", ""),
        "categoria": product_public.get("categoria", ""),
        "rendimento": product_public.get("rendimento", ""),
        "unidade_rendimento": product_public.get("unidade_rendimento", ""),
        "passos_preparo": product_public.get("passos_preparo", ()),
        "modo_preparo": product_public.get("modo_preparo", ""),
        "tempo_preparo": product_public.get("tempo_preparo", ""),
        "temperatura": product_public.get("temperatura", ""),
        "observacoes": product_public.get("observacoes", ""),
        "ingredientes": ingredient_lines,
    }
    return FichaTecnicaPdfPayload.from_dict(payload_dict)


def _normalize_passos_preparo(raw: object, legacy_modo: object = "") -> tuple[str, ...]:
    ordered: list[tuple[int, int, str]] = []
    if isinstance(raw, (list, tuple)):
        for pos, item in enumerate(raw, start=1):
            if isinstance(item, dict):
                descricao = str(item.get("descricao", "") or "").strip()
                ordem = _to_int(item.get("ordem"), pos)
            else:
                descricao = str(item or "").strip()
                ordem = pos
            if descricao:
                ordered.append((ordem, pos, descricao))
    if ordered:
        return tuple(desc for _ordem, _pos, desc in sorted(ordered, key=lambda x: (x[0], x[1])))
    legacy = str(legacy_modo or "").strip()
    if not legacy:
        return ()
    return tuple(line.strip() for line in legacy.splitlines() if line.strip())


def _to_int(value: object, default: int) -> int:
    try:
        return int(float(str(value).replace(",", ".")))
    except (TypeError, ValueError):
        return default
