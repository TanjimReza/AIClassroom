from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("accounts/", include("django.contrib.auth.urls")),
    path('register/', views.register, name='register'),
    path('verify-email/<uuid:token>/', views.verify_email, name='verify-email'),
    path('profile/', views.profile, name='profile'),
    path('dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('create-classroom/', views.create_classroom, name='create_classroom'),
    
]
