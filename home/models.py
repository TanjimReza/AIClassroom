import os
import shutil
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMultiAlternatives
from django.db import models, transaction
from django.db.models import F
from django.db.utils import IntegrityError
from django.dispatch import receiver
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.text import slugify
import uuid


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, user_type="student", **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)

        if user_type == "general_admin":
            extra_fields.setdefault("is_staff", True)
            extra_fields.setdefault("is_superuser", True)
            extra_fields.setdefault("is_active", True)

        user = self.model(email=email, user_type=user_type, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("user_type", "general_admin")

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
            ("student", "Student"),
        ],
    )
    date_last_login = models.DateTimeField(null=True, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_new_user = models.BooleanField(default=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.UUIDField(default=uuid.uuid4)

    objects = CustomUserManager()

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return f"{self.email} ({self.user_type})"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if not self.email_verification_token:
            self.email_verification_token = uuid.uuid4()
        super().save(*args, **kwargs)

        if is_new:
            print("New User Created")
        else:
            print("User Updated")

        if self.user_type == "general_admin":
            self.is_superuser = True
            self.is_staff = True

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

User = get_user_model()

class Classroom(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_classrooms')
    is_active = models.BooleanField(default=True)
    enrollment_code = models.CharField(max_length=20, unique=True)
    students = models.ManyToManyField(User, through='Student', related_name='enrolled_classrooms')
    capacity = models.IntegerField(default=30)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    schedule = models.JSONField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_classroom_admins(self):
        return User.objects.filter(classroomadmin__classroom=self)

    def __str__(self):
        return self.name


class ClassroomAdmin(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.email

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        user = self.user
        super().delete(*args, **kwargs)
        user.delete()


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.email

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        user = self.user
        super().delete(*args, **kwargs)
        user.delete()
