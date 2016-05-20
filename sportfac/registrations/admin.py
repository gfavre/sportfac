# -*- coding: utf-8 -*-
from django.contrib import admin
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _

from .models import Registration
from sportfac.utils import UnicodeWriter


class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'status')
    list_filter = ('status', 'course__activity__name')
    search_fields = (
        'child__first_name', 'child__last_name', 'course__activity__number',
        'course__activity__name', 'course__number',
    )
    change_list_template = "admin/change_list_filter_sidebar.html"
    change_list_filter_template = "admin/filter_listing.html"

    actions = ['delete_model', 'export']

    def get_queryset(self, request):
        #qs = super(RegistrationAdmin, self).get_queryset(request)
        #return qs 19
        qs = self.model._default_manager.all_with_deleted()
        return qs.select_related('course', 'course__activity', 'child')
    
    def get_actions(self, request):
        actions = super(RegistrationAdmin, self).get_actions(request)
        del actions['delete_selected']
        return actions

    def export(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=inscriptions.csv'
        writer = UnicodeWriter(response)
        field_names = (u'Inscription n°', 
                       u'Cours n°',
                       u'Activité',
                       u'Activité n°',
                       u'Responsable',
                       u'Prénom enfant',
                       u'Nom enfant',
                       u'Sexe',
                       u'Date de naissance',
                       u'Année scolaire',
                       u'Pointure',
                       u'Parent',
                       u'Adresse',
                       u'NPA',
                       u'Commune',
                       u'email',
                       u'Tél maison',
                       u'Tél mobile #1',
                       u'Tél mobile #2',
                       u'Payé',
                       u'Enseignant',
                       u'Enseignant n°',
                       )
        writer.writerow(field_names)
        for registration in queryset.select_related('course__responsible', 'course__activity', 
                                                    'child__family', 'child__teacher').all():
            if registration.extra_infos.count():
                size = registration.extra_infos.all()[0].value
            else:
                size  = ''
            writer.writerow((str(registration.id), 
                             str(registration.course.number),
                             registration.course.activity.name,
                             str(registration.course.activity.number),
                             unicode(registration.course.responsible),
                             registration.child.first_name,
                             registration.child.last_name,
                             registration.child.sex,  
                             registration.child.birth_date.strftime('%d.%m.%Y'),
                             str(registration.child.school_year.year),
                             size,
                             registration.child.family.get_full_name(),
                             registration.child.family.address,
                             str(registration.child.family.zipcode),
                             registration.child.family.city,
                             registration.child.family.email,
                             registration.child.family.private_phone,
                             registration.child.family.private_phone2,
                             registration.child.family.private_phone3,
                             str(int(registration.child.family.paid)),
                             registration.child.teacher.get_full_name(),
                             str(registration.child.teacher.number),
                             ))
        #wrapped = ("<html><body>", response.content, "</body></html>")
        #return HttpResponse(wrapped)
        return response
    export.short_description = _('Export selected registrations')

admin.site.register(Registration, RegistrationAdmin)
