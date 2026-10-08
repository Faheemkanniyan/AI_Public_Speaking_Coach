from celery import shared_task

@shared_task
def sample_task():
    # Replace this with your actual background task logic
    return "Task executed successfully"
