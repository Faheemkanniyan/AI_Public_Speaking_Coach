import os

from celery import Celery

# Tell Celery which Django settings file to use.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Create the Celery application.
app = Celery("config")

# Load Celery configuration from Django settings.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Automatically discover tasks.py files inside Django apps.
app.autodiscover_tasks()