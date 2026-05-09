"""
views.py - Talent Hire Exam Portal
"""
import time
import random
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.utils import timezone
import openpyxl
import pytz
from openpyxl.styles import Font, PatternFill, Alignment
from .models import Candidate, Question, ExamAttempt, Answer, ExamSetting, Category, Exam, Notification, SupportQuery, PendingRegistration
from .tasks import process_exam_submission


# ─── Notification helpers ─────────────────────────────────────────────
def _notify(candidate, title, message, category='info', link=''):
    """Create a single notification for a candidate."""
    return Notification.objects.create(
        candidate=candidate,
        title=title,
        message=message,
        category=category,
        link=link,
    )


def _notify_all(title, message, category='info', link=''):
    """Broadcast: create one Notification per candidate."""
    notifs = [
        Notification(candidate=c, title=title, message=message, category=category, link=link)
        for c in Candidate.objects.all()
    ]
    Notification.objects.bulk_create(notifs)


def _candidate_context(request):
    """Return dict with candidate + unread count for navbar (used by all candidate pages)."""
    candidate_id = request.session.get('candidate_id')
    if not candidate_id:
        return {}
    try:
        candidate = Candidate.objects.get(id=candidate_id)
    except Candidate.DoesNotExist:
        return {}
    unread = Notification.objects.filter(candidate=candidate, is_read=False).count()
    recent = Notification.objects.filter(candidate=candidate).order_by('-created_at')[:5]
    return {
        'nav_candidate': candidate,
        'nav_unread_count': unread,
        'nav_recent_notifications': recent,
    }


# ─── Helper: check admin access ────────────────────────────────────
def _discard_login_welcome_messages(request):
    """Remove stale candidate login welcome alerts while preserving other messages."""
    preserved = []
    for message in messages.get_messages(request):
        if not str(message).startswith("Welcome back,"):
            preserved.append(message)

    for message in preserved:
        messages.add_message(
            request,
            message.level,
            message.message,
            extra_tags=message.extra_tags,
        )


def _exam_question_pool_ids(exam):
    """Return exam-specific questions plus shared unassigned questions."""
    exam_ids = list(Question.objects.filter(exam=exam).values_list('id', flat=True))
    shared_ids = list(Question.objects.filter(exam__isnull=True).values_list('id', flat=True))
    return list(dict.fromkeys(exam_ids + shared_ids))


def _attach_candidate_exam_status(exams, candidate):
    """Add candidate-specific availability flags for exam cards."""
    exams = list(exams)
    now = timezone.now()
    for exam in exams:
        attempt_count = ExamAttempt.objects.filter(candidate=candidate, exam=exam).count()
        exam.attempt_count = attempt_count
        exam.can_start = True
        exam.start_disabled_label = ''
        exam.start_disabled_reason = ''

        if attempt_count >= exam.max_attempts:
            exam.can_start = False
            exam.start_disabled_label = 'Completed'
            exam.start_disabled_reason = 'You have used all available attempts for this exam.'
        elif exam.start_time and now < exam.start_time:
            exam.can_start = False
            exam.start_disabled_label = 'Not Open Yet'
            exam.start_disabled_reason = 'This exam has not started yet.'
        elif exam.end_time and now > exam.end_time:
            exam.can_start = False
            exam.start_disabled_label = 'Time Expired'
            exam.start_disabled_reason = 'The exam window has ended.'
    return exams


def _candidate_visible_active_exams(candidate):
    """Active exams visible to this candidate. Empty assignment means open to all."""
    return Exam.objects.filter(
        Q(assigned_candidates__isnull=True) | Q(assigned_candidates=candidate),
        is_active=True,
    ).distinct()


import functools

def admin_required(view_func):
    """Simple decorator — must be logged in as staff to access admin portal."""
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.is_staff):
            return redirect('admin_login')
        return view_func(request, *args, **kwargs)
    return wrapper


# ═══════════════════════════════════════════════════════════════════
# CANDIDATE VIEWS
# ═══════════════════════════════════════════════════════════════════

def home_view(request):
    """Landing page with Admin Portal + Candidate Login cards."""
    if request.session.get('candidate_id'):
        return redirect('candidate_dashboard')
    return render(request, 'exam/home.html')


def login_view(request):
    """Candidate login using Registration ID and Password."""
    if request.session.get('candidate_id'):
        return redirect('candidate_dashboard')

    if request.method == 'POST':
        registration_id = request.POST.get('registration_id', '').strip()
        password        = request.POST.get('password', '').strip()

        if not registration_id or not password:
            messages.error(request, "Please fill in both Registration ID and Password.")
            return render(request, 'exam/login.html')

        try:
            candidate = Candidate.objects.get(registration_id=registration_id)
            
                
            if check_password(password, candidate.password):
                request.session['candidate_id']   = candidate.id
                request.session['candidate_name'] = candidate.name
                return redirect('candidate_dashboard')
            else:
                messages.error(request, "Invalid password. Please try again.")

        except Candidate.DoesNotExist:
            messages.error(request, "Invalid Registration ID. Please check and try again.")

    return render(request, 'exam/login.html')


def change_password_view(request):
    """Allow logged-in candidates to change their password."""
    candidate_id = request.session.get('candidate_id')
    if not candidate_id:
        return redirect('login')

    candidate = get_object_or_404(Candidate, id=candidate_id)

    if request.method == 'POST':
        password     = request.POST.get('password', '').strip()
        confirm      = request.POST.get('confirm_password', '').strip()

        if not password or len(password) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
        elif password != confirm:
            messages.error(request, "Passwords do not match.")
        else:
            candidate.password = make_password(password)
            candidate.save()
            messages.success(request, "Password updated successfully!")
            return redirect('candidate_dashboard')

    return render(request, 'exam/change_password.html', {
        'candidate_name': candidate.name
    })


