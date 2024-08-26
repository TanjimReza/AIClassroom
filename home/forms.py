from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model


Users = get_user_model()


class CustomLoginForm(AuthenticationForm):

    def confirm_login_allowed(self, user):
        print(user)
        if not user.is_active:
            raise forms.ValidationError("This account is inactive.", code="inactive")
        if not user.email_verified:
            raise forms.ValidationError("Email address is not verified.", code="email_not_verified")

    def clean_username(self):
        username = self.cleaned_data.get("username")
        return username.lower()


from django import forms
from django.contrib.auth.forms import PasswordResetForm


class CustomPasswordResetForm(PasswordResetForm):
    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not Users.objects.filter(email=email).exists():
            raise forms.ValidationError("No user with that email address exists.")
        return email
