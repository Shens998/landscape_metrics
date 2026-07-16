"""Regression checks for public project documentation."""

from pathlib import Path

import yaml

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


def test_release_metadata_identifies_the_alpha_package() -> None:
    citation = yaml.safe_load(Path("CITATION.cff").read_text(encoding="utf-8"))

    assert citation["title"] == "Open Landscape Metrics"
    assert citation["version"] == "0.1.0a0"
    assert citation["license"] == "MIT"
    assert citation["authors"][0]["family-names"] == "Shen"
    assert citation["authors"][0]["given-names"] == "Shi"
    assert "alpha" in Path("CONTRIBUTING.md").read_text(encoding="utf-8").lower()
    assert "Unreleased" in Path("CHANGELOG.md").read_text(encoding="utf-8")


def test_ci_runs_supported_python_checks() -> None:
    text = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "pull_request:" in text
    assert "3.11" in text and "3.12" in text
    assert "pytest -q" in text
    assert "ruff check src tests tools benchmarks" in text
    assert "mypy src" in text
    assert "python -m build" in text