def exam_view(request, exam_id):
    """Shows the exam for a specific exam_id."""
    candidate_id = request.session.get('candidate_id')
    if not candidate_id:
        messages.error(request, "Please login to start the exam.")
        return redirect('login')

    try:
        candidate = Candidate.objects.get(id=candidate_id)
    except Candidate.DoesNotExist:
        return redirect('login')

    # Get specific exam settings
    exam = get_object_or_404(Exam, id=exam_id, is_active=True)
    
    # Check if exam is open
    from django.utils import timezone
    now = timezone.now()
    if exam.start_time and now < exam.start_time:
        msg = f'Exam will start at {exam.start_time.strftime("%d %b %Y, %I:%M %p")}. '
        return render(request, 'exam/error.html', {'message': msg})
    if exam.end_time and now > exam.end_time:
        return render(request, 'exam/error.html', {'message': 'Exam has ended.'})

    # Show result instead of allowing start again after all attempts are used.
    if ExamAttempt.objects.filter(candidate=candidate, exam=exam).count() >= exam.max_attempts:
        attempt = ExamAttempt.objects.filter(candidate=candidate, exam=exam).latest('date_taken')
        return redirect('result', attempt_id=attempt.id)

    # Try to get question IDs from session for this specific exam
    session_key = f'question_ids_{exam_id}'
    question_ids = request.session.get(session_key)
    
    if not question_ids:
        all_ids = _exam_question_pool_ids(exam)
        if not all_ids:
            return render(request, 'exam/error.html', {
                'message': 'No questions are available for this exam. Please contact admin.'
            })
        question_count = min(exam.total_questions, len(all_ids))
        question_ids = random.sample(all_ids, question_count)
        request.session[session_key] = question_ids

    # Store start time once for this specific exam
    start_time_key = f'exam_start_time_{exam_id}'
    if start_time_key not in request.session:
        request.session[start_time_key] = int(time.time())

    questions_qs      = Question.objects.filter(id__in=question_ids)
    questions_ordered = sorted(questions_qs, key=lambda q: question_ids.index(q.id))

    elapsed        = int(time.time()) - request.session[start_time_key]
    remaining_secs = max(0, exam.duration_minutes * 60 - elapsed)

    context = {
        'exam'           : exam,
        'questions'      : questions_ordered,
        'candidate_name' : request.session.get('candidate_name'),
        'total_questions': len(question_ids),
        'remaining_secs' : remaining_secs,
    }
    return render(request, 'exam/exam.html', context)


def submit_exam(request, exam_id):
    """Process exam submission for a specific exam."""
    if request.method != 'POST':
        return redirect('exam', exam_id=exam_id)

    candidate_id = request.session.get('candidate_id')
    if not candidate_id:
        return redirect('login')

    try:
        candidate = Candidate.objects.get(id=candidate_id)
        exam = Exam.objects.get(id=exam_id)
    except (Candidate.DoesNotExist, Exam.DoesNotExist):
        return redirect('login')

    # Prevent submissions after the candidate has used all attempts for this exam.
    existing_attempts = ExamAttempt.objects.filter(candidate=candidate, exam=exam)
    if existing_attempts.count() >= exam.max_attempts:
        attempt = existing_attempts.latest('date_taken')
        return redirect('result', attempt_id=attempt.id)

    session_key = f'question_ids_{exam_id}'
    question_ids = request.session.get(session_key, [])
    if not question_ids:
        return redirect('exam', exam_id=exam_id)

    # Calculate score and save answers (using correct form field names from exam.html)
    score = 0
    total = len(question_ids)
    for q_id in question_ids:
        question = Question.objects.get(id=q_id)
        selected = request.POST.get(f'q_{q_id}', '').strip().upper()
        if selected and selected == question.correct_answer:
            score += 1
    
    percentage = (score / total) * 100 if total > 0 else 0
    status = "Selected" if percentage >= exam.min_selection_score else "Not Selected"
    
    attempt = ExamAttempt.objects.create(
        candidate=candidate,
        exam=exam,
        score=score,
        total=total,
        percentage=round(percentage, 2),
        status=status,
        is_published=exam.results_published
    )
    
    # Save answers
    for q_id in question_ids:
        question = Question.objects.get(id=q_id)
        selected = request.POST.get(f'q_{q_id}', '').strip().upper() or None
        Answer.objects.create(
            attempt=attempt,
            question=question,
            selected_answer=selected,
            is_correct=bool(selected and selected == question.correct_answer)
        )

    # Clear exam session keys
    request.session.pop(session_key, None)
    request.session.pop(f'exam_start_time_{exam_id}', None)

    return redirect('result', attempt_id=attempt.id)


def result_view(request, attempt_id):
    """Show exam result. Handles 'Processing' state for async submissions."""
    candidate_id = request.session.get('candidate_id')
    if not candidate_id:
        return redirect('login')

    # If attempt_id is 0, we look for the latest attempt for this candidate
    if attempt_id == 0:
        attempt = ExamAttempt.objects.filter(candidate__id=candidate_id).order_by('-date_taken').first()
        if not attempt:
            # If no attempt yet, and submission is in progress, show processing page
            if request.session.get('submission_in_progress'):
                return render(request, 'exam/processing.html', {
                    'candidate_name': request.session.get('candidate_name')
                })
            return redirect('candidate_dashboard')
        # If found, redirect to the actual attempt URL
        return redirect('result', attempt_id=attempt.id)

    try:
        attempt = ExamAttempt.objects.get(id=attempt_id, candidate__id=candidate_id)
    except ExamAttempt.DoesNotExist:
        return redirect('login')

    # If result is held, show error or held message
    if not attempt.is_published:
        return render(request, 'exam/error.html', {
            'message': 'Your result has been held by the administrator. Please contact support for more details.'
        })

    # Clear progress flag if it exists
    request.session.pop('submission_in_progress', None)

    candidate = attempt.candidate
    answers = Answer.objects.filter(attempt=attempt).select_related('question')

    # Prepare breakdown data to match result.html template expectations
    # This ensures answers (including correct ones) are visible when admin enables show_answers/results_published
    breakdown = []
    for ans in answers:
        q = ans.question
        selected = ans.selected_answer
        if selected:
            option_field = f'option_{selected.lower()}'
            user_answer_text = getattr(q, option_field, selected)
        else:
            user_answer_text = "Not Answered"
        breakdown.append({
            'question': {'text': q.question_text},
            'user_answer_text': user_answer_text,
            'correct_answer_text': q.get_correct_answer_text,
            'is_correct': ans.is_correct,
        })

    wrong_count = sum(1 for b in breakdown if not b['is_correct'] and b.get('user_answer_text') != "Not Answered")
    skipped_count = sum(1 for b in breakdown if b.get('user_answer_text') == "Not Answered")

    context = {
        'attempt'        : attempt,
        'candidate'      : candidate,
        'breakdown'      : breakdown,
        'answers'        : answers,
        'candidate_name' : request.session.get('candidate_name'),
        'wrong_count'    : wrong_count,
        'skipped_count'  : skipped_count,
        'show_answers'   : getattr(attempt.exam, 'show_answers', True) if attempt.exam else True,
    }
    return render(request, 'exam/result.html', context)


def candidate_results_view(request):
    """Show all exam attempts and results for the logged-in candidate."""
    candidate_id = request.session.get('candidate_id')
    if not candidate_id:
        return redirect('login')

    try:
        candidate = Candidate.objects.get(id=candidate_id)
    except Candidate.DoesNotExist:
        return redirect('login')

    # Get all attempts for this candidate, ordered by most recent first
    attempts = ExamAttempt.objects.filter(candidate=candidate).select_related('exam').order_by('-date_taken')

    context = {
        'candidate_name': request.session.get('candidate_name'),
        'attempts': attempts,
    }
    return render(request, 'exam/candidate_results.html', context)


