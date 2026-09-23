"""Human-readable SSF levels; stored codes remain unchanged."""

import re

from django.utils.translation import gettext as _


def level_description(code):
    match = re.fullmatch(r"([AS])\s*([1-7])\s*([ABC])", (code or "").strip())
    if not match:
        return code or ""
    discipline, number, assessment = match.groups()
    sport = {"A": _("Alpine skiing"), "S": _("Snowboarding")}[discipline]
    descriptions = {
        "A": _("%(sport)s, level %(number)s, needs improvement"),
        "B": _("%(sport)s, level %(number)s, good"),
        "C": _("%(sport)s, level %(number)s, confirmed"),
    }
    return descriptions[assessment] % {"sport": sport, "number": number}


def level_menu_label(code):
    description = level_description(code)
    return f"{code} — {description}" if description != code else code


def diploma_evaluation(activity, code):
    if not code:
        return ""
    description = level_description(code)
    return description if description != code else f"{activity} — {code}"
