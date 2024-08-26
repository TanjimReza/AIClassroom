from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .forms import AdminUserCreationForm, StudentUserCreationForm, TeacherUserCreationForm, UsersCreationForm
from .models import AdminProfile, StudentProfile, TeacherProfile, Users, Classroom


class AdminProfileInline(admin.StackedInline):
    model = AdminProfile
    can_delete = False
    verbose_name_plural = "Admin Profile"


class TeacherProfileInline(admin.StackedInline):
    model = TeacherProfile
    can_delete = False
    verbose_name_plural = "Teacher Profile"
    autocomplete_fields = ["assigned_classroom"]


class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name_plural = "Student Profile"
    autocomplete_fields = ["enrolled_classroom"]


class CustomUserAdmin(UserAdmin):
    add_form = UsersCreationForm
    form = UsersCreationForm
    model = Users
    list_display = ["email", "first_name", "last_name", "user_type", "is_active", "is_staff", "is_superuser"]
    list_filter = ["user_type", "is_active", "is_staff", "is_superuser"]
    search_fields = ["email", "first_name", "last_name", "user_type"]
    ordering = ["email"]  # Replace 'username' with 'email'

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name")}),
        ("Permissions", {"fields": ("user_type", "is_staff", "is_active", "is_superuser")}),
        ("Important Dates", {"fields": ("date_last_login",)}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "first_name", "last_name", "user_type", "is_staff", "is_active", "is_superuser"),
            },
        ),
    )

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        inline_instances = []
        if obj.user_type == "teacher":
            inline_instances.append(TeacherProfileInline(self.model, self.admin_site))
        elif obj.user_type == "general_admin":
            inline_instances.append(AdminProfileInline(self.model, self.admin_site))
        elif obj.user_type == "student":
            inline_instances.append(StudentProfileInline(self.model, self.admin_site))
        return inline_instances


admin.site.register(Users, CustomUserAdmin)


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "role_description"]
    search_fields = ["user__email", "role_description"]
    autocomplete_fields = ["user"]


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "subject_specialization", "assigned_classroom"]
    search_fields = ["user__email", "subject_specialization", "assigned_classroom__name"]
    list_filter = ["subject_specialization"]
    autocomplete_fields = ["user", "assigned_classroom"]


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "enrolled_classroom"]
    search_fields = ["user__email", "enrolled_classroom__name"]
    list_filter = ["enrolled_classroom"]
    autocomplete_fields = ["user", "enrolled_classroom"]


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "created_by", "is_active", "capacity", "created_at", "updated_at"]
    search_fields = ["name", "slug", "created_by__email"]
    list_filter = ["is_active", "created_at"]
    ordering = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ["created_by"]
