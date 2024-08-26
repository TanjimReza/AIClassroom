from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm
from .models import Users, TeacherProfile, AdminProfile, StudentProfile


class CustomLoginForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise forms.ValidationError("This account is inactive.", code="inactive")
        if not user.email_verified:
            raise forms.ValidationError("Email address is not verified.", code="email_not_verified")

    def clean_username(self):
        username = self.cleaned_data.get("username")
        return username.lower()


class CustomPasswordResetForm(PasswordResetForm):
    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not Users.objects.filter(email=email).exists():
            raise forms.ValidationError("No user with that email address exists.")
        return email


class UsersCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Users
        fields = ("email", "user_type", "first_name", "last_name")


class TeacherUserCreationForm(UserCreationForm):
    class Meta:
        model = Users
        fields = ("email", "first_name", "last_name", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = "teacher"
        if commit:
            user.save()
            TeacherProfile.objects.create(user=user)
        return user


class AdminUserCreationForm(UserCreationForm):
    class Meta:
        model = Users
        fields = ("email", "first_name", "last_name", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = "admin"
        if commit:
            user.save()
            AdminProfile.objects.create(user=user)
        return user


class StudentUserCreationForm(UserCreationForm):
    class Meta:
        model = Users
        fields = ("email", "first_name", "last_name", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = "student"
        if commit:
            user.save()
            StudentProfile.objects.create(user=user)
        return user
