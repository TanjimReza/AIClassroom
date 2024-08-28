from .forms import LessonForm
from .models import Lesson, Classroom
from .models import Classroom
from .forms import CourseMaterialForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required

#! Authentication Views
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetCompleteView, PasswordResetConfirmView, PasswordResetDoneView, PasswordResetView
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone

from .forms import ClassroomForm, CustomLoginForm, CustomPasswordResetForm, InvitationForm, StudentRegistrationForm
from .models import *


class CustomLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = CustomLoginForm


class CustomLogoutView(LogoutView):
    next_page = "login"  # Redirect to login page after logout
    template_name = "registration/logged_out.html"


class CustomPasswordResetView(PasswordResetView):
    template_name = "registration/password_reset_form.html"
    form_class = CustomPasswordResetForm
    email_template_name = "registration/password_reset_email.html"
    subject_template_name = "registration/password_reset_subject.txt"
    success_url = reverse_lazy("password_reset_done")


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "registration/password_reset_confirm.html"
    success_url = reverse_lazy("password_reset_complete")


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "registration/password_reset_confirm.html"
    success_url = reverse_lazy("password_reset_complete")


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = "registration/password_reset_done.html"


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "registration/password_reset_complete.html"


#! ---------------------------


def home(request):
    user, type = request.user, request.user.get_user_type_display()
    return HttpResponse(f"Hello, world! {user} - {type}")


@login_required
def create_classroom(request):
    if request.method == "POST":
        form = ClassroomForm(request.POST)
        if form.is_valid():
            classroom = form.save(commit=False)
            classroom.created_by = request.user
            classroom.save()

            teacher_profile, created = TeacherProfile.objects.get_or_create(user=request.user, defaults={"assigned_classroom": classroom})
            if not created:
                teacher_profile.assigned_classroom = classroom
                teacher_profile.save()

            return redirect("classroom_detail", slug=classroom.slug)
    else:
        form = ClassroomForm()
    return render(request, "classroom_form.html", {"form": form})


@login_required
def send_invitation(request, slug):
    classroom = get_object_or_404(Classroom, slug=slug)
    if request.method == "POST":
        form = InvitationForm(request.POST, classroom=classroom)
        if form.is_valid():
            invitation = form.save()
            user_exists = Users.objects.filter(email=invitation.email).exists()
            if user_exists:
                invitation.send_invitation_email()
            else:
                invitation.register_first_enrolment()
            return redirect("classroom_detail", slug=classroom.slug)
    else:
        form = InvitationForm(classroom=classroom)
    return render(request, "send_invitation.html", {"form": form, "classroom": classroom})


def accept_invitation(request, token):
    invitation = get_object_or_404(Invitation, token=token, is_accepted=False)
    if request.user.is_authenticated and request.user.email == invitation.email:
        try:
            if invitation.register_first:
                return redirect("student_registration", token=invitation.token)
            invitation.accept(request.user)
            return redirect("classroom_detail", slug=invitation.classroom.slug)
        except ValueError as e:
            return HttpResponse(str(e), status=400)
    return HttpResponse("Unauthorized", status=401)


def student_registration(request, token):
    invitation = get_object_or_404(Invitation, token=token, enrolment_link_sent=True)

    if timezone.now() > invitation.enrolment_token_expiry:
        return HttpResponse("This registration link has expired.", status=400)

    if request.method == "POST":
        form = StudentRegistrationForm(request.POST, instance=Users(email=invitation.email, user_type="student"))
        if form.is_valid():
            user = form.save()
            login(request, user)
            invitation.accept(user)
            return redirect("classroom_detail", slug=invitation.classroom.slug)
    else:
        form = StudentRegistrationForm(initial={"email": invitation.email})

    return render(request, "student_registration.html", {"form": form})


@login_required
def teacher_dashboard(request):
    teacher_profile = get_object_or_404(TeacherProfile, user=request.user)
    created_classrooms = Classroom.objects.filter(created_by=request.user)
    enrolled_classrooms = Classroom.objects.filter(teachers__user=request.user).distinct()
    other_classrooms = enrolled_classrooms.exclude(created_by=request.user)

    context = {
        "created_classrooms": created_classrooms,
        "enrolled_classrooms": enrolled_classrooms,
        "other_classrooms": other_classrooms,
    }
    print(context)
    return render(request, "teacher_dashboard.html", context)


@login_required
def classroom_detail(request, slug):
    classroom = get_object_or_404(Classroom, slug=slug)
    if not classroom.teachers.filter(user=request.user).exists() and not classroom.students.filter(user=request.user).exists():
        return HttpResponse("You are not authorized to view this classroom.", status=403)

    students = classroom.students.all()
    co_teachers = classroom.teachers.exclude(user=request.user)
    lessons = classroom.lessons.all()  # Fetch all lessons associated with the classroom

    context = {
        "classroom": classroom,
        "students": students,
        "co_teachers": co_teachers,
        "lessons": lessons,  # Pass lessons to the template
    }

    return render(request, "classroom_detail.html", context)


