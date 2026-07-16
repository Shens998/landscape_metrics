"""Regression checks for public project documentation."""

from pathlib import Path


def test_readme_has_bilingual_project_introduction_and_public_api_example() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    assert "## 中文简介" in text
    assert "## English overview" in text
    assert "Landscape.from_geotiff" in text
    assert "FRAGSTATS-compatible" not in text
