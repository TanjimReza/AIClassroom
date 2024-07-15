from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Classroom, ClassroomAdmin, Student, Users


class CustomUserAdmin(UserAdmin):
    model = Users
    
    list_display = ('email', 'user_type', 'first_name',
                    'last_name', 'is_staff', 'is_active', 'is_superuser')
    list_filter = ('email', 'user_type', 'is_staff',
                   'is_active', 'is_superuser')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {
         'fields': ('first_name', 'last_name', 'user_type')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser')}),
    )

    search_fields = ('email', 'first_name', 'last_name')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {
         'fields': ('first_name', 'last_name', 'user_type')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'user_type'),
        }),
    )
    ordering = ("email",)

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        inline_instances = []
        if obj.user_type == "student":
            inline_instances.append(
                StudentProfileInline(self.model, self.admin_site)
            )

        if obj.user_type == "classroom_admin":
            inline_instances.append(
                ClassroomAdminInline(self.model, self.admin_site)
            )
        return super().get_inline_instances(request, obj)


class StudentProfileInline(admin.StackedInline):
    model = Student
    can_delete = False
    verbose_name_plural = 'Students'


class ClassroomAdminInline(admin.ModelAdmin):
    # autocomplete_fields = ['classroom_id']
    list_display = ('classroom_id', 'name', 'slug',
                    'description', 'created_at', 'updated_at')


admin.site.register(Classroom)
admin.site.register(ClassroomAdmin)
admin.site.register(Users, CustomUserAdmin)
