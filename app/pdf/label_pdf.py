"""PDF de etiquetas de ingredientes para impressao via driver do Windows."""

from __future__ import annotations

import os
from datetime import datetime
from collections.abc import Callable
from typing import Any

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepInFrame, Paragraph, SimpleDocTemplate, Spacer

from app.utils.dates import timestamp_file
from app.utils.filenames import pdf_filename_stem

DEFAULT_LABEL_SIZE_MM = (100, 50)


def build_ingredient_label_payload(
    product: dict[str, Any],
    ingredients: list[dict[str, Any]],
    prep_steps: list[dict[str, Any]] | list[str] | None = None,
    nested_ingredient_resolver: Callable[[str], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Monta o payload publico da etiqueta a partir dos dados atuais da ficha."""
    label_ingredients = list(ingredients or [])
    if nested_ingredient_resolver is not None:
        product_id = str(product.get("produto_id", "") or "")
        visited = {product_id} if product_id else set()
        label_ingredients = expand_nested_ingredients_for_label(
            label_ingredients,
            nested_ingredient_resolver,
            visited_product_ids=visited,
        )
    return {
        "nome": str(product.get("nome", "") or ""),
        "ingredientes": label_ingredients,
    }


def expand_nested_ingredients_for_label(
    ingredients: list[dict[str, Any]],
    nested_ingredient_resolver: Callable[[str], list[dict[str, Any]]],
    visited_product_ids: set[str] | None = None,
    max_depth: int = 4,
) -> list[dict[str, Any]]:
    """Anexa nomes de ingredientes internos para fichas intermediarias usadas na etiqueta."""
    visited = set(visited_product_ids or set())
    expanded: list[dict[str, Any]] = []
    for ingredient in ingredients or []:
        item = dict(ingredient)
        ref_id = _product_ref_id(item)
        if ref_id and max_depth > 0 and ref_id not in visited:
            nested = _nested_ingredient_labels(
                ref_id,
                nested_ingredient_resolver,
                visited | {ref_id},
                max_depth - 1,
            )
            if nested:
                item["ingredientes_internos"] = nested
        expanded.append(item)
    return expanded


def generate_ingredient_label_pdf(
    product_payload: dict[str, Any],
    output_dir: str,
    label_size: tuple[float, float] = DEFAULT_LABEL_SIZE_MM,
) -> str:
    """Gera uma etiqueta em PDF e retorna o caminho completo do arquivo."""
    os.makedirs(output_dir, exist_ok=True)
    width_mm, height_mm = label_size
    page_size = (width_mm * mm, height_mm * mm)
    product_name = str(product_payload.get("nome", "") or "produto").strip() or "produto"
    filename = f"{pdf_filename_stem(product_name, timestamp_file())}.pdf"
    path = os.path.abspath(os.path.join(output_dir, filename))

    margin = 3 * mm
    doc = SimpleDocTemplate(
        path,
        pagesize=page_size,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
    )

    frame_width = page_size[0] - (2 * margin)
    frame_height = page_size[1] - (2 * margin)
    story = _build_story(product_payload)
    doc.build([KeepInFrame(frame_width, frame_height, story, mode="shrink")])
    return path


def _build_story(payload: dict[str, Any]) -> list[Any]:
    styles = _styles()
    story: list[Any] = []

    product_name = str(payload.get("nome", "") or "Produto sem nome").strip()
    story.append(Paragraph(_escape(product_name), styles["title"]))
    story.append(Spacer(1, 1.4))

    ingredients = list(payload.get("ingredientes") or [])
    for line in _ingredient_lines(ingredients):
        story.append(Paragraph(_escape(line), styles["normal"]))

    story.append(Spacer(1, 1.4))
    story.append(Paragraph(f"Data de geração: {datetime.now().strftime('%d/%m/%Y')}", styles["normal"]))

    return story


def _styles() -> dict[str, ParagraphStyle]:
    return {
        "label": ParagraphStyle(
            "LabelLabel",
            fontName="Helvetica-Bold",
            fontSize=5.8,
            leading=6.5,
            alignment=TA_LEFT,
            spaceAfter=0.2,
        ),
        "title": ParagraphStyle(
            "LabelTitle",
            fontName="Helvetica-Bold",
            fontSize=8.0,
            leading=8.8,
            alignment=TA_LEFT,
            spaceAfter=0.2,
        ),
        "normal": ParagraphStyle(
            "LabelNormal",
            fontName="Helvetica",
            fontSize=5.8,
            leading=6.6,
            alignment=TA_LEFT,
            spaceAfter=0.1,
        ),
    }


def _nested_ingredient_labels(
    product_id: str,
    nested_ingredient_resolver: Callable[[str], list[dict[str, Any]]],
    visited_product_ids: set[str],
    depth: int,
) -> list[str]:
    ingredients = nested_ingredient_resolver(product_id)

    labels: list[str] = []
    seen: set[str] = set()
    for ingredient in ingredients or []:
        name = _ingredient_name(ingredient)
        ref_id = _product_ref_id(ingredient)
        if ref_id and depth > 0 and ref_id not in visited_product_ids:
            children = _nested_ingredient_labels(
                ref_id,
                nested_ingredient_resolver,
                visited_product_ids | {ref_id},
                depth - 1,
            )
            if children:
                children_text = ", ".join(children)
                label = f"{name} ({children_text})" if name else children_text
            else:
                label = name
        else:
            label = name
        clean = label.strip()
        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            labels.append(clean)
    return labels


def _product_ref_id(ingredient: dict[str, Any]) -> str:
    return str(ingredient.get("produto_ref_id", "") or "").strip()


def _ingredient_name(ingredient: dict[str, Any]) -> str:
    return str(ingredient.get("nome") or ingredient.get("nome_ingrediente") or "").strip()


def _ingredient_lines(ingredients: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for item in ingredients:
        name = _ingredient_name(item)
        if not name:
            name = "(sem nome)"
        nested = _format_nested_ingredients(item.get("ingredientes_internos"))
        if nested:
            name = f"{name} ({nested})"
        lines.append(name)
    return lines or ["Nenhum ingrediente informado."]


def _format_nested_ingredients(value: object) -> str:
    if not isinstance(value, (list, tuple)):
        return ""
    names = [str(item or "").strip() for item in value]
    names = [item for item in names if item]
    if not names:
        return ""
    return ", ".join(names)


def _escape(text: object) -> str:
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
