"""AQI category bands (Indian CPCB National AQI standard)."""

# (upper bound inclusive, category name). Checked in order.
CPCB_BANDS = [
    (50, "Good"),
    (100, "Satisfactory"),
    (200, "Moderate"),
    (300, "Poor"),
    (400, "Very Poor"),
]


def aqi_category(aqi: float) -> str:
    """Map an AQI value to its CPCB category.

    Predictions are floats (e.g. 100.4), so we round first: 100.4 -> 100 ->
    "Satisfactory", matching how a published integer AQI would be labelled.
    """
    value = round(aqi)
    for upper, name in CPCB_BANDS:
        if value <= upper:
            return name
    return "Severe"
