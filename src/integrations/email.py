from django.core.mail import send_mail
from django.conf import settings


def send_mail_message(subject, message, send_to=[], fail_silently=False):
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, send_to, fail_silently)