def logout_view(request):
    """Log out candidate and go home."""
    request.session.flush()
    return redirect('home')


# ═══════════════════════════════════════════════════════════════════
# ADMIN PORTAL VIEWS
# ═══════════════════════════════════════════════════════════════════

def admin_login_view(request):
    """Admin portal login with username + password."""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        user     = authenticate(request, username=username, password=password)
        if user and user.is_staff:
            login(request, user)
            return redirect('admin_dashboard')
        else:
            messages.error(request, "Invalid username / password. Only admin staff can login here.")

    return render(request, 'exam/admin_login.html')


def admin_logout_view(request):
    """Log out admin and redirect to admin login."""
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('admin_login')


@admin_required
def admin_dashboard_view(request):
    """Admin dashboard — clean modern layout matching the reference design."""
    from django.db.models import Count
    from django.utils import timezone
    now = timezone.now()
    # Newest exams first for dashboard cards.
    exams = list(Exam.objects.all().order_by('-id'))

    # KPI numbers
    total_candidates = Candidate.objects.count()
    total_questions = Question.objects.count()
    selected_count = ExamAttempt.objects.filter(status='Selected').count()
    not_selected = ExamAttempt.objects.filter(status='Not Selected').count()
    subject_count = 0

    # Subject/Exam Distribution (based on actual questions assigned per exam)
    exam_question_counts = list(
        Exam.objects.annotate(q_count=Count('questions')).filter(q_count__gt=0).order_by('-q_count', 'name')
    )
    unassigned_q_count = Question.objects.filter(exam__isnull=True).count()
    total_cat_questions = sum(e.q_count for e in exam_question_counts) + unassigned_q_count
    total_cat_questions = total_cat_questions or 1
    category_stats = []
    colors = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#06b6d4']
    for i, exam_obj in enumerate(exam_question_counts):
        pct = round((exam_obj.q_count / total_cat_questions) * 100)
        category_stats.append({
            'name': exam_obj.name,
            'count': exam_obj.q_count,
            'percent': pct,
            'color': colors[i % len(colors)],
        })
    if unassigned_q_count:
        pct = round((unassigned_q_count / total_cat_questions) * 100)
        category_stats.append({
            'name': 'Unassigned',
            'count': unassigned_q_count,
            'percent': pct,
            'color': colors[len(category_stats) % len(colors)],
        })
    subject_count = len(category_stats)
    avg_per_subject = round(total_cat_questions / subject_count, 1) if subject_count else 0

    # Scheduled Exams cards
    exam_list = []
    for idx, exam in enumerate(exams):
        registered = exam.assigned_candidates.count() or total_candidates
        attempted = exam.attempts.count()  # all attempts are considered attempted after submit
        selected = exam.attempts.filter(status='Selected').count()

        # Determine status
        if exam.start_time and exam.start_time > now:
            status = 'Upcoming'
            status_class = 'bg-light-blue'
        elif exam.end_time and exam.end_time < now:
            status = 'Completed'
            status_class = 'bg-light-green'
        else:
            status = 'Active'
            status_class = 'bg-light-purple'

        subjects = list(exam.subjects.values_list('name', flat=True)[:3])
        if not subjects:
            subjects = ['General']

        # Date range string
        date_str = ""
        if exam.start_time and exam.end_time:
            date_str = f"{exam.start_time.strftime('%Y-%m-%d')} — {exam.end_time.strftime('%Y-%m-%d')}"
        elif exam.start_time:
            date_str = exam.start_time.strftime('%Y-%m-%d')

        # Duration string
        dur = f"{exam.duration_minutes} min"
        if exam.total_questions:
            dur += f" • {exam.total_questions} Qs"

        exam_list.append({
            'id': exam.id,
            'name': exam.name,
            'code': f"TH-2025-{exam.id:03d}",
            'subjects': subjects,
            'registered': registered,
            'attempted': attempted,
            'selected': selected,
            'date_str': date_str,
            'duration': dur,
            'status': status,
            'status_class': status_class,
            'is_active': exam.is_active,
        })

    recent_attempts = list(
        ExamAttempt.objects.select_related('candidate', 'exam').order_by('-date_taken')[:8]
    )
    total_attempts = ExamAttempt.objects.count()
    selection_rate = round((selected_count / total_attempts) * 100, 1) if total_attempts else 0

    context = {
        'total_exams': len(exams),
        'active_exams': sum(1 for e in exams if e.is_active),
        'total_candidates': total_candidates,
        'selected_count': selected_count,
        'not_selected': not_selected,
        'subject_count': subject_count,
        'exam_list': exam_list,
        'category_stats': category_stats,
        'total_questions': total_questions,
        'avg_per_subject': avg_per_subject,
        'recent_attempts': recent_attempts,
        'total_attempts': total_attempts,
        'selection_rate': selection_rate,
        'exams': Exam.objects.all().order_by('name'),
    }

    return render(request, 'exam/admin_dashboard.html', context)


# ── Candidates CRUD ─────────────────────────────────────────────────

@admin_required
def admin_candidates_view(request):
    """List all candidates."""
    candidates = Candidate.objects.all().order_by('name')
    return render(request, 'exam/admin_candidates.html', {'candidates': candidates})


@admin_required
def admin_add_candidate(request):
    """Add a new candidate."""
    if request.method == 'POST':
        name            = request.POST.get('name', '').strip()
        mobile          = request.POST.get('mobile', '').strip()
        registration_id = request.POST.get('registration_id', '').strip()
        next_page       = request.POST.get('next', '')

        if not (name and mobile and registration_id):
            messages.error(request, "All fields are required.")
        elif Candidate.objects.filter(registration_id=registration_id).exists():
            messages.error(request, "Registration ID already exists.")
        else:
            Candidate.objects.create(name=name, mobile=mobile, registration_id=registration_id)
            messages.success(request, f"Candidate '{name}' added successfully.")
            if next_page == 'dashboard':
                return redirect('admin_dashboard')
            return redirect('admin_candidates')

        if next_page == 'dashboard':
            return redirect(f"{reverse('admin_dashboard')}?modal=candidate")

    return render(request, 'exam/admin_candidate_form.html', {'action': 'Add'})


@admin_required
def admin_edit_candidate(request, pk):
    """Edit an existing candidate."""
    candidate = get_object_or_404(Candidate, pk=pk)

    if request.method == 'POST':
        candidate.name            = request.POST.get('name', '').strip()
        candidate.mobile          = request.POST.get('mobile', '').strip()
        candidate.registration_id = request.POST.get('registration_id', '').strip()
        candidate.save()
        messages.success(request, "Candidate updated successfully.")
        return redirect('admin_candidates')

    return render(request, 'exam/admin_candidate_form.html', {'action': 'Edit', 'candidate': candidate})


