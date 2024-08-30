import base64
from django.core.files.base import ContentFile
from .models import ExamSession, WebcamCapture, FocusLossLog
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from openai import OpenAI
import re
from tika import parser
import json
import fitz  # PyMuPDF
import openai
from .forms import GenerateAIQuestionsForm
from django.conf import settings
from .forms import QuestionForm
from .models import Lesson, Question
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, get_object_or_404
from .forms import LessonForm
from .models import AdminProfile, Classroom, Invitation, StudentProfile, TeacherProfile, Users, Lesson, CourseMaterial, Question, Exam, ExamAnswer, ExamSession, ExamSubmission
from .forms import CourseMaterialForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required

#! Authentication Views
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetCompleteView, PasswordResetConfirmView, PasswordResetDoneView, PasswordResetView
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone

from .forms import *


class CustomLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = CustomLoginForm


class CustomLogoutView(LogoutView):
    next_page = "login"  # Redirect to login page after logout
    template_name = "registration/logged_out.html"


class CustomPasswordResetView(PasswordResetView):
    template_name = "registration/password_reset_form.html"
    form_class = CustomPasswordResetForm
    email_template_name = "registration/password_reset_email.html"
    subject_template_name = "registration/password_reset_subject.txt"
    success_url = reverse_lazy("password_reset_done")


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "registration/password_reset_confirm.html"
    success_url = reverse_lazy("password_reset_complete")


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "registration/password_reset_confirm.html"
    success_url = reverse_lazy("password_reset_complete")


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = "registration/password_reset_done.html"


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "registration/password_reset_complete.html"


#! ---------------------------


def home(request):
    user, type = request.user, request.user.get_user_type_display()
    # return HttpResponse(f"Hello, world! {user} - {type}"
    return render(request, "base.html")


def home(request):
    user, type = request.user, request.user.get_user_type_display()
    # return HttpResponse(f"Hello, world! {user} - {type}"
    return render(request, "base.html")


@login_required
def create_classroom(request):
    if request.method == "POST":
        form = ClassroomForm(request.POST)
        if form.is_valid():
            classroom = form.save(commit=False)
            classroom.created_by = request.user
            classroom.save()

            teacher_profile, created = TeacherProfile.objects.get_or_create(user=request.user, defaults={"assigned_classroom": classroom})
            if not created:
                teacher_profile.assigned_classroom = classroom
                teacher_profile.save()

            return redirect("classroom_detail", slug=classroom.slug)
    else:
        form = ClassroomForm()
    return render(request, "classroom_form.html", {"form": form})


@login_required
def send_invitation(request, slug):
    classroom = get_object_or_404(Classroom, slug=slug)
    if request.method == "POST":
        form = InvitationForm(request.POST, classroom=classroom)
        if form.is_valid():
            invitation = form.save()
            user_exists = Users.objects.filter(email=invitation.email).exists()
            if user_exists:
                invitation.send_invitation_email()
            else:
                invitation.register_first_enrolment()
            return redirect("classroom_detail", slug=classroom.slug)
    else:
        form = InvitationForm(classroom=classroom)
    return render(request, "send_invitation.html", {"form": form, "classroom": classroom})


def accept_invitation(request, token):
    invitation = get_object_or_404(Invitation, token=token, is_accepted=False)
    if request.user.is_authenticated and request.user.email == invitation.email:
        try:
            if invitation.register_first:
                return redirect("student_registration", token=invitation.token)
            invitation.accept(request.user)
            return redirect("classroom_detail", slug=invitation.classroom.slug)
        except ValueError as e:
            return HttpResponse(str(e), status=400)
    return HttpResponse("Unauthorized", status=401)


