from django.contrib import admin

from .models import Teacher




class TeacherAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'years_label', 'number')
    list_filter = ('years',) 
    filter_horizontal=('years',)
    
    #change_list_template = "admin/change_list_filter_sidebar.html"
    change_list_filter_template = "admin/filter_listing.html"

admin.site.register(Teacher, TeacherAdmin)

