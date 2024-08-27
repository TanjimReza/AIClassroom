from .models import Classroom
from .forms import CourseMaterialForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required

#! Authentication Views
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetCompleteView, PasswordResetConfirmView, PasswordResetDoneView, PasswordResetView
from django.http import HttpResponse
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
    return HttpResponse("Hello, world. You're at the home page.")


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

    context = {
        "classroom": classroom,
        "students": students,
        "co_teachers": co_teachers,
    }

    return render(request, "classroom_detail.html", context)


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