@admin_required
def admin_delete_candidate(request, pk):
    """Delete a candidate (with confirmation)."""
    candidate = get_object_or_404(Candidate, pk=pk)

    if request.method == 'POST':
        name = candidate.name
        candidate.delete()
        messages.success(request, f"Candidate '{name}' deleted.")
        return redirect('admin_candidates')

    return render(request, 'exam/admin_confirm_delete.html', {
        'object_name': candidate.name,
        'object_type': 'Candidate',
        'cancel_url' : 'admin_candidates',
    })


@admin_required
def admin_bulk_delete_candidates(request):
    """Delete multiple candidates by id list (POST 'ids')."""
    if request.method == 'POST':
        ids = request.POST.getlist('ids')
        if ids:
            count, _ = Candidate.objects.filter(id__in=ids).delete()
            messages.success(request, f"Deleted {count} candidate(s).")
        else:
            messages.warning(request, "No candidates selected.")
    return redirect('admin_candidates')


@admin_required
def admin_bulk_import_candidates(request):
    """Import candidates from CSV or Excel file."""
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        skip_duplicates = request.POST.get('skip_duplicates') == 'on'
        
        try:
            if file.name.endswith('.csv'):
                import csv
                import io
                decoded_file = file.read().decode('utf-8')
                io_string = io.StringIO(decoded_file)
                reader = csv.reader(io_string)
                next(reader, None) # Skip header
                data = list(reader)
            else:
                # Excel
                wb = openpyxl.load_workbook(file)
                ws = wb.active
                data = list(ws.iter_rows(min_row=2, values_only=True))

            count = 0
            errors = 0
            for row in data:
                if not row or len(row) < 3: continue
                name, mobile, reg_id = row[0], row[1], row[2]
                
                if Candidate.objects.filter(registration_id=reg_id).exists():
                    if skip_duplicates: continue
                    errors += 1
                    continue
                
                Candidate.objects.create(
                    name=name,
                    mobile=mobile,
                    registration_id=reg_id
                )
                count += 1
            
            if count > 0:
                messages.success(request, f"Successfully imported {count} candidates.")
            if errors > 0:
                messages.warning(request, f"Skipped {errors} duplicate registration IDs.")
                
        except Exception as e:
            messages.error(request, f"Error importing file: {str(e)}")

    return redirect('admin_candidates')


@admin_required
def admin_bulk_import_questions(request):
    """Import questions from CSV or Excel file. Optionally scoped to an exam."""
    redirect_target = request.POST.get('redirect_to') or 'admin_questions'

    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        replace_existing = request.POST.get('replace_existing') == 'on'
        target_exam = None
        target_exam_id = request.POST.get('exam_id')
        if target_exam_id:
            try:
                target_exam = Exam.objects.get(id=target_exam_id)
            except Exam.DoesNotExist:
                target_exam = None

        try:
            if replace_existing:
                if target_exam:
                    Question.objects.filter(exam=target_exam).delete()
                else:
                    Question.objects.all().delete()

            if file.name.endswith('.csv'):
                import csv
                import io
                decoded_file = file.read().decode('utf-8')
                io_string = io.StringIO(decoded_file)
                reader = csv.reader(io_string)
                next(reader, None)  # Skip header
                data = list(reader)
            else:
                wb = openpyxl.load_workbook(file)
                ws = wb.active
                data = list(ws.iter_rows(min_row=2, values_only=True))

            count = 0
            for row in data:
                if not row or len(row) < 6:
                    continue
                # Format: Question, OptionA, OptionB, OptionC, OptionD, Answer
                qt, oa, ob, oc, od, ca = row[0], row[1], row[2], row[3], row[4], row[5]
                Question.objects.create(
                    question_text=qt,
                    option_a=oa, option_b=ob, option_c=oc, option_d=od,
                    correct_answer=str(ca).strip().upper(),
                    exam=target_exam,
                )
                count += 1

            scope = f" into exam '{target_exam.name}'" if target_exam else ""
            messages.success(request, f"Successfully imported {count} questions{scope}.")

        except Exception as e:
            messages.error(request, f"Error importing file: {str(e)}")

    if redirect_target == 'admin_exam_detail' and request.POST.get('exam_id'):
        return redirect('admin_exam_detail', pk=request.POST.get('exam_id'))
    return redirect(redirect_target)


@admin_required
def admin_bulk_delete_questions(request):
    """Delete multiple questions by id list. Returns to questions list or exam detail."""
    if request.method == 'POST':
        ids = request.POST.getlist('ids')
        if ids:
            count, _ = Question.objects.filter(id__in=ids).delete()
            messages.success(request, f"Deleted {count} question(s).")
        else:
            messages.warning(request, "No questions selected.")
    nxt_exam = request.POST.get('exam_id')
    if nxt_exam:
        return redirect('admin_exam_detail', pk=nxt_exam)
    return redirect('admin_questions')


# ── Questions CRUD ──────────────────────────────────────────────────

@admin_required
def admin_questions_view(request):
    """List all questions."""
    questions = Question.objects.all().order_by('id')
    exams = Exam.objects.all().order_by('name')
    return render(request, 'exam/admin_questions.html', {'questions': questions, 'exams': exams})


@admin_required
def admin_add_question(request):
    """Add a new question."""
    if request.method == 'POST':
        qt = request.POST.get('question_text', '').strip()
        oa = request.POST.get('option_a', '').strip()
        ob = request.POST.get('option_b', '').strip()
        oc = request.POST.get('option_c', '').strip()
        od = request.POST.get('option_d', '').strip()
        ca = request.POST.get('correct_answer', '').strip().upper()
        exam_id = request.POST.get('exam_id')
        next_page = request.POST.get('next', '')

        if not all([qt, oa, ob, oc, od, ca]):
            messages.error(request, "All fields are required.")
        elif ca not in ['A', 'B', 'C', 'D']:
            messages.error(request, "Correct answer must be A, B, C, or D.")
        else:
            exam = None
            if exam_id:
                exam = get_object_or_404(Exam, id=exam_id)
            Question.objects.create(
                question_text=qt, option_a=oa, option_b=ob,
                option_c=oc, option_d=od, correct_answer=ca,
                exam=exam
            )
            messages.success(request, "Question added successfully.")
            if next_page == 'dashboard':
                return redirect('admin_dashboard')
            return redirect('admin_questions')

        if next_page == 'dashboard':
            return redirect(f"{reverse('admin_dashboard')}?modal=question")

    return render(request, 'exam/admin_question_form.html', {
        'action': 'Add',
        'exams': Exam.objects.all().order_by('name')
    })


