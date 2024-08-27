from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm
from .models import Users, TeacherProfile, AdminProfile, StudentProfile, Classroom, Invitation


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
        user.user_type = "general_admin"
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


class ClassroomForm(forms.ModelForm):
    class Meta:
        model = Classroom
        fields = ['name', 'description', 'capacity']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class InvitationForm(forms.Form):
    email = forms.EmailField(label='Student Email')

    def __init__(self, *args, **kwargs):
        self.classroom = kwargs.pop('classroom', None)
        super().__init__(*args, **kwargs)

    def save(self):
        email = self.cleaned_data['email']
        invitation = Invitation.objects.create(classroom=self.classroom, email=email)
        return invitation


class StudentRegistrationForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Users
        fields = ['email', 'first_name', 'last_name']
        widgets = {
            'email': forms.EmailInput(attrs={'readonly': 'readonly'}),
            'user_type': forms.HiddenInput(),
        }

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.user_type = "student"
        if commit:
            user.save()
        return user


