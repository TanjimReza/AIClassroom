from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse

def send_verification_email(user):
    token = user.email_verification_token
    verification_link = f"{settings.SITE_URL}{reverse('verify-email', kwargs={'token': token})}"
    subject = 'Email Verification'
    message = f'Please verify your email by clicking the following link: {verification_link}'
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [user.email]
    send_mail(subject, message, from_email, recipient_list)
    
    return token

def send_enrollment_email(student_email, classroom_link, enrollment_code):
    subject = 'Classroom Enrollment'
    message = f'You have been invited to enroll in a classroom. Use the following link and code to enroll:\n\nLink: {classroom_link}\nCode: {enrollment_code}'
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [student_email]
    send_mail(subject, message, from_email, recipient_list)