@admin_required
def admin_edit_question(request, pk):
    """Edit an existing question."""
    question = get_object_or_404(Question, pk=pk)

    if request.method == 'POST':
        question.question_text  = request.POST.get('question_text', '').strip()
        question.option_a       = request.POST.get('option_a', '').strip()
        question.option_b       = request.POST.get('option_b', '').strip()
        question.option_c       = request.POST.get('option_c', '').strip()
        question.option_d       = request.POST.get('option_d', '').strip()
        question.correct_answer = request.POST.get('correct_answer', '').strip().upper()
        
        exam_id = request.POST.get('exam_id')
        if exam_id:
            question.exam = get_object_or_404(Exam, id=exam_id)
        else:
            question.exam = None
            
        question.save()
        messages.success(request, "Question updated successfully.")
        return redirect('admin_questions')

    return render(request, 'exam/admin_question_form.html', {
        'action': 'Edit', 
        'question': question,
        'exams': Exam.objects.all().order_by('name')
    })


@admin_required
def admin_delete_question(request, pk):
    """Delete a question (with confirmation)."""
    question = get_object_or_404(Question, pk=pk)

    if request.method == 'POST':
        question.delete()
        messages.success(request, "Question deleted.")
        return redirect('admin_questions')

    return render(request, 'exam/admin_confirm_delete.html', {
        'object_name': question.question_text[:60] + '...',
        'object_type': 'Question',
        'cancel_url' : 'admin_questions',
    })


# ── Results ─────────────────────────────────────────────────────────

@admin_required
def admin_results_view(request):
    """View all exam results with optional status filter from dashboard (now filters table + export)."""
    current_filter = request.GET.get('filter', '').lower().strip()
    attempts_qs = ExamAttempt.objects.select_related('candidate').all().order_by('-date_taken')

    # Filter for table/export (stats remain overall)
    if current_filter == 'selected':
        attempts = attempts_qs.filter(status='Selected')
    elif current_filter in ['not-selected', 'not_selected', 'unselected']:
        attempts = attempts_qs.filter(status='Not Selected')
    else:
        attempts = attempts_qs

    # Calculate stats (overall, not affected by filter)
    total_attempts = attempts_qs.count()
    selected_count = attempts_qs.filter(status='Selected').count()
    not_selected = total_attempts - selected_count

    # Calculate average score
    avg_score = 0
    if total_attempts > 0:
        from django.db.models import Avg
        avg_data = ExamAttempt.objects.aggregate(avg_percentage=Avg('percentage'))
        avg_score = avg_data['avg_percentage'] or 0

    context = {
        'attempts': attempts,
        'total_attempts': total_attempts,
        'selected_count': selected_count,
        'not_selected': not_selected,
        'avg_score': round(avg_score, 1),
        'current_filter': current_filter,
    }
    return render(request, 'exam/admin_results.html', context)


@admin_required
def admin_queries_view(request, pk=None):
    """Admin query/ticket management with list, status filter from cards, search/sort options."""
    status_filter = request.GET.get('status', '').strip()
    sort_param = request.GET.get('sort', 'newest')

    # Active detail always from full set (independent of list filter)
    all_queries = SupportQuery.objects.select_related('candidate')
    active_query = None
    if pk:
        active_query = all_queries.filter(pk=pk).first()
    if not active_query and all_queries.exists():
        active_query = all_queries.first()

    # Filtered and sorted list for sidebar
    queries = all_queries.order_by('-created_at')
    if status_filter in ['Open', 'Answered', 'Closed']:
        queries = queries.filter(status=status_filter)
    if sort_param == 'oldest':
        queries = queries.order_by('created_at')
    elif sort_param == 'name':
        queries = queries.order_by('candidate__name', '-created_at')
    elif sort_param == 'status':
        queries = queries.order_by('status', '-created_at')
    # default: newest

    if request.method == 'POST' and active_query:
        action = request.POST.get('action')
        if action == 'reply':
            response = request.POST.get('admin_response', '').strip()
            if response:
                active_query.admin_response = response
                active_query.status = 'Answered'
                active_query.responded_at = timezone.now()
                active_query.save()
                _notify(
                    active_query.candidate,
                    'Support query answered',
                    f'Admin replied to "{active_query.subject}".',
                    category='support',
                    link=reverse('help_support'),
                )
                messages.success(request, "Reply sent to candidate.")
            else:
                messages.error(request, "Reply cannot be empty.")
        elif action in ['Open', 'Answered', 'Closed']:
            active_query.status = action
            if action == 'Answered' and not active_query.responded_at:
                active_query.responded_at = timezone.now()
            active_query.save()
            messages.success(request, f"Ticket marked as {action}.")
        return redirect('admin_query_detail', pk=active_query.pk)

    context = {
        'queries': queries,
        'active_query': active_query,
        'open_count': SupportQuery.objects.filter(status='Open').count(),
        'answered_count': SupportQuery.objects.filter(status='Answered').count(),
        'closed_count': SupportQuery.objects.filter(status='Closed').count(),
        'current_status': status_filter,
        'current_sort': sort_param,
    }
    return render(request, 'exam/admin_queries.html', context)


@admin_required
def admin_publish_all_results(request):
    """Set is_published=True for all exam attempts and notify each candidate."""
    pending = ExamAttempt.objects.filter(is_published=False).select_related('candidate', 'exam')
    notif_rows = []
    for att in pending:
        exam_name = att.exam.name if att.exam else 'your exam'
        notif_rows.append(Notification(
            candidate=att.candidate,
            title=f"Results published: {exam_name}",
            message=f"Your result for {exam_name} is now available. You scored {att.score}/{att.total} ({att.percentage}%) — {att.status}.",
            category='results',
            link=f"/result/{att.id}/",
        ))
    Notification.objects.bulk_create(notif_rows)
    pending.update(is_published=True)
    messages.success(request, f"All exam results have been published. {len(notif_rows)} candidates notified.")
    return redirect('admin_results')


@admin_required
def admin_hold_all_results(request):
    """Set is_published=False for all exam attempts."""
    ExamAttempt.objects.all().update(is_published=False)
    messages.success(request, "All exam results have been held (unpublished).")
    return redirect('admin_results')


