from django.conf import settings
from django.utils.translation import gettext_lazy as _

import tablib
from activities.models import ExtraNeed
from backend.templatetags.switzerland import phone
from import_export import fields, resources, widgets

from .models import Bill, ChildActivityLevel, Registration


class ExtraNeedField(fields.Field):
    def __init__(self, *args, **kwargs):
        self.extra_need = kwargs.pop("extra_need")
        kwargs["column_name"] = kwargs.pop("column_name", self.extra_need.question_label)
        super().__init__(*args, **kwargs)

    def get_value(self, obj):
        value = None
        for question in obj.extra_infos.all():
            if question.key == self.extra_need:
                value = question.value
        return value


class RegistrationResource(resources.ModelResource):
    activity = fields.Field(attribute="course__activity__name", column_name=_("Activity"))
    course = fields.Field(attribute="course__number", column_name=_("Course"))
    price = fields.Field(attribute="course__price", column_name=_("Price"))
    first_name = fields.Field(attribute="child__first_name", column_name=_("First name"))
    last_name = fields.Field(attribute="child__last_name", column_name=_("Last name"))
    child_id = fields.Field(attribute="child", column_name=_("Child identifier"))
    invoice_identifier = fields.Field(attribute="bill__billing_identifier", column_name=_("Billing identifier"))
    bib_number = fields.Field(attribute="child__bib_number", column_name=_("Bib number"))
    transport = fields.Field(attribute="transport__name", column_name=_("Transport"))
    birth_date = fields.Field(attribute="child", column_name=_("Birth date"))
    school_year = fields.Field(attribute="child__school_year__year", column_name=_("School year"))
    school_name = fields.Field(attribute="child", column_name=_("School"))
    parent_first_name = fields.Field(attribute="child__family__first_name", column_name=_("Parent's first name"))
    parent_last_name = fields.Field(attribute="child__family__last_name", column_name=_("Parent's last name"))
    parent_email = fields.Field(attribute="child__family__email", column_name=_("Email"))
    parent_address = fields.Field(attribute="child__family__address", column_name=_("Address"))
    parent_zipcode = fields.Field(attribute="child__family__zipcode", column_name=_("NPA"))
    parent_city = fields.Field(attribute="child__family__city", column_name=_("City"))
    parent_country = fields.Field(attribute="child__family__country", column_name=_("Country"))
    emergency_number = fields.Field(attribute="child", column_name=_("Emergency number"))
    before_level = fields.Field(attribute="child", column_name=_("Level -1"))
    after_level = fields.Field(attribute="child", column_name=_("Level 0"))
    paid = fields.Field(attribute="paid", column_name=_("Paid"), widget=widgets.BooleanWidget())

    class Meta:
        model = Registration
        fields = (
            "id",
            "activity",
            "course",
            "price",
            "paid",
            "invoice_identifier",
            "bib_number",
            "transport",
            "first_name",
            "last_name",
            "child_id",
            "birth_date",
            "school_year",
            "school_name",
            "emergency_number",
            "parent_first_name",
            "parent_last_name",
            "parent_email",
            "parent_address",
            "parent_zipcode",
            "parent_city",
            "parent_country",
            "before_level",
            "after_level",
        )
        export_order = fields

    def __init__(self, *args, **kwargs):
        self.course = kwargs.pop("course", None)
        super().__init__(*args, **kwargs)
        if self.course:
            queryset = ExtraNeed.objects.filter(courses__in=[self.course])
        else:
            queryset = ExtraNeed.objects.all()
        for extra in queryset:
            field = ExtraNeedField(extra_need=extra)
            self.fields[f"extra_{extra.id}"] = field
        if not settings.KEPCHUP_CHILD_SCHOOL and "school_name" in self.fields:
            # Resource objects are cached by the import-export library. Therefore we could
            # try to remove an already removed field :(
            del self.fields["school_name"]
        if not settings.KEPCHUP_BIB_NUMBERS and "bib_number" in self.fields:
            del self.fields["bib_number"]
        if not settings.KEPCHUP_REGISTRATION_LEVELS and "before_level" in self.fields:
            del self.fields["before_level"]
        if not settings.KEPCHUP_REGISTRATION_LEVELS and "after_level" in self.fields:
            del self.fields["after_level"]
        if not settings.KEPCHUP_DISPLAY_CAR_NUMBER and "transport" in self.fields:
            del self.fields["transport"]
        if settings.KEPCHUP_NO_PAYMENT:
            del self.fields["paid"]
            del self.fields["invoice_identifier"]

    def dehydrate_child_id(self, obj):
        if settings.KEPCHUP_IMPORT_CHILDREN:
            return obj.child.id_lagapeo or ""
        return obj.child.id

    def dehydrate_school_name(self, obj):
        if obj.child.school:
            return obj.child.school.name
        return obj.child.other_school

    def dehydrate_emergency_number(self, obj):
        value = obj.child.emergency_number
        return phone(value)

    def dehydrate_birth_date(self, obj):
        return obj.child.birth_date.strftime("%d.%m.%Y")

    def montreux_prepend(self, obj):
        activity = obj.course.activity
        if activity.number.startswith("200"):
            return "A "
        if activity.number.startswith("270"):
            return "S "
        if obj.extra_infos.exists():
            extra = obj.extra_infos.filter(key__question_label__startswith="Snowboard ou ski").last()
            if not extra:
                return ""
            if extra.value.lower() == "ski":
                return "A "
            return "S "
        return ""

    def dehydrate_before_level(self, obj):
        activity = obj.course.activity

        try:
            level = obj.child.levels.get(activity=activity)
            return level.before_level and self.montreux_prepend(obj) + level.before_level or ""
        except ChildActivityLevel.DoesNotExist:
            return ""

    def dehydrate_after_level(self, obj):
        activity = obj.course.activity
        try:
            level = obj.child.levels.get(activity=activity)
            return level.after_level and self.montreux_prepend(obj) + level.after_level or ""
        except ChildActivityLevel.DoesNotExist:
            return ""

    def export(self, queryset=None, *args, **kwargs):
        """
        Exports a resource.
        """

        self.before_export(queryset, *args, **kwargs)

        if queryset is None:
            queryset = self.get_queryset()
        headers = self.get_export_headers()
        data = tablib.Dataset(headers=headers)

        for obj in queryset:
            data.append(self.export_resource(obj))

        self.after_export(queryset, data, *args, **kwargs)

        return data

    def get_queryset(self):
        queryset = Registration.objects.select_related(
            "course", "child", "child__family", "transport"
        ).prefetch_related(
            "course__activity",
            "extra_infos",
            "child__school",
            "child__school_year",
            "child__levels",
        )
        if self.course:
            queryset = queryset.filter(course=self.course)
        return queryset  # noqa R504

    def get_export_order(self):
        order = tuple(self._meta.export_order or ())
        removable_fields = []
        if not settings.KEPCHUP_CHILD_SCHOOL:
            removable_fields.append("school_name")
        if not settings.KEPCHUP_REGISTRATION_LEVELS:
            removable_fields.append("before_level")
            removable_fields.append("after_level")
        if not settings.KEPCHUP_BIB_NUMBERS:
            removable_fields.append("bib_number")
        if not settings.KEPCHUP_DISPLAY_CAR_NUMBER:
            removable_fields.append("transport")
        if settings.KEPCHUP_NO_PAYMENT:
            removable_fields.append("paid")
            removable_fields.append("invoice_identifier")
        order = tuple([field for field in order if field not in removable_fields])
        return order + tuple(k for k in self.fields.keys() if k not in order)


