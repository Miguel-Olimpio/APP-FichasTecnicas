from pathlib import Path

from app.models.pdf_payload import build_pdf_payload_from_public_dict
from app.services import pdf_service


def test_generate_pdf_formats_sub_kilo_and_sub_liter_quantities(monkeypatch, tmp_path):
    drawn: list[str] = []

    class FakeCanvas:
        def __init__(self, path, pagesize):
            self.path = path
            self.pagesize = pagesize

        def setFont(self, *_args):
            pass

        def drawString(self, _x, _y, text):
            drawn.append(text)

        def showPage(self):
            pass

        def save(self):
            pass

    monkeypatch.setattr(pdf_service.canvas, "Canvas", FakeCanvas)
    monkeypatch.setattr(pdf_service, "get_pdfs_dir", lambda: str(tmp_path))
    monkeypatch.setattr(pdf_service, "timestamp_file", lambda: "20260514_101112")

    payload = build_pdf_payload_from_public_dict(
        {
            "nome": "Massa",
            "categoria": "Base",
            "rendimento": "0,8",
            "unidade_rendimento": "kg",
        },
        [
            {"nome": "Farinha", "quantidade": "0,8", "unidade": "kg"},
            {"nome": "Leite", "quantidade": 0.8, "unidade": "L"},
        ],
    )

    path = pdf_service.generate_pdf(payload)

    assert Path(path).name == "Massa_20260514_101112.pdf"
    assert "Rendimento: 800 g" in drawn
    assert "- Farinha: 800 g" in drawn
    assert "- Leite: 800 mL" in drawn
