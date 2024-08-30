import re

from django.contrib import admin
from django.urls import include, path, re_path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    # custom login path
    re_path(r"^login/$", views.CustomLoginView.as_view(), name="login"),
    re_path(r"^logout/$", views.CustomLogoutView.as_view(), name="logout"),
    path("password_reset/", views.CustomPasswordResetView.as_view(), name="password_reset"),
    path("reset/<uidb64>/<token>/", views.CustomPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("password_reset/done/", views.CustomPasswordResetDoneView.as_view(), name="password_reset_done"),
    path("reset/done/", views.CustomPasswordResetCompleteView.as_view(), name="password_reset_complete"),
    path("classroom/create/", views.create_classroom, name="create_classroom"),
    path("classroom/<slug:slug>/invite/", views.send_invitation, name="send_invitation"),
    path("invite/accept/<uuid:token>/", views.accept_invitation, name="accept_invitation"),
    path("register/<uuid:token>/", views.student_registration, name="student_registration"),
    path("dashboard/", views.teacher_dashboard, name="teacher_dashboard"),
    path("classroom/<slug:slug>/", views.classroom_detail, name="classroom_detail"),
    path("classroom/<slug:slug>/upload_material/", views.upload_material, name="upload_material"),
    path("classroom/<slug:classroom_slug>/lesson/create/", views.create_lesson, name="create_lesson"),
    path("classroom/<slug:classroom_slug>/manage-content/", views.classroom_content_management, name="classroom_content_management"),
    path("classroom/<slug:classroom_slug>/material/<int:pk>/edit/", views.edit_course_material, name="edit_course_material"),
    path("classroom/<slug:classroom_slug>/material/<int:pk>/delete/", views.delete_course_material, name="delete_course_material"),
    path("classroom/<slug:classroom_slug>/lesson/<int:lesson_id>/", views.lesson_detail, name="lesson_detail"),
    path("lesson/<int:lesson_id>/question/add/", views.add_question, name="add_question"),
    path("question/<int:question_id>/edit/", views.edit_question, name="edit_question"),
    path("question/<int:question_id>/delete/", views.delete_question, name="delete_question"),
    path("classroom/<slug:classroom_slug>/create_exam/", views.create_exam, name="create_exam"),
    path("exam/<str:exam_id>/take/", views.take_exam, name="take_exam"),
    path("exam/<str:exam_id>/", views.exam_detail, name="exam_detail"),
    path("exam/session/<uuid:session_token>/", views.exam_session, name="exam_session"),
    path("exam/session/<uuid:session_token>/capture-image/", views.capture_image, name="capture_image"),
    path("exam/session/<uuid:session_token>/log-focus-loss/", views.log_focus_loss, name="log_focus_loss"),
    path("classroom/<slug:classroom_slug>/lesson/<int:lesson_id>/update/", views.update_lesson, name="update_lesson"),
    path("lesson/<slug:classroom_slug>/<int:lesson_id>/generate-ai-questions/", views.generate_ai_questions, name="generate_ai_questions"),
    path("lesson/<slug:classroom_slug>/<int:lesson_id>/process-ai-generation/<int:num_questions>/", views.process_ai_generation, name="process_ai_generation"),
    path('classroom/<slug:classroom_slug>/create_exam/', views.create_exam, name='create_exam'),
    path('exam/<str:exam_id>/', views.exam_detail, name='exam_detail'),
    path('exam/session/<uuid:session_token>/', views.exam_session, name='exam_session'),
    path('exam/session/<uuid:session_token>/capture-image/', views.capture_image, name='capture_image'),
    path('exam/session/<uuid:session_token>/log-focus-loss/', views.log_focus_loss, name='log_focus_loss'),
    path('exam/session/<uuid:session_token>/submit/', views.submit_exam, name='submit_exam'),
    path('exam/submission/<str:submission_key>/grade/', views.grade_submission, name='grade_submission'),
    path('exam/submission/success/', views.exam_submission_success, name='exam_submission_success'),    
    path('exam/submission/<str:submission_key>/response/', views.view_exam_response, name='view_exam_response'),
    
    path("classroom/<slug:classroom_slug>/create_exam/", views.create_exam, name="create_exam"),
    path("exams/", views.exam_overview, name="exam_overview"),
    path("exam/<str:exam_id>/take/", views.take_exam, name="take_exam"),
    path("exam/<str:exam_id>/", views.exam_detail, name="exam_detail"),
    path("exam/session/<uuid:session_token>/", views.exam_session, name="exam_session"),
    path("exam/session/<uuid:session_token>/capture-image/", views.capture_image, name="capture_image"),
    path("exam/session/<uuid:session_token>/log-focus-loss/", views.log_focus_loss, name="log_focus_loss"),
]
