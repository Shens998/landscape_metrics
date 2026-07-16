from landscape_metrics.metrics import load_metric_cards


EXPECTED_METRIC_IDS = {
    "aggregation_index",
    "area",
    "area_cv",
    "area_mean",
    "area_sd",
    "edge_density",
    "fractal_dimension",
    "largest_patch_index",
    "number_of_patches",
    "patch_density",
    "perimeter",
    "perimeter_area_ratio",
    "proportion_of_landscape",
    "radius_of_gyration",
    "shape_index",
    "shape_index_mean",
    "shannon_diversity",
    "shannon_evenness",
    "simpson_diversity",
    "total_area",
    "total_edge",
}


def test_all_public_metrics_have_formula_rules_and_stable_source() -> None:
    cards = load_metric_cards()

    assert set(cards) == EXPECTED_METRIC_IDS
    for metric_id, card in cards.items():
        assert card["id"] == metric_id
        assert card["source_kind"] in {"original", "definition_reference", "review"}
        assert card["formula"]
        assert card["rules"]
        assert card["unit"]
        assert card["level"]
        assert any(url.startswith("https://") for url in card["sources"])


def test_metric_cards_have_standard_display_names_and_latex_formulas() -> None:
    cards = load_metric_cards()

    for card in cards.values():
        assert card["name"]
        assert card["name_zh"]
        assert card["abbreviation"]
        assert card["formula"].startswith("\\(")
        assert card["formula"].endswith("\\)")
