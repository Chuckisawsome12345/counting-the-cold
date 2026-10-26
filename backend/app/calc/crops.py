"""GDD presets (°F). Thresholds follow UC IPM degree-day models for each crop's key pest."""

CROPS = {
    "almond": {"id": "almond", "label": "Almond (navel orangeworm)", "base_f": 55.0, "upper_f": 94.0},
    "pistachio": {"id": "pistachio", "label": "Pistachio (navel orangeworm)", "base_f": 55.0, "upper_f": 94.0},
    "walnut": {"id": "walnut", "label": "Walnut (codling moth)", "base_f": 50.0, "upper_f": 88.0},
    "prune": {"id": "prune", "label": "Prune (peach twig borer)", "base_f": 50.0, "upper_f": 88.0},
    # Kept for API callers; the app offers only crops it can also give a bloom verdict for.
    "generic": {"id": "generic", "label": "Generic (base 50°F)", "base_f": 50.0, "upper_f": None},
}
