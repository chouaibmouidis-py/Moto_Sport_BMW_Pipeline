from pypdf import PdfWriter
from vortex_support import VORTEX_EXTENSION_DIRECTORY

from experiments.storage_formats.benchmark_pdf_blob import benchmark_pdf


def test_pdf_blob_benchmark_preserves_all_bytes(tmp_path):
    source = tmp_path / "source.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(source)
    original = source.read_bytes()
    report = benchmark_pdf(source, VORTEX_EXTENSION_DIRECTORY, pairs=2)
    assert report["input_bytes"] == len(original)
    assert report["pages"] == 1
    assert [record["format"] for record in report["measurements"]] == [
        "parquet",
        "vortex",
        "vortex",
        "parquet",
    ]
    assert all(record["exact_match"] for record in report["measurements"])
    assert all(record["size_bytes"] > 0 for record in report["measurements"])
    assert source.read_bytes() == original
    assert set(tmp_path.iterdir()) == {source}