def student_registration(request, token):
    invitation = get_object_or_404(Invitation, token=token, enrolment_link_sent=True)

    if timezone.now() > invitation.enrolment_token_expiry:
        return HttpResponse("This registration link has expired.", status=400)

    if request.method == "POST":
        form = StudentRegistrationForm(request.POST, instance=Users(email=invitation.email, user_type="student"))
        if form.is_valid():
            user = form.save()
            login(request, user)
            invitation.accept(user)
            return redirect("classroom_detail", slug=invitation.classroom.slug)
    else:
        form = StudentRegistrationForm(initial={"email": invitation.email})

    return render(request, "student_registration.html", {"form": form})


@login_required
def teacher_dashboard(request):
    teacher_profile = get_object_or_404(Users, user_type="teacher", email=request.user.email)
    created_classrooms = Classroom.objects.filter(created_by=request.user)
    enrolled_classrooms = Classroom.objects.filter(teachers__user=request.user).distinct()
    other_classrooms = enrolled_classrooms.exclude(created_by=request.user)

    context = {
        "created_classrooms": created_classrooms,
        "enrolled_classrooms": enrolled_classrooms,
        "other_classrooms": other_classrooms,
    }
    print(context)
    return render(request, "dashboard/dashboard.html", context)


@login_required
def classroom_detail(request, slug):
    # Get the classroom based on the slug
    classroom = get_object_or_404(Classroom, slug=slug)

    # Check if the user is authorized to view the classroom
    user_profile = None
    if request.user.user_type == "teacher":
        user_profile = TeacherProfile.objects.filter(user=request.user).first()
    elif request.user.user_type == "student":
        user_profile = StudentProfile.objects.filter(user=request.user).first()

    if not user_profile or (user_profile.assigned_classroom != classroom and user_profile.enrolled_classroom != classroom):
        return HttpResponse("You are not authorized to view this classroom.", status=403)

    # Fetch related data
    students = classroom.students.all()
    co_teachers = classroom.teachers.exclude(user=request.user)
    lessons = Lesson.objects.filter(classroom=classroom).order_by("deadline")
    course_materials = CourseMaterial.objects.filter(classroom=classroom).order_by("uploaded_at")

    context = {
        "classroom": classroom,
        "students": students,
        "co_teachers": co_teachers,
        "lessons": lessons,
        "course_materials": course_materials,
    }

    return render(request, "classroom/classroom_detail.html", context)


@login_required
def lesson_detail(request, classroom_slug, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id, classroom__slug=classroom_slug)
    is_teacher = request.user.is_staff or request.user == lesson.classroom.created_by or lesson.classroom.co_teachers.filter(id=request.user.id).exists()

    context = {
        "lesson": lesson,
        "is_teacher": is_teacher,  # Pass the teacher check to the template
    }

    return render(request, "lesson/lesson_detail.html", context)


@login_required
def upload_material(request, slug):
    classroom = get_object_or_404(Classroom, slug=slug)
    if not request.user.is_staff and request.user != classroom.created_by:
        return HttpResponse("You do not have permission to upload materials to this classroom.", status=403)

    if request.method == "POST":
        form = CourseMaterialForm(request.POST, request.FILES, classroom=classroom)
        if form.is_valid():
            form.instance.uploaded_by = request.user  # Set the user who uploads the files
            form.save()
            return redirect("classroom_detail", slug=slug)
    else:
        form = CourseMaterialForm()

    return render(request, "upload_material.html", {"form": form, "classroom": classroom})


@login_required
def create_lesson(request, classroom_slug):
    classroom = get_object_or_404(Classroom, slug=classroom_slug)

    if request.method == "POST":
        form = LessonForm(request.POST, classroom=classroom)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.classroom = classroom
            lesson.created_by = request.user
            lesson.save()
            form.save_m2m()  # Save many-to-many relationships
            return redirect("classroom_detail", slug=classroom.slug)
    else:
        form = LessonForm(classroom=classroom)

    return render(request, "create_lesson.html", {"form": form, "classroom": classroom})


