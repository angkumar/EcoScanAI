"""Environmental scoring and recommendation logic."""

from __future__ import annotations

from typing import Dict, List, Tuple

IMPACT_TO_CO2 = {"Red": 5.0, "Yellow": 2.5, "Green": 0.8}
IMPACT_TO_LABEL = {"Red": "High Impact", "Yellow": "Medium Impact", "Green": "Low Impact"}
IMPACT_TO_POINTS = {"Red": 1, "Yellow": 2, "Green": 3}


def _normalize_text(values: List[str]) -> str:
    return " ".join(values).lower()


def score_product(product_data: Dict) -> Tuple[str, str]:
    """Return (impact_score, explanation) from Open Food Facts product payload."""
    categories = product_data.get("categories_tags") or []
    labels = product_data.get("labels_tags") or []
    packaging = product_data.get("packaging_tags") or []
    product_name = (product_data.get("product_name") or "").lower()
    ingredients = (product_data.get("ingredients_text") or "").lower()
    nova_group = str(product_data.get("nova_group") or "").strip()

    category_blob = _normalize_text(categories)
    label_blob = _normalize_text(labels)
    packaging_blob = _normalize_text(packaging)
    combined = " ".join([category_blob, label_blob, packaging_blob, product_name, ingredients])

    if "beef" in combined or "meat" in combined:
        return "Red", "Category indicates meat-heavy product (higher footprint)."

    if nova_group == "4" or "packaged-foods" in category_blob:
        return "Yellow", "Likely ultra-processed packaged food."

    if any(term in combined for term in ["plant", "vegan", "vegetarian", "plant-based"]):
        return "Green", "Plant-based indicators found."

    if any(term in packaging_blob for term in ["bulk", "recyclable", "paper"]):
        return "Green", "Lower-impact packaging indicators found."

    return "Yellow", "Insufficient certainty; assigned medium impact."


def estimate_co2(impact_score: str) -> float:
    """Map impact color to mocked CO2 estimate."""
    return IMPACT_TO_CO2.get(impact_score, 2.5)


def suggest_alternative(impact_score: str, product_name: str) -> str:
    """Generate an MVP lower-impact suggestion."""
    name = product_name.strip() or "this product"
    if impact_score == "Red":
        return f"Try a plant-based version of {name} and choose minimal packaging."
    if impact_score == "Yellow":
        return f"Consider a less-processed or refill/bulk alternative to {name}."
    return f"{name} is a lower-impact choice. Prioritize local sourcing when possible."

