from app.utils import open_file_location


def test_reveal_file_in_explorer_uses_exact_pdf_path_on_windows(monkeypatch, tmp_path):
    pdf_path = tmp_path / "pdfs" / "ficha.pdf"
    pdf_path.parent.mkdir()
    pdf_path.write_text("pdf")
    calls = []

    monkeypatch.setattr(open_file_location.os, "name", "nt")
    monkeypatch.setattr(open_file_location.subprocess, "Popen", lambda args: calls.append(args))

    open_file_location.reveal_file_in_explorer(str(pdf_path))

    assert calls == [["explorer.exe", "/select,", str(pdf_path)]]
