"""City-based disposal guidance module."""

from __future__ import annotations

from typing import Dict

SUPPORTED_CITIES = ("San Francisco", "Chicago")

CITY_DISPOSAL_RULES = {
    "San Francisco": {
        "plastic bottle": "Recycle",
        "glass bottle": "Recycle",
        "greasy cardboard": "Trash",
    },
    "Chicago": {
        "plastic bottle": "Recycle",
        "glass bottle": "Recycle",
        "greasy cardboard": "Trash",
    },
}


def detect_material(packaging_text: str) -> str:
    """Extract simplified material type from packaging text."""
    text = packaging_text.lower()
    if "plastic bottle" in text:
        return "plastic bottle"
    if "glass bottle" in text:
        return "glass bottle"
    if "greasy cardboard" in text:
        return "greasy cardboard"
    return "unknown"


def get_disposal_instruction(city: str, packaging_text: str) -> Dict[str, str]:
    """Return disposal decision payload for UI and storage."""
    material = detect_material(packaging_text or "")
    city_rules = CITY_DISPOSAL_RULES.get(city, {})
    disposal_type = city_rules.get(material, "Check Local Guidelines")

    if disposal_type == "Recycle":
        icon = "♻"
    elif disposal_type == "Trash":
        icon = "🗑"
    else:
        icon = "ℹ"

    detail = (
        f"{material.title()} -> {disposal_type}"
        if material != "unknown"
        else "Material unclear. Follow local sorting guidelines."
    )

    return {
        "city": city,
        "material": material,
        "disposal_type": disposal_type,
        "icon": icon,
        "detail": detail,
    }

