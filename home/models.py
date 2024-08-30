import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.mail import send_mail
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.core.files.storage import default_storage


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, user_type="student", **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)

        user = self.model(email=email, user_type=user_type, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("user_type", "general_admin")
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("email_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        if extra_fields.get("user_type") != "general_admin":
            raise ValueError("Superuser must have user_type as general_admin.")

        return self.create_user(email, password, **extra_fields)


class Users(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    user_type = models.CharField(
        max_length=20,
        choices=[
            ("general_admin", "General Admin"),
            ("classroom_admin", "Class Admin"),
            ("teacher", "Teacher"),
            ("student", "Student"),
        ],
    )
    date_last_login = models.DateTimeField(null=True, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=True)
    email_verification_token = models.UUIDField(default=uuid.uuid4)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = CustomUserManager()

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return f"{self.email} ({self.user_type})"

    def save(self, *args, **kwargs):
        if not self.email_verification_token:
            self.email_verification_token = uuid.uuid4()
        super().save(*args, **kwargs)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"


class AdminProfile(models.Model):
    user = models.OneToOneField(Users, on_delete=models.CASCADE, primary_key=True)
    role_description = models.CharField(max_length=100, default="System Administrator")

    def __str__(self):
        return f"{self.user.email} - Admin"

    def delete(self, *args, **kwargs):
        user = self.user
        super().delete(*args, **kwargs)
        user.delete()


class TeacherProfile(models.Model):
    user = models.OneToOneField(Users, on_delete=models.CASCADE, primary_key=True)
    subject_specialization = models.CharField(max_length=100)
    assigned_classroom = models.ForeignKey("Classroom", on_delete=models.CASCADE, related_name="teachers", null=True, blank=True)

    def __str__(self):
        return f"{self.user.email} - Teacher"

    def delete(self, *args, **kwargs):
        user = self.user
        super().delete(*args, **kwargs)
        user.delete()


class StudentProfile(models.Model):
    user = models.OneToOneField(Users, on_delete=models.CASCADE, primary_key=True)
    enrolled_classroom = models.ForeignKey("Classroom", on_delete=models.CASCADE, related_name="students", null=True, blank=True)

    def __str__(self):
        return f"{self.user.email} - Student"

    def delete(self, *args, **kwargs):
        user = self.user
        super().delete(*args, **kwargs)
        user.delete()


class Classroom(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="created_classrooms")
    co_teachers = models.ManyToManyField(Users, related_name="co_teaching_classrooms", blank=True)
    is_active = models.BooleanField(default=True)
    capacity = models.IntegerField(default=30)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def add_co_teacher(self, teacher: Users):
        if teacher.user_type == "teacher":
            self.co_teachers.add(teacher)
        else:
            raise ValueError("Only users with teacher role can be co-teachers.")


class Invitation(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_accepted = models.BooleanField(default=False)
    invited_at = models.DateTimeField(auto_now_add=True)
    enrolment_link_sent = models.BooleanField(default=False)
    enrolment_token_expiry = models.DateTimeField(null=True, blank=True)
    register_first = models.BooleanField(default=False)

    def __str__(self):
        return f"Invitation to {self.email} for {self.classroom.name}"

    def accept(self, user: Users):
        if user.email == self.email:
            if user.user_type == "student":
                student_profile, created = StudentProfile.objects.get_or_create(user=user, defaults={"enrolled_classroom": self.classroom})
                student_profile.enrolled_classroom = self.classroom
                student_profile.save()
                self.is_accepted = True
                self.save()
            else:
                teacher_profile, created = TeacherProfile.objects.get_or_create(user=user, defaults={"assigned_classroom": self.classroom})
                teacher_profile.assigned_classroom = self.classroom
                teacher_profile.save()
                self.is_accepted = True
                self.save()
        else:
            raise ValueError("Email mismatch for this invitation.")

    def register_first_enrolment(self):
        enrolment_url = reverse("student_registration", kwargs={"token": self.token})
        full_url = f"{settings.SITE_URL}{enrolment_url}"
        subject = f"Registration required to join {self.classroom.name}"
        message = f"You have been invited to join the classroom {self.classroom.name}. Please register here: {full_url} (expires in 48 hours)."

        self.enrolment_token_expiry = timezone.now() + timedelta(hours=48)
        self.enrolment_link_sent = True
        self.register_first = True
        self.save()

        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [self.email])

    def send_invitation_email(self):
        token_url = reverse("accept_invitation", kwargs={"token": self.token})
        full_url = f"{settings.SITE_URL}{token_url}"
        subject = f"Invitation to join {self.classroom.name}"
        message = f"You have been invited to join the classroom {self.classroom.name}. Click the link to join: {full_url}"

        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [self.email])


import os


def classroom_directory_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/coursename_contents/<filename>
    return os.path.join(f"{instance.classroom.name}_contents", filename)


from django.core.files.storage import default_storage


class CourseMaterial(models.Model):
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to=classroom_directory_path)
    course_material_url = models.URLField(max_length=500, blank=True, editable=False, null=True)
    description = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="materials")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)

    def save(self, *args, **kwargs):
        # Generate the relative URL based on classroom and filename
        relative_path = classroom_directory_path(self, os.path.basename(self.file.name))
        self.course_material_url = default_storage.url(relative_path)

        # Construct the full public URL (if needed)
        # self.public_url = f"{settings.SITE_URL}{self.course_material_url}"

        existing_material = CourseMaterial.objects.filter(classroom=self.classroom, course_material_url=self.course_material_url).first()

        if existing_material:
            # If a file with the same URL already exists, delete it
            default_storage.delete(existing_material.file.path)
            existing_material.delete()

        # Now save the new entry with the correct URL
        super(CourseMaterial, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.file:
            file_path = self.file.path
            if os.path.exists(file_path):
                print("Deleting file from disk")
                os.remove(file_path)
                if not os.path.exists(file_path):
                    print("File deletion successful")
                else:
                    print("File deletion failed")

        super(CourseMaterial, self).delete(*args, **kwargs)

    def get_full_url(self, site=settings.SITE_URL):
        return f"{site}{self.course_material_url}"

    def __str__(self):
        return f"{self.title} ({self.classroom.name})"


from django.db import models


class Lesson(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    objectives = models.TextField(blank=True, null=True)
    deadline = models.DateTimeField(blank=True, null=True)
    course_materials = models.ManyToManyField(CourseMaterial, related_name="lessons", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.title} ({self.classroom.name})"

    class Meta:
        unique_together = ("classroom", "title")


class Question(models.Model):
    QUESTION_TYPES = [
        ("multiple_choice", "Multiple Choice"),
        ("true_false", "True/False"),
        ("short_answer", "Short Answer"),
        ("long_answer", "Long Answer/Essay"),
        ("fill_in_the_blank", "Fill-in-the-Blank"),
    ]

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="questions")
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    choices = models.TextField(blank=True, null=True)
    correct_answer = models.TextField(blank=True, null=True)
    points = models.IntegerField(default=1, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_question_type_display()} - {self.question_text[:50]}"


class Exam(models.Model):
    classroom = models.ForeignKey("Classroom", on_delete=models.CASCADE, related_name="exams")
    exam_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration_minutes = models.IntegerField(help_text="Duration in minutes")
    is_published = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_exams")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    lessons = models.ManyToManyField("Lesson", related_name="exams", blank=True)
    question_count = models.IntegerField(default=0)

    def get_questions(self):
        return Question.objects.filter(lesson__in=self.lessons.all())

    def __str__(self):
        return f"{self.title} - {self.classroom.name}"


class ExamSession(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="sessions")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="exam_sessions")
    session_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"Session {self.session_token} for {self.exam.title} by {self.student.get_full_name()}"

    def get_absolute_url(self):
        return reverse("exam_session", kwargs={"session_token": self.session_token})