@login_required
def update_lesson(request, classroom_slug, lesson_id):
    classroom = get_object_or_404(Classroom, slug=classroom_slug)
    lesson = get_object_or_404(Lesson, id=lesson_id, classroom=classroom)

    if request.method == "POST":
        form = LessonForm(request.POST, instance=lesson, classroom=classroom)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.classroom = classroom
            lesson.created_by = request.user
            lesson.save()
            form.save_m2m()
            # return redirect("classroom_detail", slug=classroom.slug)
            return redirect("lesson_detail", classroom_slug=classroom.slug, lesson_id=lesson.id)
    else:
        form = LessonForm(instance=lesson, classroom=classroom)

    return render(request, "update_lesson.html", {"form": form, "classroom": classroom, "lesson": lesson})


@login_required
def classroom_content_management(request, classroom_slug):
    classroom = get_object_or_404(Classroom, slug=classroom_slug)

    if not request.user.is_staff and request.user != classroom.created_by:
        return HttpResponseForbidden("You do not have permission to manage content in this classroom.")

    course_materials = CourseMaterial.objects.filter(classroom=classroom)

    return render(
        request,
        "classroom_content_management.html",
        {
            "classroom": classroom,
            "course_materials": course_materials,
        },
    )


@login_required
def edit_course_material(request, classroom_slug, pk):
    material = get_object_or_404(CourseMaterial, pk=pk, classroom__slug=classroom_slug)

    if not request.user.is_staff and request.user != material.classroom.created_by:
        return HttpResponseForbidden("You do not have permission to edit this content.")

    if request.method == "POST":
        form = CourseMaterialForm(request.POST, request.FILES, instance=material)
        if form.is_valid():
            form.save()
            return redirect("classroom_content_management", classroom_slug=classroom_slug)
    else:
        form = CourseMaterialForm(instance=material)

    return render(request, "edit_course_material.html", {"form": form, "material": material})


@login_required
def delete_course_material(request, classroom_slug, pk):
    material = get_object_or_404(CourseMaterial, pk=pk, classroom__slug=classroom_slug)

    if not request.user.is_staff and request.user != material.classroom.created_by:
        return HttpResponseForbidden("You do not have permission to delete this content.")

    if request.method == "POST":
        material.delete()
        return redirect("classroom_content_management", classroom_slug=classroom_slug)

    return render(request, "confirm_delete.html", {"material": material})


@login_required
def add_question(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)

    if request.method == "POST":
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.lesson = lesson
            question.save()
            return redirect("lesson_detail", classroom_slug=lesson.classroom.slug, lesson_id=lesson.id)
    else:
        form = QuestionForm()

    return render(request, "add_question.html", {"form": form, "lesson": lesson})