@admin_required
def admin_toggle_result_publish(request, pk):
    """Toggle is_published status for a specific exam attempt."""
    attempt = get_object_or_404(ExamAttempt, pk=pk)
    attempt.is_published = not attempt.is_published
    attempt.save()

    status = "published" if attempt.is_published else "held"
    if attempt.is_published:
        exam_name = attempt.exam.name if attempt.exam else 'your exam'
        _notify(
            attempt.candidate,
            title=f"Result published: {exam_name}",
            message=f"Your result is now available. You scored {attempt.score}/{attempt.total} ({attempt.percentage}%) — {attempt.status}.",
            category='results',
            link=f"/result/{attempt.id}/",
        )
    messages.success(request, f"Result for {attempt.candidate.name} is now {status}.")
    return redirect('admin_results')


# ── Excel Export ────────────────────────────────────────────────────

@admin_required
def export_results(request):
    """Download results as Excel (respects selected/unselected filter from results page)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Exam Results"

    headers      = ['S.No', 'Candidate Name', 'Mobile', 'Registration ID',
                    'Score', 'Total', 'Percentage', 'Status', 'Date Taken']
    header_fill  = PatternFill(start_color="E65C00", end_color="E65C00", fill_type="solid")
    header_font  = Font(color="FFFFFF", bold=True, size=11)
    center_align = Alignment(horizontal="center", vertical="center")

    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_align
    ws.row_dimensions[1].height = 25

    # Respect ?filter=selected or not-selected from results page (exact match to dropdown + JS link)
    current_filter = (request.GET.get('filter') or request.GET.get('status') or '').lower().strip()
    attempts_qs = ExamAttempt.objects.select_related('candidate').all().order_by('-date_taken')
    sheet_title = "All Results"
    filename_base = "talent_hire_results"
    if current_filter == 'selected' or 'selected' in current_filter:
        attempts_qs = attempts_qs.filter(status__iexact='Selected')
        sheet_title = "Selected Candidates"
        filename_base = "talent_hire_selected"
    elif current_filter in ['not-selected', 'not_selected', 'unselected', 'not'] or any(x in current_filter for x in ['not', 'unselected']):
        attempts_qs = attempts_qs.filter(status__iexact='Not Selected')
        sheet_title = "Not Selected Candidates"
        filename_base = "talent_hire_not_selected"
    attempts = attempts_qs
    ws.title = sheet_title

    light_fill = PatternFill(start_color="FFF3E0", end_color="FFF3E0", fill_type="solid")
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

    for row_num, attempt in enumerate(attempts, start=2):
        row_data = [
            row_num - 1, attempt.candidate.name, attempt.candidate.mobile,
            attempt.candidate.registration_id, attempt.score, attempt.total,
            f"{attempt.percentage}%", attempt.status,
            attempt.date_taken.strftime('%d %b %Y, %I:%M %p'),
        ]
        row_fill = light_fill if row_num % 2 == 0 else white_fill
        for col_num, value in enumerate(row_data, start=1):
            cell = ws.cell(row=row_num, column=col_num, value=value)
            cell.fill = row_fill
            cell.alignment = center_align
            if col_num == 8:
                cell.font = Font(
                    color="1E8449" if attempt.status == "Selected" else "C0392B",
                    bold=True
                )

    for i, width in enumerate([8, 25, 18, 20, 10, 10, 15, 18, 25], start=1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = width

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename_base}.xlsx"'
    wb.save(response)
    return response


@admin_required
def admin_settings_view(request):
    """All-exams list with per-exam stats. Used for browsing/managing exams."""
    from django.db.models import Count
    exams = Exam.objects.all().annotate(
        q_count=Count('questions', distinct=True),
        a_count=Count('attempts', distinct=True),
    ).order_by('id')
    return render(request, 'exam/admin_settings.html', {'exams': exams})


@admin_required
def admin_add_exam(request):
    """Add a new exam with full settings, candidate/question selection support."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        desc = request.POST.get('description', '').strip()
        if name:
            exam = Exam.objects.create(
                name=name,
                description=desc,
                is_active=True,
                total_questions=request.POST.get('total_questions') or 20,
                duration_minutes=request.POST.get('duration_minutes') or 60,
                min_selection_score=60,  # kept in model (UI uses Passing % only)
                passing_percentage=request.POST.get('passing_percentage') or 50,
                max_attempts=request.POST.get('max_attempts') or 1,
                shuffle_questions=request.POST.get('shuffle_questions') == 'on',
                negative_marking=request.POST.get('negative_marking') == 'on',
                show_answers=request.POST.get('show_answers') == 'on',
                results_published=request.POST.get('results_published') == 'on',
            )

            # Parse schedule with timezone (Asia/Kolkata)
            tz = pytz.timezone('Asia/Kolkata')
            start_str = request.POST.get('start_time')
            end_str = request.POST.get('end_time')
            if start_str:
                dt = timezone.datetime.strptime(start_str, '%Y-%m-%dT%H:%M')
                exam.start_time = tz.localize(dt)
            if end_str:
                dt = timezone.datetime.strptime(end_str, '%Y-%m-%dT%H:%M')
                exam.end_time = tz.localize(dt)
            exam.save()

            exam.assigned_candidates.set(request.POST.getlist('candidate_ids'))
            exam.subjects.set(request.POST.getlist('subject_ids'))
            
            # Link selected questions to this exam (sets FK)
            question_ids = request.POST.getlist('question_ids')
            if question_ids:
                for qid in question_ids:
                    try:
                        q = Question.objects.get(id=qid)
                        q.exam = exam
                        q.save()
                    except Question.DoesNotExist:
                        pass
                messages.info(request, f"Linked {len(question_ids)} specific questions to exam.")
            
            messages.success(request, f"Exam '{name}' created successfully with selected candidates, questions and settings.")
            return redirect('admin_edit_exam', pk=exam.pk)  # redirect to settings page (like form but for edit)
        else:
            messages.error(request, "Exam name is required.")
    
    return render(request, 'exam/admin_exam_form.html', {
        'action': 'Add',
        'candidates': Candidate.objects.all().order_by('name'),
        'subjects': Category.objects.all().order_by('name'),
        'questions': Question.objects.all().order_by('question_text')[:50],  # Limited for preview/select
    })


