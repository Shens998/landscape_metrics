# Standard Metric Names and LaTeX Formulas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Present v0.1 metric cards with conventional landscape-ecology names, abbreviations, Chinese names, and LaTeX formulas without changing stable machine IDs or calculations.

**Architecture:** `metric_cards.yaml` remains the sole source of metric metadata. Each card adds display fields while retaining its established Python result-column ID. The render tool reads those fields to rebuild `docs/metrics.md` deterministically.

**Tech Stack:** Python 3.11+, PyYAML, Markdown, pytest, Ruff.

## Global Constraints

- Keep all 21 v0.1 metric IDs, levels, calculations, output columns, and citations unchanged.
- Do not add FRAGSTATS or PyLandStats compatibility claims or copy software code or text.
- Use conventional metric terms and abbreviations only as human-facing display metadata.
- Store formula notation as Markdown-compatible LaTeX delimited by `\(` and `\)`.

---

### Task 1: Add standard display metadata and render it

**Files:**

- Modify: `src/landscape_metrics/metric_cards.yaml`
- Modify: `tools/render_metric_cards.py`
- Modify: `tests/test_metric_cards.py`
- Modify: `tests/test_release_docs.py`
- Modify: `docs/metrics.md`

**Interfaces:**

- Each card continues to expose `id`, `level`, `formula`, `unit`, `rules`, `source_kind`, and `sources`.
- Each card additionally exposes non-empty `name`, `name_zh`, and `abbreviation` strings.
- `python tools/render_metric_cards.py` produces `docs/metrics.md` with Name, 中文名称, ID, Level, Formula, Unit, and Source columns.

- [ ] **Step 1: Write failing metadata and rendered-document tests**

```python
def test_metric_cards_have_standard_display_names_and_latex_formulas() -> None:
    cards = load_metric_cards()
    for card in cards.values():
        assert card["name"]
        assert card["name_zh"]
        assert card["abbreviation"]
        assert card["formula"].startswith("\\(")
        assert card["formula"].endswith("\\)")
```

Add document assertions for `Patch Area (AREA)` and `\( a_{ij} \)`.

- [ ] **Step 2: Verify the red state**

Run: `.venv/bin/python -m pytest tests/test_metric_cards.py tests/test_release_docs.py -v`

Expected: FAIL because the cards lack display fields and formulas are plain text.

- [ ] **Step 3: Add standard names and LaTeX formula metadata**

Use display names such as `Patch Area` / `AREA` / `斑块面积`, `Edge Density` / `ED` / `边缘密度`, and `Largest Patch Index` / `LPI` / `最大斑块指数`. Rewrite each existing card formula as a compact LaTeX expression while retaining its numerical meaning.

- [ ] **Step 4: Render the documentation**

Update `tools/render_metric_cards.py` to render the display metadata. Run `.venv/bin/python tools/render_metric_cards.py`.

- [ ] **Step 5: Verify and commit**

Run `.venv/bin/python -m pytest -q`, `.venv/bin/python -m ruff check src tests tools benchmarks`, and `.venv/bin/python -m mypy src`. Then commit the five implementation files with message `docs: standardize metric names and formulas`.
