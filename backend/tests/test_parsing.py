from app.ingestion.parsing import extract_text


def test_extract_text_plain():
    assert extract_text("notes.txt", b"hello world") == "hello world"


def test_extract_text_invalid_pdf_degrades_gracefully():
    result = extract_text("broken.pdf", b"not a real pdf")
    assert "failed to parse PDF" in result


def test_extract_text_unsupported_binary_falls_back():
    result = extract_text("diagram.png", b"\x89PNG...")
    assert "unparsed binary document" in result