class WebcamCapture(models.Model):
    session = models.ForeignKey(ExamSession, on_delete=models.CASCADE, related_name="captures")
    image = models.ImageField(upload_to="webcam_captures/")
    captured_at = models.DateTimeField(auto_now_add=True)


class FocusLossLog(models.Model):
    session = models.ForeignKey(ExamSession, on_delete=models.CASCADE, related_name="focus_logs")
    timestamp = models.DateTimeField(auto_now_add=True)


class ExamAnswer(models.Model):
    session = models.ForeignKey(ExamSession, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="answers")
    text_answer = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    marks_obtained = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"Answer by {self.student.email} to {self.question}"
    
    
class ExamSubmission(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exam_submissions')
    exam_session = models.OneToOneField(ExamSession, on_delete=models.CASCADE, related_name='submission')
    answers = models.JSONField()
    total_score = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[('ungraded', 'Ungraded'), ('graded', 'Graded')], default='ungraded')
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submission_key = models.CharField(max_length=255, unique=True, blank=False, primary_key=True)

    def __str__(self):
        return f"Submission for {self.exam_session.exam.title} by {self.exam_session.student.get_full_name()}"

    def save(self, *args, **kwargs):
        if not self.submission_key:
            self.submission_key = self.get_submission_key()
        super().save(*args, **kwargs)

    def get_submission_key(self):
        return f"{self.student.first_name}_{self.exam_session.exam.title}_{self.exam_session.exam.classroom.slug}"