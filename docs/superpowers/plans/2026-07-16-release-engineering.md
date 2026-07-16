# Release Engineering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Add CI, citation metadata, contribution/release documents, and reproducible package-build validation for the public alpha library.

**Architecture:** A GitHub Actions workflow validates each push and pull request on Python 3.11 and 3.12. Static project files state the existing alpha version and MIT license, while local tests validate their essential fields without contacting external services.

**Tech Stack:** GitHub Actions, Python 3.11/3.12, Hatchling, build, PyYAML, pytest, Ruff, mypy.

## Global Constraints

- Keep v0.1 calculations, public API, 21 metric IDs, and runtime dependencies unchanged.
- Do not upload packages, create releases, access private data, or add telemetry.
- Workflow permissions are read-only and it must run pytest, Ruff, mypy, and package build.
- Software author is Shi Shen; version remains 0.1.0a0 and license remains MIT.

---

### Task 1: Release metadata, documents, and test contracts

**Files:**

- Modify: pyproject.toml
- Create: CITATION.cff
- Create: CONTRIBUTING.md
- Create: CHANGELOG.md
- Modify: tests/test_release_docs.py

- [ ] **Step 1: Write failing release-document tests**

~~~python
def test_release_metadata_identifies_the_alpha_package() -> None:
    citation = yaml.safe_load(Path("CITATION.cff").read_text(encoding="utf-8"))
    assert citation["title"] == "Open Landscape Metrics"
    assert citation["version"] == "0.1.0a0"
    assert citation["license"] == "MIT"
    assert citation["authors"][0]["family-names"] == "Shen"
    assert citation["authors"][0]["given-names"] == "Shi"
~~~

Also assert CONTRIBUTING.md and CHANGELOG.md exist and identify alpha scope. Run the focused test and confirm it fails before files exist.

- [ ] **Step 2: Add minimal release files and build dependency**

Add build>=1.2 to the dev extra. Write CFF 1.2 metadata for Shi Shen and the GitHub repository URL. Document test-first contributions, no compatibility claims, and alpha scope. Create an Unreleased changelog entry covering exact chunking, metric selection, and standard metric-card names.

- [ ] **Step 3: Verify document contracts and package build**

Run:

~~~bash
python -m pytest tests/test_release_docs.py -v
python -m build
~~~

Confirm dist contains one wheel and one source distribution. Commit metadata and documents.

### Task 2: CI workflow and local verification

**Files:**

- Create: .github/workflows/ci.yml
- Modify: tests/test_release_docs.py

- [ ] **Step 1: Write the failing workflow test**

~~~python
def test_ci_runs_supported_python_checks() -> None:
    text = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "pull_request:" in text
    assert "3.11" in text and "3.12" in text
    assert "pytest -q" in text
    assert "ruff check src tests tools benchmarks" in text
    assert "mypy src" in text
    assert "python -m build" in text
~~~

- [ ] **Step 2: Add minimal GitHub Actions workflow**

Use ubuntu-latest, permissions contents: read, setup-python matrix [3.11, 3.12], pip install -e .[dev], pytest, Ruff, mypy, and a build step. Upload no artifacts and use no secrets.

- [ ] **Step 3: Verify and commit**

Run:

~~~bash
python -m pytest -q
python -m ruff check src tests tools benchmarks
python -m mypy src
python -m build
~~~

Commit CI, tests, the plan and design record with message ci: add release validation workflow.