class BillResource(resources.ModelResource):
    billing_identifier = fields.Field(
        attribute="billing_identifier", column_name=_("Billing identifier"), widget=widgets.CharWidget()
    )
    amount = fields.Field(attribute="total", column_name=_("Amount"), widget=widgets.DecimalWidget())
    due_date = fields.Field(
        attribute="due_date", column_name=_("Due date"), widget=widgets.DateWidget(format="%d.%m.%Y")
    )
    parent = fields.Field(attribute="family", column_name=_("Parent"))
    children = fields.Field(attribute="registrations", column_name=_("Children"))
    paid = fields.Field(attribute="is_paid", column_name=_("Paid"), widget=widgets.BooleanWidget())

    class Meta:
        model = Bill
        fields = ("billing_identifier", "amount", "due_date", "paid", "parent", "children")
        export_order = fields

    def dehydrate_children(self, obj):
        return ", ".join([registration.child.full_name for registration in obj.registrations.all()])

    def dehydrate_parent(self, obj):
        return obj.family.full_name

    def export(self, queryset=None, *args, **kwargs):
        """
        Exports a resource.
        """

        self.before_export(queryset, *args, **kwargs)

        if queryset is None:
            queryset = self.get_queryset()
        headers = self.get_export_headers()
        data = tablib.Dataset(headers=headers)
        for obj in queryset:
            data.append(self.export_resource(obj))

        self.after_export(queryset, data, *args, **kwargs)

        return data
