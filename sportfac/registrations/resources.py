from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from import_export import resources, fields
import tablib

from activities.models import ExtraNeed
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
    child = fields.Field(attribute='child', column_name=_("Child"))
    child_id = fields.Field(attribute='child', column_name=_("Child identifier"))
    birth_date = fields.Field(attribute='child', column_name=_("Birth date"))
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

    def dehydrate_child(self, obj):
        return obj.child.full_name

    def dehydrate_child_id(self, obj):
        if settings.KEPCHUP_IMPORT_CHILDREN:
            return obj.child.id_lagapeo or ''
        return obj.child.id

    def dehydrate_emergency_number(self, obj):
        return obj.child.emergency_number

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
        queryset = Registration.objects.select_related('course', 'child')\
                                       .prefetch_related('course__activity', 'extra_infos')
        if self.course:
            queryset = queryset.filter(course=self.course)
        return queryset

    class Meta:
        model = Registration
        fields = ('id', 'activity', 'course', 'child', 'child_id', 'birth_date', 'emergency_number')
        export_order = ('id', 'activity', 'course', 'child', 'child_id', 'birth_date', 'emergency_number')
