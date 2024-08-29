from .models import Question
from .models import Lesson, CourseMaterial
from .models import CourseMaterial
from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, UserCreationForm

from .models import AdminProfile, Classroom, Invitation, StudentProfile, TeacherProfile, Users, Lesson, CourseMaterial, Question, Exam, ExamAnswer


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
        fields = ["name", "description", "capacity"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class InvitationForm(forms.Form):
    email = forms.EmailField(label="Student Email")

    def __init__(self, *args, **kwargs):
        self.classroom = kwargs.pop("classroom", None)
        super().__init__(*args, **kwargs)

    def save(self):
        email = self.cleaned_data["email"]
        invitation = Invitation.objects.create(classroom=self.classroom, email=email)
        return invitation


class StudentRegistrationForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Users
        fields = ["email", "first_name", "last_name"]
        widgets = {
            "email": forms.EmailInput(attrs={"readonly": "readonly"}),
            "user_type": forms.HiddenInput(),
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


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result


class CourseMaterialForm(forms.ModelForm):
    file = MultipleFileField(required=False)
    title = forms.CharField(required=False, max_length=255)
    description = forms.CharField(widget=forms.Textarea, required=False)

    class Meta:
        model = CourseMaterial
        fields = ["file", "title", "description"]

    def __init__(self, *args, **kwargs):
        self.classroom = kwargs.pop("classroom", None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        files = self.cleaned_data["file"]
        materials = []
        for file in files:
            material = CourseMaterial(
                # Use provided title or default to filename
                title=self.cleaned_data["title"] or file.name,
                # Use provided description or None if not filled
                description=self.cleaned_data.get("description"),
                file=file,
                classroom=self.classroom,
                uploaded_by=self.instance.uploaded_by if self.instance.uploaded_by else None,
            )
            if commit:
                material.save()
            materials.append(material)
        return materials


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ["title", "description", "objectives", "deadline", "course_materials"]

    def __init__(self, *args, **kwargs):
        classroom = kwargs.pop("classroom", None)
        super().__init__(*args, **kwargs)

        # Restrict course materials to those within the selected classroom
        if classroom:
            self.fields["course_materials"].queryset = CourseMaterial.objects.filter(classroom=classroom)


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ["question_text", "question_type", "choices", "correct_answer", "points"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["choices"].widget = forms.Textarea(attrs={"rows": 3, "placeholder": "Enter choices separated by commas (only for Multiple Choice)"})
        # Ensure choices are not required by default
        self.fields["choices"].required = False
        self.fields["correct_answer"].widget = forms.TextInput(attrs={"placeholder": "Enter the correct answer"})

    def clean(self):
        cleaned_data = super().clean()
        question_type = cleaned_data.get("question_type")

        # Validate the choices field only if it's a multiple choice question
        if question_type == "multiple_choice":
            choices = cleaned_data.get("choices")
            if not choices or len(choices.split(",")) < 2:
                self.add_error("choices", "Please provide at least two choices for a multiple choice question.")

        return cleaned_data


class GenerateAIQuestionsForm(forms.Form):
    number_of_questions = forms.IntegerField(label="Number of Questions", min_value=1, help_text="Enter the number of AI-generated questions you want.")


class ExamForm(forms.ModelForm):
    lessons = forms.ModelMultipleChoiceField(queryset=Lesson.objects.none(), widget=forms.CheckboxSelectMultiple, required=False)

    class Meta:
        model = Exam
        fields = ["title", "description", "start_time", "end_time", "duration_minutes", "lessons"]
        widgets = {
            "start_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        classroom = kwargs.pop("classroom", None)
        super().__init__(*args, **kwargs)
        if classroom:
            self.fields["lessons"].queryset = Lesson.objects.filter(classroom=classroom)


class ExamSubmissionForm(forms.Form):
    def __init__(self, *args, **kwargs):
        exam = kwargs.pop("exam")
        super().__init__(*args, **kwargs)

        for question in exam.get_questions():
            field_name = f"question_{question.id}"
            if question.question_type == "multiple_choice":
                self.fields[field_name] = forms.ChoiceField(choices=[(opt, opt) for opt in question.choices.splitlines()], widget=forms.RadioSelect)
            elif question.question_type == "true_false":
                self.fields[field_name] = forms.ChoiceField(choices=[("True", "True"), ("False", "False")], widget=forms.RadioSelect)
            elif question.question_type == "short_answer":
                self.fields[field_name] = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))
            elif question.question_type == "long_answer":
                self.fields[field_name] = forms.CharField(widget=forms.Textarea(attrs={"rows": 5}))
            elif question.question_type == "fill_in_the_blank":
                self.fields[field_name] = forms.CharField()
            else:
                raise ValueError(f"Invalid question type: {question.question_type}")
