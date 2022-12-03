# -*- coding: utf-8 -*-
from __future__ import absolute_import

import datetime

from django.utils.dateparse import parse_datetime
from django.utils.timezone import now

from rest_framework_datatables.filters import DatatablesFilterBackend


def cleanup_value(model_class, accessor, values):
    if "__" in accessor:
        parent_field_name, child_field_name = accessor.split("__")[0], "__".join(
            accessor.split("__")[1:]
        )
        # noinspection PyProtectedMember
        query_filter, cleaned_values = cleanup_value(
            model_class._meta.get_field(parent_field_name).related_model, child_field_name, values
        )
        return "{}__{}".format(parent_field_name, query_filter), cleaned_values

    # noinspection PyProtectedMember
    model_field = model_class._meta.get_field(accessor)
    if hasattr(model_field, "choices") and model_field.choices:
        # for some reason, even if datatables is provided with labels and values, it stills sends
        # label rather than value. Which is a pain for multi choices. Here we revert the choices to find
        # key from value.
        # And we pray for the i18n questions.
        # noinspection PyProtectedMember
        values_mapper = {v: k for k, v in model_field.choices._display_map.items()}
        return "{}__in".format(accessor), [values_mapper.get(value) for value in values]
    elif model_field.get_internal_type() == "BooleanField":
        return "{}__in".format(accessor), [bool(int(value)) for value in values]
    elif model_field.get_internal_type() == "DateTimeField":
        thedate = parse_datetime(values[0])
        if thedate > now():
            return "{}__isnull".format(accessor), True
        return "{}__gte".format(accessor), thedate
    return accessor, values


class DatatablesFilterandPanesBackend(DatatablesFilterBackend):
    def filter_queryset(self, request, queryset, view):
        queryset = super(DatatablesFilterandPanesBackend, self).filter_queryset(
            request, queryset, view
        )
        if request.method == "POST":
            request_data = request.data
        else:
            request_data = request.query_params
        getter = request_data.get
        fields = self.get_fields(getter)
        for field in fields:
            pane_name = field["data"]
            pane_data_accessor = field["name"][0]
            count = 0
            values = []
            while True:
                pane_value = getter("searchPanes[{}][{}]".format(pane_name, count))
                if not pane_value:
                    break
                values.append(pane_value)
                count += 1
            if values:
                accessor, values = cleanup_value(queryset.model, pane_data_accessor, values)
                queryset = queryset.filter(**{accessor: values})
        filtered_count = queryset.count()
        setattr(view, "_datatables_filtered_count", filtered_count)
        return queryset
