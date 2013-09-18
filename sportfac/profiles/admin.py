#!/usr/bin/python
# -*- coding: utf-8 -*-

from django import forms
from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponse

import autocomplete_light

from sportfac.utils import UnicodeWriter
from .models import FamilyUser, Child, Teacher, Registration



class FamilyCreationForm(forms.ModelForm):
    """A form for creating new users. Includes all the required
    fields, plus a repeated password."""
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = FamilyUser
        fields = ('email', 'first_name', 'last_name', 
                  'address', 'zipcode', 'city', 'country', 
                  'private_phone', 'private_phone2')

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super(FamilyCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class FamilyChangeForm(forms.ModelForm):
    """A form for updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    password hash display field.
    """
    password = ReadOnlyPasswordHashField(help_text= _("Raw passwords are not stored, so there is no way to see "
                    "this user's password, but you can change the password "
                    "using <a href=\"password/\">this form</a>."))

    class Meta:
        model = FamilyUser
        fields = ('email', 'is_staff', 'finished_registration', 'paid',
                  'first_name', 'last_name', 
                  'address', 'zipcode', 'city', 'country', 
                  'private_phone', 'private_phone2', 'private_phone3')


    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial["password"]

class ChildInline(admin.StackedInline):
    model = Child
    extra = 1
    verbose_name = _("child")
    verbose_name_plural = _("children")
    
class FamilyAdmin(UserAdmin):
    # The forms to add and change user instances
    form = FamilyChangeForm
    add_form = FamilyCreationForm
    readonly_fields = ('total',)

    list_display = ('email', 'first_name', 'last_name', 'children_names', 'billing_identifier', 'finished_registration', 'total', 'paid')
    
    list_filter = ('paid', 'finished_registration')
    change_list_template = "admin/change_list_filter_sidebar.html"
    change_list_filter_template = "admin/filter_listing.html"

    
    fieldsets = (
        (None, {'fields': ('email', 'password', 'is_staff', 'finished_registration', 'total', 'paid')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 
                                      'address', 'zipcode', 'city', 'country', 
                                      'private_phone', 'private_phone2', 'private_phone3')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2')}
        ),
        ('Personal info', {'fields': ('first_name', 'last_name', 
                                      'address', 'zipcode', 'city', 'country', 
                                      'private_phone', 'private_phone2')}),
    )
    search_fields = ('email', 'last_name', 'first_name', 'billing_identifier')
    ordering = ('last_name', 'first_name')
    #filter_horizontal = ()
    inlines = [ChildInline]
    
    def queryset(self, request):
        qs = super(FamilyAdmin, self).queryset(request)
        #return qs 19
        return qs.prefetch_related('children')
    
    

admin.site.register(FamilyUser, FamilyAdmin)
admin.site.unregister(Group)

class TeacherAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'years_label')
    list_filter = ('years',) 
    filter_horizontal=('years',)
    
    change_list_template = "admin/change_list_filter_sidebar.html"
    change_list_filter_template = "admin/filter_listing.html"

admin.site.register(Teacher, TeacherAdmin)

class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'validated')
    
    list_filter = ('validated', 'course__activity__name')
    
    search_fields = ('child__first_name', 'child__last_name', 
                     'course__activity__number', 'course__activity__name',
                     'course__number',
                     )
    change_list_template = "admin/change_list_filter_sidebar.html"
    change_list_filter_template = "admin/filter_listing.html"
    
    form = autocomplete_light.modelform_factory(Registration)
    actions = ['delete_model', 'export']
    
    
    def queryset(self, request):
        qs = super(RegistrationAdmin, self).queryset(request)
        #return qs 19
        return qs.select_related('course', 'course__activity', 'child')
    
    def save_model(self, request, obj, form, change):
        obj.save()
        obj.child.family.update_total()
        obj.child.family.save()
    
    def get_actions(self, request):
        actions = super(RegistrationAdmin, self).get_actions(request)
        del actions['delete_selected']
        return actions
    
    def delete_model(self, request, queryset):
        for registration in queryset.all():
            family = registration.child.family
            registration.delete()
            family.update_total()
            family.save()
    delete_model.short_description = _('Delete selected registration')
    
    def export(self, request, queryset):
        response = HttpResponse(mimetype='text/csv')
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
