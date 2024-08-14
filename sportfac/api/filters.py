from django.utils.dateparse import parse_datetime
from django.utils.timezone import now

from rest_framework_datatables.filters import DatatablesFilterBackend


def cleanup_value(model_class, accessor, values):
    if "__" in accessor:
        parent_field_name, child_field_name = accessor.split("__")[0], "__".join(accessor.split("__")[1:])
        # noinspection PyProtectedMember
        query_filter, cleaned_values = cleanup_value(
            model_class._meta.get_field(parent_field_name).related_model, child_field_name, values
        )
        return f"{parent_field_name}__{query_filter}", cleaned_values

    # noinspection PyProtectedMember
    model_field = model_class._meta.get_field(accessor)
    if hasattr(model_field, "choices") and model_field.choices:
        # for some reason, even if datatables is provided with labels and values, it stills sends
        # label rather than value. Which is a pain for multi choices. Here we revert the choices to find
        # key from value.
        # And we pray for the i18n questions.
        # noinspection PyProtectedMember
        values_mapper = {v: k for k, v in model_field.choices._display_map.items()}
        return f"{accessor}__in", [values_mapper.get(value) for value in values]
    if model_field.get_internal_type() == "BooleanField":
        return f"{accessor}__in", [bool(int(value)) for value in values]
    if model_field.get_internal_type() == "DateTimeField":
        thedate = parse_datetime(values[0])
        if thedate > now():
            return f"{accessor}__isnull", True
        return f"{accessor}__gte", thedate
    return accessor, values


def parse_phone_numbers(search_value):
    if search_value.startswith("00"):
        return "+" + search_value[2:]
    if search_value.startswith("0") and search_value.isdigit():
        return "+41" + search_value[1:].lstrip("0")
    return search_value


class DatatablesFilterandPanesBackend(DatatablesFilterBackend):
    def filter_queryset(self, request, queryset, view):
        mutable_params = request.query_params.copy()
        if "search[value]" in mutable_params:
            mutable_params["search[value]"] = parse_phone_numbers(mutable_params["search[value]"])

        # This is a hack to make the query_params mutable, and intercept the changes before the lib uses it.
        request._request.GET = mutable_params  # noqa

        queryset = super().filter_queryset(request, queryset, view)
        getter = request.query_params.get
        fields = self.get_fields(getter)
        for field in fields:
            pane_name = field["data"]
            pane_data_accessor = field["name"][0]
            count = 0
            values = []
            while True:
                pane_value = getter(f"searchPanes[{pane_name}][{count}]")
                if not pane_value:
                    break
                values.append(pane_value)
                count += 1
            if values:
                accessor, values = cleanup_value(queryset.model, pane_data_accessor, values)
                queryset = queryset.filter(**{accessor: values})
        filtered_count = queryset.count()
        view._datatables_filtered_count = filtered_count
        return queryset
