"""Geração de PDF sem dados financeiros."""

from __future__ import annotations

import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from app.config.paths import get_pdfs_dir
from app.models.pdf_payload import FichaTecnicaPdfPayload, build_pdf_payload_from_public_dict
from app.utils.dates import timestamp_file
from app.utils.filenames import pdf_filename_stem, safe_filename
from app.utils.units import format_quantity_with_unit

__all__ = ["FichaTecnicaPdfPayload", "build_pdf_payload_from_public_dict", "generate_pdf", "wrap_text"]


def wrap_text(text: str, limit: int) -> list[str]:
    result: list[str] = []
    for raw_line in str(text or "").splitlines():
        words = raw_line.split()
        if not words:
            result.append("")
            continue
        current = ""
        for w in words:
            if len(current) + len(w) + 1 <= limit:
                current = f"{current} {w}".strip()
            else:
                result.append(current)
                current = w
        if current:
            result.append(current)
    return result or [""]


def generate_pdf(payload: FichaTecnicaPdfPayload) -> str:
    pdf_dir = get_pdfs_dir()
    os.makedirs(pdf_dir, exist_ok=True)
    stem = pdf_filename_stem(safe_filename(payload.nome), timestamp_file())
    path = os.path.join(pdf_dir, f"{stem}.pdf")

    c = canvas.Canvas(path, pagesize=A4)
    height = A4[1]
    y = height - 2 * cm

    def line(text: str, size: int = 10, bold: bool = False, gap: float = 0.55) -> None:
        nonlocal y
        if y < 2 * cm:
            c.showPage()
            y = height - 2 * cm
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(2 * cm, y, str(text))
        y -= gap * cm

    line("FICHA TÉCNICA", 16, True, 0.9)
    line(f"Produto: {payload.nome}", 12, True)
    line(f"Categoria: {payload.categoria}", 10)
    line(f"Rendimento: {format_quantity_with_unit(payload.rendimento, payload.unidade_rendimento)}", 10)
    line("")

    line("Ingredientes", 12, True)
    for ing in payload.ingredientes:
        line(f"- {ing.nome}: {format_quantity_with_unit(ing.quantidade, ing.unidade)}", 10)

    line("")
    line("Modo de preparo", 12, True)
    for idx, descricao in enumerate(payload.passos_preparo, start=1):
        for paragraph in wrap_text(f"{idx}. {descricao}", 95):
            line(paragraph, 10)

    obs = str(payload.observacoes or "").strip()
    if obs:
        line("")
        line("Observações técnicas", 12, True)
        for paragraph in wrap_text(obs, 95):
            line(paragraph, 10)

    c.save()
    return path
