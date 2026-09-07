from django.contrib import admin
from django.utils.translation import gettext_lazy as _


class SportfacAdminMixin:
    timestamp_fields = ("created", "modified")

    def get_timestamp_fields(self):
        model_fields = {field.name for field in self.model._meta.get_fields()}
        return tuple(field for field in self.timestamp_fields if field in model_fields)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        for field in self.get_timestamp_fields():
            if field not in readonly_fields:
                readonly_fields.append(field)
        return tuple(readonly_fields)

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj is None:
            return fieldsets

        timestamp_fields = self.get_timestamp_fields()
        if not timestamp_fields:
            return fieldsets

        displayed_fields = set()
        for _junk, options in fieldsets:
            displayed_fields.update(self._flatten_fieldsets_fields(options.get("fields", ())))

        missing_fields = tuple(field for field in timestamp_fields if field not in displayed_fields)
        if not missing_fields:
            return fieldsets

        return tuple(fieldsets) + ((_("Timestamps"), {"fields": missing_fields}),)

    def _flatten_fieldsets_fields(self, fields):
        for field in fields:
            if isinstance(field, (list, tuple)):
                yield from self._flatten_fieldsets_fields(field)
            else:
                yield field

    def log_addition(self, *args, **kwargs):
        pass

    def log_change(self, *args, **kwargs):
        pass

    def log_deletion(self, *args, **kwargs):
        pass


class SportfacModelAdmin(SportfacAdminMixin, admin.ModelAdmin):
    def log_addition(self, *args, **kwargs):
        pass

    def log_change(self, *args, **kwargs):
        pass

    def log_deletion(self, *args, **kwargs):
        pass
