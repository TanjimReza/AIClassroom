from django.shortcuts import render
from django.contrib.auth import logout, authenticate, login
from django.shortcuts import redirect, get_object_or_404, render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .forms import UserRegistrationForm, ClassroomForm
from .models import Users, Classroom
from .utils import send_verification_email

# Create your views here.

def home(request):
    return HttpResponse("Hello, world. You're at the home page.")

def logout_view(request):
    logout(request)
    return redirect("home")

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.user_type = form.cleaned_data.get('user_type')
            # user.is_active = False
            user.save()
            # send_verification_email(user)
            for_now = send_verification_email(user)
            verify_email(request, for_now)
            return redirect('email_verification_sent')
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

def verify_email(request, token):
    user = get_object_or_404(Users, email_verification_token=token)
    user.email_verified = True
    user.is_active = True
    user.email_verification_token = None
    user.save()
    return HttpResponse('Email verified successfully. You can now log in.')

@login_required
def profile(request):
    return render(request, 'profile.html')

def teacher_dashboard(request):
    user = request.user
    created_classrooms = Classroom.objects.filter(created_by=user)
    enrolled_classrooms = Classroom.objects.filter(students=user)
    other_classrooms = enrolled_classrooms.exclude(created_by=user)
    
    context = {
        'created_classrooms': created_classrooms,
        'enrolled_classrooms': enrolled_classrooms,
        'other_classrooms': other_classrooms,
    }
    
    return render(request, 'dashboard/teacher_dashboard.html', context)

def create_classroom(request):
    if request.method == 'POST':
        form = ClassroomForm(request.POST)
        if form.is_valid():
            classroom = form.save(commit=False)
            classroom.created_by = request.user
            classroom.save()
            return redirect('teacher_dashboard')
    else:
        form = ClassroomForm()

    return render(request, 'dashboard/create_classroom.html', {'form': form})