@login_required
def edit_question(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    lesson = question.lesson

    if request.method == "POST":
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            return redirect("lesson_detail", classroom_slug=lesson.classroom.slug, lesson_id=lesson.id)
    else:
        form = QuestionForm(instance=question)

    return render(request, "edit_question.html", {"form": form, "lesson": lesson})


@login_required
def delete_question(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    lesson = question.lesson

    if request.method == "POST":
        question.delete()
        return redirect("lesson_detail", classroom_slug=lesson.classroom.slug, lesson_id=lesson.id)

    return render(request, "delete_question.html", {"question": question, "lesson": lesson})


# * ---------------------------------------------------------------------
def extract_text_from_txt(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        text = file.read()
    print(f"Extracted text from TXT file ({file_path}): {text[:100]}...")
    return text


def clean_extracted_text(text):
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    return text


def extract_text_from_pdf(file_path):
    parsed_pdf = parser.from_file(file_path)
    text = parsed_pdf["content"]

    clean_text = clean_extracted_text(text)

    print(f"Extracted text from PDF file ({file_path}): {clean_text[:100]}...")

    return clean_text


def describe_image(image_url):
    description = f"USE CONTEXT FROM REST OF THE CONTENTS"
    print(f"Describing image ({image_url}): {description}")
    return description


def collect_lesson_data(lesson):
    lesson_data = {"classroom": lesson.classroom.name, "lesson_title": lesson.title, "lesson_description": lesson.description, "lesson_objectives": lesson.objectives, "lesson_contents": []}

    print(
        f"Collecting data for Lesson: {lesson.title} (Classroom: {lesson.classroom.name})"
    )

    for material in lesson.course_materials.all():
        file_url = material.get_full_url()
        print(f"Processing file: {file_url}")

        if file_url.endswith(".txt"):
            text_content = extract_text_from_txt(material.file.path)
            lesson_data["lesson_contents"].append({"type": "text", "content": text_content})

        elif file_url.endswith(".pdf"):
            pdf_text = extract_text_from_pdf(material.file.path)
            lesson_data["lesson_contents"].append({"type": "text", "content": pdf_text})

        elif file_url.endswith((".jpg", ".jpeg", ".png", ".gif")):
            image_description = describe_image(file_url)
            lesson_data["lesson_contents"].append({"type": "image_description", "description": image_description})

    print(f"Collected lesson data: {lesson_data}")
    return lesson_data


def create_prompt_from_payload(payload):
    prompt = f"Generate {payload['question_count']} questions based on the following lesson content.\n\n"
    prompt += f"Classroom: {payload['classroom']}\n"
    prompt += f"Lesson Title: {payload['lesson_title']}\n"
    prompt += f"Description: {payload['lesson_description']}\n"
    prompt += f"Objectives: {payload['lesson_objectives']}\n"
    prompt += "Materials:\n"

    for content in payload["lesson_contents"]:
        if content["type"] == "text":
            prompt += f"{content['content']}\n"
        elif content["type"] == "image_description":
            prompt += f"Image: {content['description']}\n"

    prompt += "\nPlease format the questions in the following JSON structure:\n"
    prompt += """[
        {
            "question": "string",
            "type": "multiple_choice|true_false|short_answer|long_answer|fill_in_the_blank",
            "options": ["option1", "option2", "option3"],  # Only for multiple-choice
            "correct_answer": "string",  # Required for multiple-choice, true_false, and fill_in_the_blank
            "points": 1  # Optional, defaults to 1
        }
    ]\n"""

    print(f"Created prompt for OpenAI: {prompt[:800]}...")
    return prompt


def prepare_openai_payload(lesson_data, number_of_questions):
    payload = {
        "classroom": lesson_data["classroom"],
        "lesson_title": lesson_data["lesson_title"],
        "lesson_description": lesson_data["lesson_description"],
        "lesson_objectives": lesson_data["lesson_objectives"],
        "lesson_contents": lesson_data["lesson_contents"],
        "question_count": number_of_questions,
    }
    print(f"Prepared OpenAI payload: {json.dumps(payload, indent=2)}...")
    return payload


def send_openai_request(payload):
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that generates educational questions. and you strictly follow json structure that you have been given. You also make sure that you return a valid json",
        },
        {"role": "user", "content": create_prompt_from_payload(payload)},
    ]

    print("Sending request to OpenAI...")
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=4000,
        temperature=0.7,
    )

    print(f"Received response from OpenAI: {completion}")
    return completion


def store_generated_questions(lesson, response):
    print(
        f"Storing questions for Lesson: {lesson.title} (Classroom: {lesson.classroom.name})"
    )

    generated_questions_text = response.choices[0].message.content.strip("```json").strip("```")
    print(f"Generated questions text: {generated_questions_text}")

    try:
        generated_questions = json.loads(generated_questions_text)

        if not isinstance(generated_questions, list):
            generated_questions = [generated_questions]

        for question_data in generated_questions:
            question_text = question_data.get("question")
            question_type = question_data.get("type", "short_answer")  # Default to 'short_answer'
            choices = "\n".join(question_data.get("options", [])) if question_type == "multiple_choice" else None
            correct_answer = question_data.get("correct_answer")
            points = question_data.get("points", 1)  # Default to 1

            # Only create a Question if there's a question_text
            if question_text:
                Question.objects.create(lesson=lesson, question_text=question_text, question_type=question_type, choices=choices, correct_answer=correct_answer, points=points)

        print("Questions stored successfully.")

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")


# * ---------------------------------------------------------------------


