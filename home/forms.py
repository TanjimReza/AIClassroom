from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Users, Classroom

class UserRegistrationForm(UserCreationForm):
    class Meta:
        model = Users
        fields = ['email', 'first_name', 'last_name', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError('Email is required')

        domain = email.split('@')[1]
        valid_domains = {
            'gmail.com': 'classroom_admin',
            'teacher.me': 'classroom_admin',
            'student.me': 'student'
        }

        if domain not in valid_domains:
            raise forms.ValidationError('Invalid domain')

        self.cleaned_data['user_type'] = valid_domains[domain]
        return email

class ClassroomForm(forms.ModelForm):
    class Meta:
        model = Classroom
        fields = ['name', 'description', 'capacity', 'start_date', 'end_date', 'schedule']