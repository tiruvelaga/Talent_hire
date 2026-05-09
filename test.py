r"""
Simple validation script for candidate active exams.

How to run:
    .\.venv\Scripts\python.exe test.py

Optional:
    .\.venv\Scripts\python.exe test.py TH-2024-003

If registration id is passed, script checks that candidate.
If not passed, script takes the first candidate from database.
"""

import os
import sys


# This line tells Python which Django settings file should be used.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "talent_hire.settings")


# Django setup must be called before importing models.
import django
django.setup()


from django.utils import timezone
from exam.models import Candidate, Exam, ExamAttempt


def get_candidate():
    """
    Get candidate for testing.
    If user gives registration id in command, use that candidate.
    Otherwise use first candidate from database.
    """
    if len(sys.argv) > 1:
        registration_id = sys.argv[1]
        return Candidate.objects.filter(registration_id=registration_id).first()

    return Candidate.objects.first()


def get_exam_button_status(candidate, exam):
    """
    This function checks if Start Exam button should be enabled or disabled.
    Same rules used in candidate dashboard cards.
    """
    now = timezone.now()
    attempt_count = ExamAttempt.objects.filter(candidate=candidate, exam=exam).count()

    if attempt_count >= exam.max_attempts:
        return "DISABLED", "Completed"

    if exam.start_time and now < exam.start_time:
        return "DISABLED", "Not Open Yet"

    if exam.end_time and now > exam.end_time:
        return "DISABLED", "Time Expired"

    return "ENABLED", "Start Exam"


def validate_latest_first(active_exams):
    """
    Dashboard should show latest active exams first.
    Here latest means bigger exam id first.
    """
    exam_ids = [exam.id for exam in active_exams]
    sorted_ids = sorted(exam_ids, reverse=True)

    if exam_ids == sorted_ids:
        print("PASS: Active exams are ordered latest first.")
    else:
        print("FAIL: Active exams are not ordered latest first.")
        print("Current order :", exam_ids)
        print("Expected order:", sorted_ids)


def validate_exam_buttons(candidate, active_exams):
    """
    Print button status for each active exam.
    This helps us manually check completed and expired exams.
    """
    print()
    print("Candidate:", candidate.name, "|", candidate.registration_id)
    print("Active exam button validation")
    print("-" * 70)

    for exam in active_exams:
        attempt_count = ExamAttempt.objects.filter(candidate=candidate, exam=exam).count()
        button_status, button_text = get_exam_button_status(candidate, exam)

        print("Exam ID       :", exam.id)
        print("Exam Name     :", exam.name)
        print("Attempts      :", str(attempt_count) + "/" + str(exam.max_attempts))
        print("Start Time    :", exam.start_time if exam.start_time else "Always open")
        print("End Time      :", exam.end_time if exam.end_time else "No end time")
        print("Button Status :", button_status)
        print("Button Text   :", button_text)
        print("-" * 70)


def main():
    """
    Main function.
    We keep all script steps here so file is easy to understand.
    """
    candidate = get_candidate()

    if not candidate:
        print("No candidate found. Please add a candidate first.")
        return

    active_exams = list(Exam.objects.filter(is_active=True).order_by("-id"))

    if not active_exams:
        print("No active exams found. Please activate or create an exam first.")
        return

    validate_latest_first(active_exams)
    validate_exam_buttons(candidate, active_exams)


if __name__ == "__main__":
    main()
