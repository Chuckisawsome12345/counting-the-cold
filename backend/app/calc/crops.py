"""GDD presets (°F). Thresholds follow UC IPM degree-day models."""

CROPS = {
    "almond": {"id": "almond", "label": "Almond (navel orangeworm)", "base_f": 55.0, "upper_f": 94.0},
    "walnut": {"id": "walnut", "label": "Walnut (codling moth)", "base_f": 50.0, "upper_f": 88.0},
    "generic": {"id": "generic", "label": "Generic (base 50°F)", "base_f": 50.0, "upper_f": None},
}
