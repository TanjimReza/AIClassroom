from .models import Classroom, CourseMaterial, Lesson
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import AdminUserCreationForm, StudentUserCreationForm, TeacherUserCreationForm, UsersCreationForm
from .models import AdminProfile, Classroom, CourseMaterial, Invitation, StudentProfile, TeacherProfile, Users, Lesson, Exam, ExamSession, WebcamCapture, FocusLossLog, ExamAnswer, ExamSubmission, Question
from .models import Question

admin.site.register(Question)


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
    list_display = [
        "email",
        "first_name",
        "last_name",
        "user_type",
        "is_active",
        "is_staff",
        "is_superuser",
        "email_verified",
    ]
    list_filter = [
        "user_type",
        "is_active",
        "is_staff",
        "is_superuser",
        "email_verified",
    ]
    search_fields = ["email", "first_name", "last_name", "user_type"]
    ordering = ["email"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name")}),
        (
            "Permissions",
            {
                "fields": (
                    "user_type",
                    "is_staff",
                    "is_active",
                    "is_superuser",
                    "email_verified",
                )
            },
        ),
        ("Important Dates", {"fields": ("date_last_login",)}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                    "user_type",
                    "is_staff",
                    "is_active",
                    "is_superuser",
                    "email_verified",
                ),
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
    search_fields = [
        "user__email",
        "subject_specialization",
        "assigned_classroom__name",
    ]
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
    list_display = [
        "name",
        "slug",
        "created_by",
        "is_active",
        "capacity",
        "created_at",
        "updated_at",
    ]
    search_fields = ["name", "slug", "created_by__email"]
    list_filter = ["is_active", "created_at"]
    ordering = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ["created_by"]
    filter_horizontal = ("co_teachers",)


admin.site.register(Invitation)
admin.site.register(WebcamCapture)
admin.site.register(FocusLossLog)
admin.site.register(ExamSession)
admin.site.register(ExamAnswer)



@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ["title", "classroom", "created_by", "created_at", "exam_id"]
    search_fields = ["title", "classroom__name", "created_by__email"]
    list_filter = ["classroom", "created_at"]
    raw_id_fields = ("created_by",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

@admin.register(ExamSubmission)
class ExamSubmissionAdmin(admin.ModelAdmin):
    list_display = ["student", "submission_key", "submitted_at"]
    search_fields = ["exam__title", "student__email", "submission_key"]
    # raw_id_fields = ("student")
    date_hierarchy = "submitted_at"
    ordering = ("-submitted_at",)

@admin.register(CourseMaterial)
class CourseMaterialAdmin(admin.ModelAdmin):
    list_display = ["title", "classroom", "uploaded_by", "uploaded_at"]
    search_fields = ["title", "description", "classroom__name", "uploaded_by__email"]
    list_filter = ["classroom", "uploaded_at"]
    list_display = ("title", "classroom", "uploaded_at", "uploaded_by")
    raw_id_fields = ("uploaded_by",)
    date_hierarchy = "uploaded_at"
    ordering = ("-uploaded_at",)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "classroom", "deadline", "created_at", "created_by")
    list_filter = ("classroom", "created_at", "deadline")
    search_fields = ("title", "description", "objectives")
    autocomplete_fields = ["course_materials"]
    raw_id_fields = ("created_by",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("classroom", "created_by").prefetch_related("course_materials")

admin.site.register(Question)