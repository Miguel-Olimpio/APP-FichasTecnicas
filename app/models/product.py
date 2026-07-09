"""Modelo de produto / ficha técnica."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.utils.filenames import normalize_name_key
from app.utils.numbers import to_float


def _parse_bool(value: object, default: bool = True) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in ("0", "false", "n", "no", "nao", "não"):
        return False
    if s in ("1", "true", "s", "sim", "yes"):
        return True
    return default


@dataclass
class Product:
    produto_id: str
    nome: str = ""
    nome_normalizado: str = ""
    categoria: str = ""
    tipo_ficha: str = "produto_final"
    rendimento: float = 0.0
    unidade_rendimento: str = ""
    quantidade_porcoes: float = 1.0
    tempo_preparo: str = ""
    temperatura: str = ""
    modo_preparo: str = ""
    observacoes: str = ""
    custo_total: float = 0.0
    custo_por_unidade: float = 0.0
    custo_por_porcao: float = 0.0
    custo_por_kg: float = 0.0
    data_criacao: str = ""
    data_atualizacao: str = ""
    active: bool = True

    def sync_derived(self) -> None:
        self.nome_normalizado = normalize_name_key(self.nome)

    def to_row_dict(self) -> dict[str, Any]:
        self.sync_derived()
        d = asdict(self)
        return d

    @classmethod
    def from_row_dict(cls, row: dict[str, Any]) -> Product:
        return cls(
            produto_id=str(row.get("produto_id", "") or ""),
            nome=str(row.get("nome", "") or ""),
            nome_normalizado=str(row.get("nome_normalizado", "") or ""),
            categoria=str(row.get("categoria", "") or ""),
            tipo_ficha=str(row.get("tipo_ficha", "") or "produto_final"),
            rendimento=to_float(row.get("rendimento")),
            unidade_rendimento=str(row.get("unidade_rendimento", "") or ""),
            quantidade_porcoes=to_float(row.get("quantidade_porcoes")) or 1.0,
            tempo_preparo=str(row.get("tempo_preparo", "") or ""),
            temperatura=str(row.get("temperatura", "") or ""),
            modo_preparo=str(row.get("modo_preparo", "") or ""),
            observacoes=str(row.get("observacoes", "") or ""),
            custo_total=to_float(row.get("custo_total")),
            custo_por_unidade=to_float(row.get("custo_por_unidade")),
            custo_por_porcao=to_float(row.get("custo_por_porcao")),
            custo_por_kg=to_float(row.get("custo_por_kg")),
            data_criacao=str(row.get("data_criacao", "") or ""),
            data_atualizacao=str(row.get("data_atualizacao", "") or ""),
            active=_parse_bool(row.get("active"), True),
        )


def product_to_public_pdf_dict(p: Product) -> dict[str, Any]:
    """Somente campos permitidos no PDF (sem financeiro)."""
    return {
        "nome": p.nome,
        "categoria": p.categoria,
        "rendimento": p.rendimento,
        "unidade_rendimento": p.unidade_rendimento,
        "tempo_preparo": p.tempo_preparo,
        "temperatura": p.temperatura,
        "modo_preparo": p.modo_preparo,
        "observacoes": p.observacoes,
    }
