from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from .models import Session, Absence


class SessionAdmin(admin.ModelAdmin):
    list_display = ('course_short', 'date', 'instructor_short', 'presentees', 'absentees_nb')
    list_filter = ('date', )
    date_hierarchy = 'date'
    search_fields = ('course__name', 'course__activity__name', 'course__number',
                     'instructor__first_name', 'instructor__last_name')

    def course_short(self, obj):
        return obj.course.short_name
    course_short.short_description = _("course")

    def instructor_short(self, obj):
        if obj.instructor:
            return obj.instructor.full_name
        return
    instructor_short.short_description = _("Instructor")

    def presentees(self, obj):
        return obj.presentees_nb()
    presentees.short_description = _("Presentees")

    def absentees_nb(self, obj):
        return len(obj.absentees())
    absentees_nb.short_description = _("Absentees")

    def get_queryset(self, request):
        return Session.objects.prefetch_related('absences')\
                              .select_related('course', 'course__activity', 'instructor')\
                              .order_by('-date')


admin.site.register(Session, SessionAdmin)
admin.site.register(Absence)
