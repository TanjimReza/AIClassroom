from django.shortcuts import render
from django.contrib.auth import logout, authenticate, login
from django.shortcuts import redirect, get_object_or_404, render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .forms import UserRegistrationForm, ClassroomForm
from .models import Users, Classroom

# Create your views here.


def home(request):
    return HttpResponse("Hello, world. You're at the home page.")
