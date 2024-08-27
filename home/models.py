from datetime import timedelta
import uuid
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.text import slugify
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings

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
        if teacher.user_type == 'teacher':
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
            if user.user_type == 'student':
                student_profile, created = StudentProfile.objects.get_or_create(user=user, defaults={'enrolled_classroom': self.classroom})
                student_profile.enrolled_classroom = self.classroom
                student_profile.save()
                self.is_accepted = True
                self.save()
            else:
                teacher_profile, created = TeacherProfile.objects.get_or_create(user=user, defaults={'assigned_classroom': self.classroom})
                teacher_profile.assigned_classroom = self.classroom
                teacher_profile.save()
                self.is_accepted = True
                self.save()
        else:
            raise ValueError("Email mismatch for this invitation.")

    def register_first_enrolment(self):
        enrolment_url = reverse('student_registration', kwargs={'token': self.token})
        full_url = f"{settings.SITE_URL}{enrolment_url}"
        subject = f"Registration required to join {self.classroom.name}"
        message = f"You have been invited to join the classroom {self.classroom.name}. Please register here: {full_url} (expires in 48 hours)."

        self.enrolment_token_expiry = timezone.now() + timedelta(hours=48)
        self.enrolment_link_sent = True
        self.register_first = True
        self.save()

        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [self.email])

    def send_invitation_email(self):
        token_url = reverse('accept_invitation', kwargs={'token': self.token})
        full_url = f"{settings.SITE_URL}{token_url}"
        subject = f"Invitation to join {self.classroom.name}"
        message = f"You have been invited to join the classroom {self.classroom.name}. Click the link to join: {full_url}"

        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [self.email])
