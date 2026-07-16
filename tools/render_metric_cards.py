"""Render the public metric table from the package's single YAML source."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CARDS = yaml.safe_load(
    (ROOT / "src/landscape_metrics/metric_cards.yaml").read_text(encoding="utf-8")
)["metrics"]
ROWS = [
    "# Metric cards",
    "",
    "| Name | 中文名称 | ID | Level | Formula | Unit | Source |",
    "|---|---|---|---|---|---|---|",
]
for metric_id, card in CARDS.items():
    source = ", ".join(f"[source]({url})" for url in card["sources"])
    ROWS.append(
        f"| {card['name']} ({card['abbreviation']}) | {card['name_zh']} | {metric_id} | "
        f"{', '.join(card['level'])} | {card['formula']} | {card['unit']} | {source} |"
    )
ROWS.extend(
    [
        "",
        "Cards marked as original identify a cited original source. Definition references identify a transparent definition source without claiming original authorship.",
    ]
)
(ROOT / "docs/metrics.md").write_text("\n".join(ROWS) + "\n", encoding="utf-8")