@login_required
def process_ai_generation(request, classroom_slug, lesson_id, num_questions):
    lesson = get_object_or_404(Lesson, id=lesson_id, classroom__slug=classroom_slug)

    lesson_data = collect_lesson_data(lesson)

    payload = prepare_openai_payload(lesson_data, num_questions)

    response = send_openai_request(payload)

    store_generated_questions(lesson, response)

    return redirect("lesson_detail", classroom_slug=classroom_slug, lesson_id=lesson_id)


@login_required
def generate_ai_questions(request, classroom_slug, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id, classroom__slug=classroom_slug)

    if request.method == "POST":
        form = GenerateAIQuestionsForm(request.POST)
        if form.is_valid():
            number_of_questions = form.cleaned_data["number_of_questions"]
            return redirect("process_ai_generation", classroom_slug=classroom_slug, lesson_id=lesson_id, num_questions=number_of_questions)
    else:
        form = GenerateAIQuestionsForm()

    return render(request, "generate_ai_questions.html", {"form": form, "lesson": lesson})


@login_required
def create_exam(request, classroom_slug):
    classroom = get_object_or_404(Classroom, slug=classroom_slug)
    if request.method == "POST":
        form = ExamForm(request.POST, classroom=classroom)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.classroom = classroom
            exam.created_by = request.user
            exam.save()
            form.save_m2m()  
            return redirect('exam_detail', exam_id=exam.exam_id)
    else:
        form = ExamForm(classroom=classroom)
    return render(request, "exams/create_exam.html", {"form": form, "classroom": classroom})


@login_required
def exam_detail(request, exam_id):
    exam = get_object_or_404(Exam, exam_id=exam_id)

    window = exam.start_time.strftime("%d %b %Y %I:%M %p") + " — " + exam.end_time.strftime("%d %b %Y %I:%M %p")
    duration = exam.duration_minutes
    num_questions = exam.question_count
    total_points = 0
    for question in exam.get_questions():
        total_points += question.points
        
    context = { 'exam': exam, 'window': window, 'duration': duration, 'num_questions': num_questions, 'total_points': total_points }
    
    if not (exam.start_time <= timezone.now() <= exam.end_time):
        return HttpResponse(f"Exam is not within the valid time window. {exam.start_time} - {exam.end_time}", status=403)

    session = ExamSession.objects.filter(exam=exam, student=request.user).first()
    context['session'] = session

    if not session:
        if request.method == "POST":
            session = ExamSession.objects.create(exam=exam, student=request.user)
            return redirect(session.get_absolute_url())
    
    submission = ExamSubmission.objects.filter(exam_session=session, student=request.user)
    submitted = submission.exists()
    context['submitted'] = submitted
    context['submission'] = submission.first() if submitted else None
    # else:
    #     # If session exists, redirect to the session
    #     return redirect(session.get_absolute_url())

    return render(request, 'exams/exam_detail.html', context=context)


@login_required
def exam_session(request, session_token):
    session = get_object_or_404(ExamSession, session_token=session_token, student=request.user)

    timer = session.exam.duration_minutes * 60
    elapsed_time = (timezone.now() - session.started_at).seconds
    countdown = timer - elapsed_time

    if countdown <= 0 or session.completed_at:
        if not session.completed_at:
            session.completed_at = timezone.now()
            session.save()
        return render(request, 'exams/exam_completed.html', {'session': session})

    questions = session.exam.get_questions()

    return render(request, 'exams/exam_session.html', {
        'session': session,
        'questions': questions,
        'countdown': countdown
    })


@require_POST
def capture_image(request, session_token):
    session = get_object_or_404(ExamSession, session_token=session_token, student=request.user)
    data = json.loads(request.body)
    image_data = data.get("image")

    format, imgstr = image_data.split(";base64,")
    ext = format.split("/")[-1]
    image = ContentFile(
        base64.b64decode(imgstr),
        name=f"{session.student.id}_{session.exam.id}.{ext}",
    )

    WebcamCapture.objects.create(session=session, image=image)

    return JsonResponse({"status": "success"})