@login_required
def lesson_detail(request, classroom_slug, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id, classroom__slug=classroom_slug)
    is_teacher = request.user.is_staff or request.user == lesson.classroom.created_by or lesson.classroom.co_teachers.filter(id=request.user.id).exists()

    context = {
        "lesson": lesson,
        "is_teacher": is_teacher,  # Pass the teacher check to the template
    }

    return render(request, "lesson_detail.html", context)


@login_required
def upload_material(request, slug):
    classroom = get_object_or_404(Classroom, slug=slug)
    if not request.user.is_staff and request.user != classroom.created_by:
        return HttpResponse("You do not have permission to upload materials to this classroom.", status=403)

    if request.method == "POST":
        form = CourseMaterialForm(request.POST, request.FILES, classroom=classroom)
        if form.is_valid():
            form.instance.uploaded_by = request.user  # Set the user who uploads the files
            form.save()
            return redirect("classroom_detail", slug=slug)
    else:
        form = CourseMaterialForm()

    return render(request, "upload_material.html", {"form": form, "classroom": classroom})


@login_required
def create_lesson(request, classroom_slug):
    classroom = get_object_or_404(Classroom, slug=classroom_slug)

    if request.method == "POST":
        form = LessonForm(request.POST, classroom=classroom)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.classroom = classroom
            lesson.created_by = request.user
            lesson.save()
            form.save_m2m()  # Save many-to-many relationships
            return redirect("classroom_detail", slug=classroom.slug)
    else:
        form = LessonForm(classroom=classroom)

    return render(request, "create_lesson.html", {"form": form, "classroom": classroom})


@login_required
def update_lesson(request, classroom_slug, lesson_id):
    classroom = get_object_or_404(Classroom, slug=classroom_slug)
    lesson = get_object_or_404(Lesson, id=lesson_id, classroom=classroom)

    if request.method == "POST":
        form = LessonForm(request.POST, instance=lesson, classroom=classroom)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.classroom = classroom
            lesson.created_by = request.user
            lesson.save()
            form.save_m2m()  # Save many-to-many relationships
            # return redirect("classroom_detail", slug=classroom.slug)
            # redirect to the lesson detail page
            return redirect("lesson_detail", classroom_slug=classroom.slug, lesson_id=lesson.id)
    else:
        form = LessonForm(instance=lesson, classroom=classroom)

    return render(request, "update_lesson.html", {"form": form, "classroom": classroom, "lesson": lesson})


@login_required
def classroom_content_management(request, classroom_slug):
    classroom = get_object_or_404(Classroom, slug=classroom_slug)

    if not request.user.is_staff and request.user != classroom.created_by:
        # If the user is not authorized, return a 403 Forbidden response
        return HttpResponseForbidden("You do not have permission to manage content in this classroom.")

    # Retrieve all course materials associated with this classroom
    course_materials = CourseMaterial.objects.filter(classroom=classroom)

    # Render the management template
    return render(
        request,
        "classroom_content_management.html",
        {
            "classroom": classroom,
            "course_materials": course_materials,
        },
    )


from django.shortcuts import render, redirect, get_object_or_404
from .forms import CourseMaterialForm


@login_required
def edit_course_material(request, classroom_slug, pk):
    material = get_object_or_404(CourseMaterial, pk=pk, classroom__slug=classroom_slug)

    if not request.user.is_staff and request.user != material.classroom.created_by:
        return HttpResponseForbidden("You do not have permission to edit this content.")

    if request.method == "POST":
        form = CourseMaterialForm(request.POST, request.FILES, instance=material)
        if form.is_valid():
            form.save()
            return redirect("classroom_content_management", classroom_slug=classroom_slug)
    else:
        form = CourseMaterialForm(instance=material)

    return render(request, "edit_course_material.html", {"form": form, "material": material})


from django.shortcuts import redirect, get_object_or_404
from django.http import HttpResponseForbidden


@login_required
def delete_course_material(request, classroom_slug, pk):
    material = get_object_or_404(CourseMaterial, pk=pk, classroom__slug=classroom_slug)

    if not request.user.is_staff and request.user != material.classroom.created_by:
        return HttpResponseForbidden("You do not have permission to delete this content.")

    if request.method == "POST":
        material.delete()
        return redirect("classroom_content_management", classroom_slug=classroom_slug)

    return render(request, "confirm_delete.html", {"material": material})


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Lesson, Question
from .forms import QuestionForm


@login_required
def add_question(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)

    if request.method == "POST":
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.lesson = lesson
            question.save()
            return redirect("lesson_detail", classroom_slug=lesson.classroom.slug, lesson_id=lesson.id)
    else:
        form = QuestionForm()

    return render(request, "add_question.html", {"form": form, "lesson": lesson})


@login_required
def edit_question(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    lesson = question.lesson

    if request.method == "POST":
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            return redirect("lesson_detail", classroom_slug=lesson.classroom.slug, lesson_id=lesson.id)
    else:
        form = QuestionForm(instance=question)

    return render(request, "edit_question.html", {"form": form, "lesson": lesson})


@login_required
def delete_question(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    lesson = question.lesson

    if request.method == "POST":
        question.delete()
        return redirect("lesson_detail", classroom_slug=lesson.classroom.slug, lesson_id=lesson.id)

    return render(request, "delete_question.html", {"question": question, "lesson": lesson})
