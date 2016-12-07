from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from import_export import resources, fields
import tablib

from activities.models import ExtraNeed
from backend.templatetags.switzerland import phone
from .models import Registration


class ExtraNeedField(fields.Field):
    def __init__(self, *args, **kwargs):
        self.extra_need = kwargs.pop('extra_need')
        kwargs['column_name'] = kwargs.pop('column_name', self.extra_need.question_label)
        super(ExtraNeedField, self).__init__(*args, **kwargs)

    def get_value(self, obj):
        value = None
        for question in obj.extra_infos.all():
            if question.key == self.extra_need:
                value = question.value
        return value


class RegistrationResource(resources.ModelResource):
    activity = fields.Field(attribute='course__activity__name', column_name=_("Activity"))
    course = fields.Field(attribute='course__number', column_name=_("Course"))
    price = fields.Field(attribute='course__price', column_name=_("Price"))
    first_name = fields.Field(attribute='child__first_name', column_name=_("First name"))
    last_name = fields.Field(attribute='child__last_name', column_name=_("Last name"))
    child_id = fields.Field(attribute='child', column_name=_("Child identifier"))
    birth_date = fields.Field(attribute='child', column_name=_("Birth date"))
    school_year = fields.Field(attribute='child__school_year__year', column_name=_("School year"))
    school = fields.Field(attribute='child__school__name', column_name=_("School"))
    parent_first_name= fields.Field(attribute='child__family__first_name', column_name=_("Parent's first name"))
    parent_last_name= fields.Field(attribute='child__family__last_name', column_name=_("Parent's last name"))
    parent_email= fields.Field(attribute='child__family__email', column_name=_("Email"))
    parent_address= fields.Field(attribute='child__family__address', column_name=_("Address"))
    parent_zipcode= fields.Field(attribute='child__family__zipcode', column_name=_("NPA"))
    parent_city= fields.Field(attribute='child__family__city', column_name=_("City"))
    parent_country= fields.Field(attribute='child__family__country', column_name=_("Country"))


    emergency_number = fields.Field(attribute='child', column_name=_("Emergency number"))


    def __init__(self, *args, **kwargs):
        self.course = kwargs.pop('course', None)
        super(RegistrationResource, self).__init__(*args, **kwargs)
        if self.course:
            queryset = ExtraNeed.objects.filter(courses__in=[self.course])
        else:
            queryset = ExtraNeed.objects.all()
        for extra in queryset:
            field = ExtraNeedField(extra_need=extra)
            self.fields['extra_{}'.format(extra.id)] = field

    def dehydrate_child_id(self, obj):
        if settings.KEPCHUP_IMPORT_CHILDREN:
            return obj.child.id_lagapeo or ''
        return obj.child.id

    def dehydrate_emergency_number(self, obj):
        value = obj.child.emergency_number
        return phone(value)

    def dehydrate_birth_date(self, obj):
        return obj.child.birth_date.isoformat()

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
        queryset = Registration.objects.select_related('course', 'child', 'child__family')\
                                       .prefetch_related('course__activity', 'extra_infos', 'child__school',
                                                         'child__school_year')
        if self.course:
            queryset = queryset.filter(course=self.course)
        return queryset

    class Meta:
        model = Registration
        fields = ('id', 'activity', 'course', 'price',
                  'first_name', 'last_name', 'child_id', 'birth_date', 'emergency_number')
        export_order = ('id', 'activity', 'course', 'price',
                        'first_name', 'last_name', 'child_id', 'birth_date', 'emergency_number')
