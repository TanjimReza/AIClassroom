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
from .models import Lesson, Classroom
from .models import Classroom
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

from .forms import ClassroomForm, CustomLoginForm, CustomPasswordResetForm, InvitationForm, StudentRegistrationForm
from .models import *


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
    return HttpResponse(f"Hello, world! {user} - {type}")


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
    teacher_profile = get_object_or_404(TeacherProfile, user=request.user)
    created_classrooms = Classroom.objects.filter(created_by=request.user)
    enrolled_classrooms = Classroom.objects.filter(teachers__user=request.user).distinct()
    other_classrooms = enrolled_classrooms.exclude(created_by=request.user)

    context = {
        "created_classrooms": created_classrooms,
        "enrolled_classrooms": enrolled_classrooms,
        "other_classrooms": other_classrooms,
    }
    print(context)
    return render(request, "teacher_dashboard.html", context)


@login_required
def classroom_detail(request, slug):
    classroom = get_object_or_404(Classroom, slug=slug)
    if not classroom.teachers.filter(user=request.user).exists() and not classroom.students.filter(user=request.user).exists():
        return HttpResponse("You are not authorized to view this classroom.", status=403)

    students = classroom.students.all()
    co_teachers = classroom.teachers.exclude(user=request.user)
    # Fetch all lessons associated with the classroom
    lessons = classroom.lessons.all()

    context = {
        "classroom": classroom,
        "students": students,
        "co_teachers": co_teachers,
        "lessons": lessons,  # Pass lessons to the template
    }

    return render(request, "classroom_detail.html", context)


@login_required
def lesson_detail(request, classroom_slug, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id, classroom__slug=classroom_slug)
    is_teacher = request.user.is_staff or request.user == lesson.classroom.created_by or lesson.classroom.co_teachers.filter(id=request.user.id).exists()

    context = {
        "lesson": lesson,
        "is_teacher": is_teacher,  # Pass the teacher check to the template
    }

    return render(request, "lesson_detail.html", context)


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
            form.save_m2m()  # Save many-to-many relationships
            # return redirect("classroom_detail", slug=classroom.slug)
            # redirect to the lesson detail page
            return redirect("lesson_detail", classroom_slug=classroom.slug, lesson_id=lesson.id)
    else:
        form = LessonForm(instance=lesson, classroom=classroom)

    return render(request, "update_lesson.html", {"form": form, "classroom": classroom, "lesson": lesson})


@login_required
def classroom_content_management(request, classroom_slug):
    classroom = get_object_or_404(Classroom, slug=classroom_slug)

    if not request.user.is_staff and request.user != classroom.created_by:
        # If the user is not authorized, return a 403 Forbidden response
        return HttpResponseForbidden("You do not have permission to manage content in this classroom.")

    # Retrieve all course materials associated with this classroom
    course_materials = CourseMaterial.objects.filter(classroom=classroom)

    # Render the management template
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
    # Remove excessive newlines and whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Optionally, remove non-ASCII characters (if they are causing issues)
    text = re.sub(r"[^\x00-\x7F]+", " ", text)

    return text


def extract_text_from_pdf(file_path):
    parsed_pdf = parser.from_file(file_path)
    text = parsed_pdf["content"]

    # Clean the extracted text
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
        f"Collecting data for Lesson: {
          lesson.title} (Classroom: {lesson.classroom.name})"
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

    # Specify the JSON format to be used in the response
    prompt += "\nPlease format the questions in the following JSON structure:\n"
    prompt += """[
        {
            "question": "string",
            "type": "multiple-choice|true_false|short_answer|long_answer|fill_in_the_blank",
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
    messages = [{"role": "system", "content": "You are a helpful assistant that generates educational questions."}, {"role": "user", "content": create_prompt_from_payload(payload)}]

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
    print(f"Storing questions for Lesson: {lesson.title} (Classroom: {lesson.classroom.name})")

    # Access the content of the first choice
    generated_questions_text = response.choices[0].message.content.strip("```json").strip("```")
    print(f"Generated questions text: {generated_questions_text}")

    try:
        # Parse the JSON from the generated text
        generated_questions = json.loads(generated_questions_text)

        # Ensure it's a list
        if not isinstance(generated_questions, list):
            generated_questions = [generated_questions]

        for question_data in generated_questions:
            question_text = question_data.get("question")
            question_type = question_data.get("type", "short_answer")  # Default to 'short_answer'
            choices = ", ".join(question_data.get("options", [])) if question_type == "multiple-choice" else None
            correct_answer = question_data.get("correct_answer")
            points = question_data.get("points", 1)  # Default to 1

            # Only create a Question if there's a question_text
            if question_text:
                Question.objects.create(lesson=lesson, question_text=question_text, question_type=question_type, choices=choices, correct_answer=correct_answer, points=points)

        print("Questions stored successfully.")

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        # Log error or notify the user as necessary


# * ---------------------------------------------------------------------


@login_required
def process_ai_generation(request, classroom_slug, lesson_id, num_questions):
    lesson = get_object_or_404(Lesson, id=lesson_id, classroom__slug=classroom_slug)

    # Collect lesson data
    lesson_data = collect_lesson_data(lesson)

    # Prepare payload for OpenAI
    payload = prepare_openai_payload(lesson_data, num_questions)

    # Send request to OpenAI and get the response
    response = send_openai_request(payload)

    # Parse the response and store the generated questions in the database
    store_generated_questions(lesson, response)

    # Redirect to lesson detail page
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
