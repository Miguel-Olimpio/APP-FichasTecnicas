import re
from pathlib import Path

from reportlab.lib.units import mm

from app.pdf.label_pdf import (
    _build_story,
    _ingredient_lines,
    build_ingredient_label_payload,
    generate_ingredient_label_pdf,
)


def _payload(ingredients=None):
    product = {
        "nome": "Pao Frances",
        "rendimento": 20,
        "unidade_rendimento": "un",
        "observacoes": "Assar no mesmo dia.",
    }
    return build_ingredient_label_payload(
        product,
        ingredients
        or [
            {"nome": "Farinha", "quantidade": 1, "unidade": "kg"},
            {"nome": "Fermento", "quantidade": 10, "unidade": "g"},
        ],
        ["Misturar e sovar."],
    )


def test_generate_label_pdf_creates_file_and_returns_path(tmp_path):
    path = generate_ingredient_label_pdf(_payload(), str(tmp_path))

    assert Path(path).is_file()
    assert Path(path).parent == tmp_path
    assert re.match(r"^Pao_Frances_\d{8}_\d{6}\.pdf$", Path(path).name)


def test_generate_label_pdf_handles_many_ingredients(tmp_path):
    ingredients = [
        {"nome": f"Ingrediente {idx}", "quantidade": idx, "unidade": "g"}
        for idx in range(1, 20)
    ]

    path = generate_ingredient_label_pdf(_payload(ingredients), str(tmp_path))

    assert Path(path).is_file()
    assert Path(path).stat().st_size > 0


def test_label_payload_cites_intermediate_product_ingredients():
    product = {
        "produto_id": "pizza",
        "nome": "Pizza",
        "rendimento": 1,
        "unidade_rendimento": "un",
    }
    ingredients = [
        {
            "nome": "Massa de pizza",
            "tipo": "produto_composto",
            "produto_ref_id": "massa",
            "quantidade": 1,
            "unidade": "un",
        },
        {"nome": "Queijo", "quantidade": 200, "unidade": "g"},
    ]
    nested = {
        "massa": [
            {"nome": "Farinha", "quantidade": 1, "unidade": "kg"},
            {"nome": "Fermento", "quantidade": 10, "unidade": "g"},
        ]
    }

    payload = build_ingredient_label_payload(
        product,
        ingredients,
        nested_ingredient_resolver=lambda product_id: nested.get(product_id, []),
    )

    assert payload["ingredientes"][0]["ingredientes_internos"] == ["Farinha", "Fermento"]
    assert _ingredient_lines(payload["ingredientes"])[0] == "Massa de pizza (Farinha, Fermento)"


def test_label_uses_only_ingredient_names_without_quantities():
    lines = _ingredient_lines(
        [
            {"nome": "Farinha", "quantidade": "0,8", "unidade": "kg"},
            {"nome": "Leite", "quantidade": 0.8, "unidade": "L"},
        ]
    )

    assert lines == ["Farinha", "Leite"]


def test_label_story_does_not_include_prep_steps():
    story = _build_story(
        build_ingredient_label_payload(
            {"nome": "Pizza", "rendimento": 1, "unidade_rendimento": "un"},
            [{"nome": "Massa", "quantidade": 1, "unidade": "un"}],
            [{"ordem": 1, "descricao": "Assar por 10 minutos."}],
        )
    )
    rendered_text = "\n".join(getattr(item, "getPlainText", lambda: "")() for item in story)

    assert "Preparo" not in rendered_text
    assert "Assar por 10 minutos" not in rendered_text
    assert "Rendimento" not in rendered_text
    assert "Produto:" not in rendered_text
    assert "Ingredientes:" not in rendered_text
    assert "Obs:" not in rendered_text
    assert "Gerado em" not in rendered_text
    assert "Data de geração" in rendered_text
    assert "Massa" in rendered_text


def test_label_keeps_all_ingredients_in_story():
    ingredients = [
        {"nome": f"Ingrediente {idx}", "quantidade": idx, "unidade": "g"}
        for idx in range(1, 20)
    ]

    lines = _ingredient_lines(ingredients)

    assert len(lines) == 19
    assert lines[0] == "Ingrediente 1"
    assert lines[-1] == "Ingrediente 19"


def test_generate_label_pdf_uses_requested_page_size(tmp_path):
    path = generate_ingredient_label_pdf(_payload(), str(tmp_path), label_size=(100, 50))
    raw = Path(path).read_bytes()
    match = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([0-9.]+)\s+([0-9.]+)\s*\]", raw)

    assert match is not None
    width = float(match.group(1))
    height = float(match.group(2))
    assert width == pytest_approx(100 * mm)
    assert height == pytest_approx(50 * mm)


def pytest_approx(value):
    import pytest

    return pytest.approx(value, rel=1e-4)
