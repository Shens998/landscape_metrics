"""Regression checks for public project documentation."""

from pathlib import Path


def test_readme_has_bilingual_project_introduction_and_public_api_example() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    assert "## 中文简介" in text
    assert "## English overview" in text
    assert "Landscape.from_geotiff" in text
    assert "FRAGSTATS-compatible" not in text


def test_public_docs_describe_selection_and_exact_chunking_without_compatibility_claims() -> None:
    text = (
        Path("README.md").read_text(encoding="utf-8")
        + Path("docs/methods.md").read_text(encoding="utf-8")
    )

    assert 'metrics=["edge_density"]' in text
    assert "48 bytes/像元" in text
    assert "FRAGSTATS-compatible" not in text
    assert "PyLandStats-compatible" not in text


def test_metric_cards_document_standard_names_and_latex_formulas() -> None:
    text = Path("docs/metrics.md").read_text(encoding="utf-8")

    assert "Patch Area (AREA)" in text
    assert "\\( AREA = a_{ij} \\)" in text
