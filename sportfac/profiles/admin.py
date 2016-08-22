# -*- coding: utf-8 -*-
from django import forms
from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.utils.translation import ugettext_lazy as _

from .models import FamilyUser, School, SchoolYear
from registrations.models import Child


class FamilyCreationForm(forms.ModelForm):
    """A form for creating new users. Includes all the required
    fields, plus a repeated password."""
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = FamilyUser
        fields = ('email', 'first_name', 'last_name', 
                  'address', 'zipcode', 'city', 'country', 
                  'private_phone', 'private_phone2', 
                  'birth_date', 'iban', 'ahv')

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
        fields = ('email', 'is_staff', 'is_superuser', 'groups',
                  'first_name', 'last_name', 
                  'address', 'zipcode', 'city', 'country', 
                  'private_phone', 'private_phone2', 'private_phone3',
                  'birth_date', 'iban', 'ahv')


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

    list_display = ('email', 'first_name', 'last_name', 'children_names', 'last_login', 'date_joined')
    
    change_list_template = "admin/change_list_filter_sidebar.html"
    change_list_filter_template = "admin/filter_listing.html"

    
    fieldsets = (
        (None, {'fields': ('email', 'password', 'is_staff', 'is_superuser', 'groups')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 
                                      'address', 'zipcode', 'city', 'country', 
                                      'private_phone', 'private_phone2', 'private_phone3',
                                      'birth_date', 'iban', 'ahv')}),
        
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2')}
        ),
        ('Personal info', {'fields': ('first_name', 'last_name', 
                                      'address', 'zipcode', 'city', 'country', 
                                      'private_phone', 'private_phone2',
                                      'birth_date', 'iban', 'ahv')}),
    )
    search_fields = ('email', 'last_name', 'first_name',)
    ordering = ('last_name', 'first_name')
    #filter_horizontal = ()
    inlines = [ChildInline]
    
    def get_queryset(self, request):
        qs = super(FamilyAdmin, self).get_queryset(request)
        #return qs 19
        return qs.prefetch_related('children')
    
    

admin.site.register(FamilyUser, FamilyAdmin)
admin.site.register(SchoolYear)
admin.site.register(School)
