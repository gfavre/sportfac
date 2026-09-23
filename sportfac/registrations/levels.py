"""Human-readable SSF levels; stored codes remain unchanged."""

import re


def level_description(code):
    match = re.fullmatch(r"([AS])\s*([1-7])\s*([ABC])", (code or "").strip())
    if not match:
        return code or ""
    discipline, number, assessment = match.groups()
    sport = {"A": "Ski alpin", "S": "Snowboard"}[discipline]
    label = {"A": "à améliorer", "B": "bien", "C": "confirmé"}[assessment]
    return f"{sport}, niveau {number}, {label}"


def level_menu_label(code):
    description = level_description(code)
    return f"{code} — {description}" if description != code else code


def diploma_evaluation(activity, code):
    if not code:
        return ""
    description = level_description(code)
    return description if description != code else f"{activity} — {code}"