@admin_required
def admin_edit_exam(request, pk):
    """Edit exam details and settings."""
    exam = get_object_or_404(Exam, pk=pk)
    
    if request.method == 'POST':
        exam.name = request.POST.get('name', '').strip()
        exam.description = request.POST.get('description', '').strip()
        exam.is_active = request.POST.get('is_active') == 'on'
        exam.duration_minutes = request.POST.get('duration_minutes') or 10
        exam.max_attempts = request.POST.get('max_attempts') or 1
        exam.passing_percentage = request.POST.get('passing_percentage') or 70
        exam.total_questions = request.POST.get('total_questions') or 20
        exam.shuffle_questions = request.POST.get('shuffle_questions') == 'on'
        exam.negative_marking = request.POST.get('negative_marking') == 'on'
        exam.show_answers = request.POST.get('show_answers') == 'on'
        exam.results_published = request.POST.get('results_published') == 'on'
        # min_selection_score removed from UI (defaults in model)

        tz = pytz.timezone('Asia/Kolkata')
        start_str = request.POST.get('start_time')
        end_str = request.POST.get('end_time')
        if start_str:
            dt = timezone.datetime.strptime(start_str, '%Y-%m-%dT%H:%M')
            exam.start_time = tz.localize(dt)
        else:
            exam.start_time = None
        if end_str:
            dt = timezone.datetime.strptime(end_str, '%Y-%m-%dT%H:%M')
            exam.end_time = tz.localize(dt)
        else:
            exam.end_time = None

        exam.save()
        exam.assigned_candidates.set(request.POST.getlist('candidate_ids'))
        exam.subjects.set(request.POST.getlist('subject_ids'))
        messages.success(request, "Exam settings updated.")
        return redirect('admin_edit_exam', pk=exam.pk)

    context = {
        'exam': exam,
        'categories': Category.objects.all().order_by('name'),
        'candidates': Candidate.objects.all().order_by('name'),
    }
    return render(request, 'exam/admin_exam_settings.html', context)


@admin_required
def admin_exam_detail(request, pk):
    """Exam detail: info, stats, full question list with bulk import / multi-delete."""
    exam = get_object_or_404(Exam, pk=pk)
    # Include both exam-specific and shared (unassigned) questions for the full pool used by this exam
    questions = Question.objects.filter(
        Q(exam=exam) | Q(exam__isnull=True)
    ).distinct().order_by('id')
    attempts = ExamAttempt.objects.filter(exam=exam).select_related('candidate').order_by('-date_taken')

    selected_count = attempts.filter(status='Selected').count()
    not_selected_count = attempts.filter(status='Not Selected').count()
    attempt_count = attempts.count()
    selection_rate = round((selected_count / attempt_count * 100), 1) if attempt_count > 0 else 0

    assigned_candidates = exam.assigned_candidates.all().order_by('name')
    candidate_count = assigned_candidates.count() or Candidate.objects.count()

    # Subject distribution based on linked categories/subjects (uses their configured question_count)
    category_stats = []
    subjects = exam.subjects.all()
    if subjects.exists():
        total = sum(s.question_count for s in subjects) or 1
        colors = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444']
        for i, subj in enumerate(subjects):
            pct = round((subj.question_count / total * 100), 1)
            category_stats.append({
                'name': subj.name,
                'count': subj.question_count,
                'percent': pct,
                'color': colors[i % len(colors)],
            })
    # Fallback if no subjects but questions exist
    elif questions.exists():
        category_stats = [{
            'name': 'General Questions',
            'count': questions.count(),
            'percent': 100,
            'color': '#10b981'
        }]

    context = {
        'exam': exam,
        'questions': questions,
        'attempts': attempts,
        'assigned_candidates': assigned_candidates,
        'question_count': questions.count(),
        'candidate_count': candidate_count,
        'attempt_count': attempt_count,
        'selected_count': selected_count,
        'not_selected_count': not_selected_count,
        'selection_rate': selection_rate,
        'category_stats': category_stats,
        'all_exams': Exam.objects.exclude(id=exam.id).order_by('name'),
    }
    return render(request, 'exam/admin_exam_detail.html', context)


@admin_required
def admin_delete_exam(request, pk):
    """Delete an exam."""
    exam = get_object_or_404(Exam, pk=pk)
    if request.method == 'POST':
        name = exam.name
        exam.delete()
        messages.success(request, f"Exam '{name}' deleted.")
        return redirect('admin_settings')
    
    return render(request, 'exam/admin_confirm_delete.html', {
        'object_name': exam.name,
        'object_type': 'Exam',
        'cancel_url': 'admin_settings'
    })


# ═══════════════════════════════════════════════════════════════════
# CANDIDATE PHASE 2 FEATURES
# ═══════════════════════════════════════════════════════════════════

def candidate_dashboard(request):
    """Candidate personal dashboard with active exams and attempt history."""
    candidate_id = request.session.get('candidate_id')
    if not candidate_id:
        return redirect('login')
    _discard_login_welcome_messages(request)

    try:
        candidate = Candidate.objects.get(id=candidate_id)
    except Candidate.DoesNotExist:
        return redirect('login')

    active_exam_list = _attach_candidate_exam_status(
        _candidate_visible_active_exams(candidate).order_by('-id'),
        candidate,
    )
    attempts = ExamAttempt.objects.filter(candidate=candidate).select_related('exam').order_by('-date_taken')

    context = {
        'candidate': candidate,
        'candidate_name': candidate.name,
        'attempts': attempts,
        'active_exams': active_exam_list,
        'active_exam_count': len(active_exam_list),
    }
    context.update(_candidate_context(request))
    return render(request, 'exam/candidate_dashboard.html', context)


def candidate_active_exams(request):
    """Show all active exams available to the candidate."""
    candidate_id = request.session.get('candidate_id')
    if not candidate_id:
        return redirect('login')
    _discard_login_welcome_messages(request)

    try:
        candidate = Candidate.objects.get(id=candidate_id)
    except Candidate.DoesNotExist:
        return redirect('login')

    search_query = request.GET.get('q', '').strip()
    time_filter = request.GET.get('time_filter', 'all')
    sort_by = request.GET.get('sort', 'latest')

    exams = _candidate_visible_active_exams(candidate)
    if search_query:
        exams = exams.filter(Q(name__icontains=search_query) | Q(description__icontains=search_query))

    now = timezone.now()
    if time_filter == 'open':
        exams = exams.filter(Q(start_time__isnull=True) | Q(start_time__lte=now)).filter(
            Q(end_time__isnull=True) | Q(end_time__gte=now)
        )
    elif time_filter == 'scheduled':
        exams = exams.filter(start_time__gt=now)
    elif time_filter == 'no_end':
        exams = exams.filter(end_time__isnull=True)

    sort_map = {
        'latest': '-id',
        'oldest': 'id',
        'name': 'name',
        'name_desc': '-name',
        'duration': 'duration_minutes',
        'duration_desc': '-duration_minutes',
        'passing': 'passing_percentage',
        'passing_desc': '-passing_percentage',
    }
    exams = exams.order_by(sort_map.get(sort_by, '-id'))
    active_exam_list = _attach_candidate_exam_status(list(exams), candidate)

    context = {
        'candidate': candidate,
        'candidate_name': candidate.name,
        'active_exams': active_exam_list,
        'active_exam_count': len(active_exam_list),
        'search_query': search_query,
        'time_filter': time_filter,
        'sort_by': sort_by,
    }
    context.update(_candidate_context(request))
    return render(request, 'exam/candidate_active_exams.html', context)


