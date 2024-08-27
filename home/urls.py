from django.contrib import admin
from django.urls import path, include, re_path
from . import views
import re

urlpatterns = [
    path("", views.home, name="home"),
    # custom login path
    re_path(r"^login/$", views.CustomLoginView.as_view(), name="login"),
    re_path(r"^logout/$", views.CustomLogoutView.as_view(), name="logout"),
    path("password_reset/", views.CustomPasswordResetView.as_view(), name="password_reset"),
    path("reset/<uidb64>/<token>/", views.CustomPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("password_reset/done/", views.CustomPasswordResetDoneView.as_view(), name="password_reset_done"),
    path("reset/done/", views.CustomPasswordResetCompleteView.as_view(), name="password_reset_complete"),
    path('classroom/create/', views.create_classroom, name='create_classroom'),
    path('classroom/<slug:slug>/invite/', views.send_invitation, name='send_invitation'),
    path('invite/accept/<uuid:token>/', views.accept_invitation, name='accept_invitation'),
    path('register/<uuid:token>/', views.student_registration, name='student_registration'),
    path('dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('classroom/<slug:slug>/', views.classroom_detail, name='classroom_detail'),
    
]