@require_POST
def log_focus_loss(request, session_token):
    session = get_object_or_404(ExamSession, session_token=session_token, student=request.user)
    FocusLossLog.objects.create(session=session)
    return JsonResponse({"status": "logged"})


@login_required
def exam_overview(request):
    user = request.user

    # Check if the user is a teacher
    is_teacher = user.user_type == "teacher" or user.is_staff

    # Get upcoming exams (exams that haven't ended yet)
    upcoming_exams = Exam.objects.filter(end_time__gt=timezone.now()).order_by("start_time")

    # Get previous exams (exams that have already ended)
    previous_exams = Exam.objects.filter(end_time__lte=timezone.now()).order_by("-start_time")

    context = {
        "is_teacher": is_teacher,
        "upcoming_exams": upcoming_exams,
        "previous_exams": previous_exams,
    }

    return render(request, "exam/exam_overview.html", context)


@login_required
def submit_exam(request, session_token):
    session = get_object_or_404(ExamSession, session_token=session_token, student=request.user)
    exam = session.exam

    if request.method == 'POST':
        form = ExamSubmissionForm(request.POST, exam=exam)
        if form.is_valid():
            submission, created = ExamSubmission.objects.update_or_create(
                exam_session=session,
                defaults={
                    'student': request.user,
                    'answers': {"questions": form.cleaned_data['answers']},
                    'status': 'new',
                }
            )
            session.completed_at = timezone.now()
            session.save()
            return redirect('exam_submission_success')
    else:
        form = ExamSubmissionForm(exam=exam)

    return render(request, 'exams/exam_session.html', {'form': form, 'session': session})    


@login_required
def grade_submission(request, submission_key):
    submission = get_object_or_404(ExamSubmission, submission_key=submission_key)

    if request.method == 'POST':
        form = GradingForm(request.POST, submission=submission)
        if form.is_valid():
            total_score = 0
            for answer in submission.answers['questions']:
                question_id = answer['question_id']
                max_score = answer['max_score']
                score = form.cleaned_data.get(f'score_{question_id}', 0)
                feedback = form.cleaned_data.get(f'feedback_{question_id}', '')

                answer['max_score'] = max_score
                answer['score'] = score
                answer['feedback'] = feedback
                total_score += score

            submission.answers['questions'] = submission.answers['questions']
            submission.total_score = total_score
            submission.status = 'graded'
            submission.save()

            return redirect('exam_overview')
    else:
        form = GradingForm(submission=submission)

    return render(request, 'exams/grade_submission.html', {'form': form, 'submission': submission})


@login_required
def exam_submission_success(request):
    return render(request, 'exams/exam_submission_success.html')


@login_required
def view_exam_response(request, submission_key):
    submission = get_object_or_404(ExamSubmission, submission_key=submission_key, exam_session__student=request.user)
    total_points = 0
    for question in submission.exam_session.exam.get_questions():
        total_points += question.points

    return render(request, 'exams/view_exam_response.html', {'submission': submission, 'total_points': total_points})


@login_required
def completed_exams(request):
    user = request.user

    # # Check if the user is a student
    # if user.user_type != "student":
    #     return render(request, "exam/completed_exams.html", {"error": "Only students can view their completed exams."})

    # Get completed exams for the user
    completed_exams = Exam.objects.filter(
        end_time__lte=timezone.now(),
        examsubmission__student=user
    ).distinct().order_by("-start_time")

    context = {
        "completed_exams": completed_exams,
    }

    return render(request, "exam/user_completed_exams.html", context)

@login_required
def exams_overview(request):
    user = request.user

    # Get completed exam submissions for the user
    completed_submissions = ExamSubmission.objects.filter(
        student=user,
        exam_session__end_time__lte=timezone.now()
    ).order_by('-exam_session__end_time')

    context = {
        'completed_submissions': completed_submissions,
        # Add other context variables if needed
    }

    return render(request, 'exam_overview.html', context)