def exam_rules(request):
    """Display exam rules and guidelines."""
    candidate_id = request.session.get('candidate_id')
    if not candidate_id:
        return redirect('login')

    context = {
        'candidate_name': request.session.get('candidate_name'),
    }
    return render(request, 'exam/exam_rules.html', context)


def pre_exam_check(request, exam_id):
    """System check page before starting a specific exam."""
    candidate_id = request.session.get('candidate_id')
    if not candidate_id:
        return redirect('login')

    candidate = get_object_or_404(Candidate, id=candidate_id)
    exam = get_object_or_404(Exam, id=exam_id, is_active=True)
    exam = _attach_candidate_exam_status([exam], candidate)[0]

    context = {
        'exam': exam,
        'candidate_name': candidate.name,
    }
    return render(request, 'exam/pre_exam_check.html', context)


def help_support(request):
    """Help and support: FAQs + raise-query form + own queries list."""
    candidate_id = request.session.get('candidate_id')
    if not candidate_id:
        return redirect('login')

    candidate = get_object_or_404(Candidate, id=candidate_id)

    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()
        if not subject or not message:
            messages.error(request, "Subject and message are required.")
        else:
            SupportQuery.objects.create(
                candidate=candidate,
                subject=subject,
                message=message,
            )
            _notify(
                candidate,
                title="Query received",
                message=f"Your query \"{subject[:60]}\" has been received. The admin team will respond shortly.",
                category='support',
                link='/help/',
            )
            messages.success(request, "Your query has been raised. Admin will respond soon.")
            return redirect('help_support')

    queries = SupportQuery.objects.filter(candidate=candidate).order_by('-created_at')

    context = {
        'candidate_name': candidate.name,
        'queries': queries,
    }
    context.update(_candidate_context(request))
    return render(request, 'exam/help_support.html', context)


def notifications(request):
    """Notifications inbox — real per-candidate rows."""
    candidate_id = request.session.get('candidate_id')
    if not candidate_id:
        return redirect('login')

    candidate = get_object_or_404(Candidate, id=candidate_id)
    notifs = Notification.objects.filter(candidate=candidate).order_by('-created_at')

    context = {
        'candidate_name': candidate.name,
        'notifications': notifs,
        'unread_count': notifs.filter(is_read=False).count(),
        'total_count': notifs.count(),
    }
    context.update(_candidate_context(request))
    return render(request, 'exam/notifications.html', context)


def notification_mark_read(request, pk):
    """Mark single notification as read (POST)."""
    candidate_id = request.session.get('candidate_id')
    if not candidate_id:
        return redirect('login')
    notif = get_object_or_404(Notification, pk=pk, candidate_id=candidate_id)
    notif.is_read = True
    notif.save(update_fields=['is_read'])
    nxt = request.POST.get('next') or request.GET.get('next') or 'notifications'
    if nxt.startswith('/'):
        return redirect(nxt)
    return redirect(nxt)


def notification_mark_all_read(request):
    """Mark all notifications for this candidate as read."""
    candidate_id = request.session.get('candidate_id')
    if not candidate_id:
        return redirect('login')
    Notification.objects.filter(candidate_id=candidate_id, is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    nxt = request.POST.get('next') or request.GET.get('next') or 'notifications'
    if nxt.startswith('/'):
        return redirect(nxt)
    return redirect(nxt)


# ── Self-Registration & Candidate Profile (New Feature) ─────────────────
def candidate_register(request):
    """Public form for candidates to request access. Creates PendingRegistration for admin approval."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        mobile = request.POST.get('mobile', '').strip()
        reg_id = request.POST.get('registration_id', '').strip()
        reason = request.POST.get('reason', '').strip()
        if name and mobile and reg_id:
            if (PendingRegistration.objects.filter(registration_id=reg_id).exists() or 
                Candidate.objects.filter(registration_id=reg_id).exists()):
                messages.error(request, 'This Registration ID is already taken or pending approval.')
            else:
                PendingRegistration.objects.create(
                    name=name, mobile=mobile, registration_id=reg_id, reason=reason
                )
                messages.success(request, 'Registration request submitted. Admin will review shortly.')
                return redirect('login')
        else:
            messages.error(request, 'Name, Mobile, and Registration ID are required.')
    return render(request, 'exam/register.html', {'title': 'Register for Access'})


def candidate_profile(request):
    """View own data (name, reg ID) and change password after login."""
    candidate_id = request.session.get('candidate_id')
    if not candidate_id:
        return redirect('login')
    candidate = get_object_or_404(Candidate, id=candidate_id)
    if request.method == 'POST':
        new_password = request.POST.get('new_password', '').strip()
        if new_password and len(new_password) >= 6:
            candidate.password = make_password(new_password)
            candidate.save()
            messages.success(request, 'Password updated successfully. Use it for next login.')
            return redirect('candidate_profile')
        messages.error(request, 'Password must be at least 6 characters.')
    attempts = ExamAttempt.objects.filter(candidate=candidate).order_by('-date_taken')
    context = {
        'candidate': candidate,
        'candidate_name': candidate.name,
        'attempts': attempts,
        'attempted_count': attempts.count(),
        'selected_count': attempts.filter(status='Selected').count(),
    }
    context.update(_candidate_context(request))
    return render(request, 'exam/candidate_profile.html', context)


@admin_required
def admin_pending_registrations(request):
    """List pending self-registrations for admin approval."""
    pendings = PendingRegistration.objects.all()
    return render(request, 'exam/admin_pending.html', {'pendings': pendings})


@admin_required
def admin_approve_registration(request, pk):
    """Approve pending request by creating Candidate record."""
    pending = get_object_or_404(PendingRegistration, pk=pk)
    if request.method == 'POST':
        candidate = Candidate.objects.create(
            name=pending.name,
            mobile=pending.mobile,
            registration_id=pending.registration_id,
        )
        pending.status = 'Approved'
        pending.reviewed_at = timezone.now()
        pending.reviewed_by = request.user.username if hasattr(request.user, 'username') else 'Admin'
        pending.save()
        messages.success(request, f"Approved {candidate.name} (Reg ID: {candidate.registration_id}). They can now login.")
        return redirect('admin_pending_registrations')
    return redirect('admin_pending_registrations')


@admin_required
def admin_reject_registration(request, pk):
    """Reject a pending registration request."""
    pending = get_object_or_404(PendingRegistration, pk=pk)
    if request.method == 'POST':
        pending.status = 'Rejected'
        pending.reviewed_at = timezone.now()
        pending.reviewed_by = request.user.username if hasattr(request.user, 'username') else 'Admin'
        pending.save()
        messages.success(request, f"Rejected registration for {pending.name}.")
    return redirect('admin_pending_registrations')
