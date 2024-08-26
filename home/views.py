from .forms import CustomPasswordResetForm
from django.urls import reverse_lazy
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.shortcuts import render
from django.contrib.auth import logout, authenticate, login
from django.shortcuts import redirect, get_object_or_404, render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView, PasswordResetView, PasswordResetDoneView, PasswordResetCompleteView
from .forms import CustomLoginForm
from django.contrib.auth.views import LogoutView

# Create your views here.


def home(request):
    return HttpResponse("Hello, world. You're at the home page.")


#! Authentication Views


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
