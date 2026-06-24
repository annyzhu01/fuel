from unittest.mock import patch, MagicMock
from ingest_pdf import extract_text_chunks


def _mock_pdf(n_pages: int):
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Recipe text on page"
    mock_pdf = MagicMock()
    mock_pdf.__enter__ = lambda s: s
    mock_pdf.__exit__ = MagicMock(return_value=False)
    mock_pdf.pages = [mock_page] * n_pages
    return mock_pdf


def test_small_pdf_single_chunk():
    with patch("ingest_pdf.pdfplumber.open", return_value=_mock_pdf(10)):
        chunks = extract_text_chunks("fake.pdf", max_pages_before_chunk=40)
    assert len(chunks) == 1


def test_large_pdf_splits():
    with patch("ingest_pdf.pdfplumber.open", return_value=_mock_pdf(60)):
        chunks = extract_text_chunks("fake.pdf", max_pages_before_chunk=40, pages_per_chunk=10, overlap=2)
    assert len(chunks) > 1


def test_boundary_pdf_single_chunk():
    with patch("ingest_pdf.pdfplumber.open", return_value=_mock_pdf(40)):
        chunks = extract_text_chunks("fake.pdf", max_pages_before_chunk=40)
    assert len(chunks) == 1
