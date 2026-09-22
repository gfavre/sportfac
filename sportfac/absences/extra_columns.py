import json

from django import forms


def parse_extra_columns(value):
    columns = json.loads(value or "[]")
    # Preserve preferences saved before the structured editor was introduced.
    if isinstance(columns, dict):
        columns = [{"label": label, "question": question, "values": {}} for label, question in columns.items()]
    if not isinstance(columns, list):
        raise ValueError("La configuration doit être une liste de colonnes.")
    for column in columns:
        if not isinstance(column, dict):
            raise ValueError("Colonne invalide.")
        for key in ("label", "question"):
            if not isinstance(column.get(key), str) or not column[key].strip():
                raise ValueError("Choisissez une question et un libellé pour chaque colonne.")
        values = column.get("values", {})
        if not isinstance(values, dict) or any(not isinstance(value, str) for value in values.values()):
            raise ValueError("Les correspondances doivent associer des valeurs textuelles.")
    return columns


class AttendanceExtraColumnsWidget(forms.Textarea):
    template_name = "absences/widgets/extra-columns.html"

    class Media:
        css = {"all": ("css/attendance-extra-columns.css",)}
        js = ("js/attendance-extra-columns.js",)

    def get_context(self, name, value, attrs):
        from activities.models import ExtraNeed

        context = super().get_context(name, value, attrs)
        # Resolve questions at render time, inside the selected school-year schema.
        context["questions"] = (
            ExtraNeed.objects.order_by("question_label").values_list("question_label", flat=True).distinct()
        )
        return context


class AttendanceExtraColumnsField(forms.CharField):
    def validate(self, value):
        super().validate(value)
        try:
            parse_extra_columns(value)
        except (ValueError, TypeError) as exc:
            raise forms.ValidationError(str(exc)) from exc
