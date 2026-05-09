"""
models.py - Database Models for Talent Hire Exam Portal

We define 4 models here:
1. Candidate   - Stores candidate login info (pre-registered by admin)
2. Question    - Stores exam questions with 4 options
3. ExamAttempt - Stores result of each candidate's exam attempt
4. Answer      - Stores each individual answer given by the candidate
"""

from django.db import models


# ─────────────────────────────────────────────────────────────────────
# 1. CANDIDATE MODEL
# Admin pre-registers candidates with name, mobile, and registration ID
# ─────────────────────────────────────────────────────────────────────
class Candidate(models.Model):
    name            = models.CharField(max_length=100)        # Full name of candidate
    mobile          = models.CharField(max_length=15)         # 10-digit mobile number
    registration_id = models.CharField(max_length=50, unique=True)  # Unique ID given by admin
    password        = models.CharField(max_length=128, blank=True, null=True) # Hashed password
    is_activated    = models.BooleanField(default=True)       # Candidates can login by default
    
    def save(self, *args, **kwargs):
        # If password is not set, use registration_id as default password
        from django.contrib.auth.hashers import make_password
        if not self.password:
            self.password = make_password(self.registration_id)
        super().save(*args, **kwargs)

    def __str__(self):
        # This is what shows up in Django admin list
        return f"{self.name} ({self.registration_id})"

    class Meta:
        verbose_name = "Candidate"
        verbose_name_plural = "Candidates"
        ordering = ['name']


# ─────────────────────────────────────────────────────────────────────
# 2. QUESTION MODEL
# Stores MCQ questions with 4 options and the correct answer
# Admin can add/edit/delete questions via Django Admin Panel
# ─────────────────────────────────────────────────────────────────────
class Question(models.Model):
    question_text   = models.TextField()              # The actual question
    option_a        = models.CharField(max_length=300)  # Option A
    option_b        = models.CharField(max_length=300)  # Option B
    option_c        = models.CharField(max_length=300)  # Option C
    option_d        = models.CharField(max_length=300)  # Option D

    # correct_answer stores 'A', 'B', 'C', or 'D'
    ANSWER_CHOICES = [
        ('A', 'Option A'),
        ('B', 'Option B'),
        ('C', 'Option C'),
        ('D', 'Option D'),
    ]
    correct_answer = models.CharField(max_length=1, choices=ANSWER_CHOICES)
    exam           = models.ForeignKey('Exam', on_delete=models.SET_NULL, null=True, blank=True, related_name='questions')

    @property
    def get_correct_answer_text(self):
        """Returns the actual text of the correct option."""
        mapping = {
            'A': self.option_a,
            'B': self.option_b,
            'C': self.option_c,
            'D': self.option_d
        }
        return mapping.get(self.correct_answer, "")

    def __str__(self):
        # Show first 60 chars of question in admin panel
        return self.question_text[:60] + "..." if len(self.question_text) > 60 else self.question_text

    class Meta:
        verbose_name = "Question"
        verbose_name_plural = "Questions"


# ─────────────────────────────────────────────────────────────────────
# 3. EXAM ATTEMPT MODEL
# Created once per candidate when they submit the exam
# Stores overall result: score, percentage, status
# ─────────────────────────────────────────────────────────────────────
class ExamAttempt(models.Model):
    candidate   = models.ForeignKey(Candidate, on_delete=models.CASCADE)  # Link to candidate
    exam        = models.ForeignKey('Exam', on_delete=models.SET_NULL, null=True, blank=True, related_name='attempts')
    score       = models.IntegerField(default=0)          # Number of correct answers (e.g., 15)
    total       = models.IntegerField(default=20)         # Total questions (always 20)
    percentage  = models.FloatField(default=0.0)          # e.g., 75.0
    status      = models.CharField(max_length=20)         # 'Selected' or 'Not Selected'
    is_published = models.BooleanField(default=True)       # Whether candidate can see this result
    date_taken  = models.DateTimeField(auto_now_add=True) # Automatically set when attempt created

    def __str__(self):
        return f"{self.candidate.name} | {self.score}/{self.total} | {self.status}"

    class Meta:
        verbose_name = "Exam Attempt"
        verbose_name_plural = "Exam Attempts"
        ordering = ['-date_taken']  # Newest first


# ─────────────────────────────────────────────────────────────────────
# 4. ANSWER MODEL
# Stores each answer the candidate selected during the exam
# One row per question per attempt (so 20 rows per attempt)
# ─────────────────────────────────────────────────────────────────────
class Answer(models.Model):
    attempt         = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE)  # Which attempt
    question        = models.ForeignKey(Question, on_delete=models.CASCADE)     # Which question
    selected_answer = models.CharField(max_length=1, blank=True, null=True)     # 'A', 'B', 'C', 'D', or None if skipped
    is_correct      = models.BooleanField(default=False)  # Was the answer correct?

    def __str__(self):
        return f"Attempt #{self.attempt.id} | Q:{self.question.id} | Selected:{self.selected_answer} | Correct:{self.is_correct}"

    class Meta:
        verbose_name = "Answer"
        verbose_name_plural = "Answers"


# ─────────────────────────────────────────────────────────────────────
# 5. EXAM MODEL
# Stores individual exams with their own specific settings
# ─────────────────────────────────────────────────────────────────────
class Exam(models.Model):
    name                = models.CharField(max_length=200)
    description         = models.TextField(blank=True, null=True)
    is_active           = models.BooleanField(default=True)
    assigned_candidates = models.ManyToManyField(Candidate, blank=True, related_name='assigned_exams')
    subjects            = models.ManyToManyField('Category', blank=True, related_name='exams')
    
    duration_minutes    = models.IntegerField(default=10)
    start_time          = models.DateTimeField(null=True, blank=True)
    end_time            = models.DateTimeField(null=True, blank=True)
    
    passing_percentage  = models.IntegerField(default=50)
    min_selection_score = models.IntegerField(default=60)
    total_questions     = models.IntegerField(default=20)
    
    max_attempts        = models.IntegerField(default=1)
    show_answers        = models.BooleanField(default=True)
    results_published   = models.BooleanField(default=True)
    shuffle_questions   = models.BooleanField(default=True)
    negative_marking    = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Exam"
        verbose_name_plural = "Exams"


# ─────────────────────────────────────────────────────────────────────
# 6. EXAM SETTINGS MODEL (Deprecated - use Exam model)
# ─────────────────────────────────────────────────────────────────────
class ExamSetting(models.Model):
    duration_minutes    = models.IntegerField(default=10)        # Exam time in minutes
    start_time          = models.DateTimeField(null=True, blank=True) # When exam opens
    end_time            = models.DateTimeField(null=True, blank=True) # When exam closes
    
    passing_percentage  = models.IntegerField(default=50)        # Min to pass
    min_selection_score = models.IntegerField(default=60)        # Above this = Selected
    total_questions     = models.IntegerField(default=20)        # Total Qs per exam
    
    max_attempts        = models.IntegerField(default=1)         # Attempts per candidate
    show_answers        = models.BooleanField(default=True)      # Reveal answers after submit
    results_published   = models.BooleanField(default=True)      # Global toggle for results visibility

    def __str__(self):
        return "Global Exam Settings"


# ─────────────────────────────────────────────────────────────────────
# 6. CATEGORY MODEL
# Stores subject categories for questions
# ─────────────────────────────────────────────────────────────────────
class Category(models.Model):
    name           = models.CharField(max_length=100)
    question_count = models.IntegerField(default=0)  # How many questions to pull from this category

    def __str__(self):
        return f"{self.name} ({self.question_count})"


# ─────────────────────────────────────────────────────────────────────
# 7. NOTIFICATION MODEL
# Per-candidate inbox. Created by admin actions (publish results, etc.)
# ─────────────────────────────────────────────────────────────────────
class Notification(models.Model):
    CATEGORY_CHOICES = [
        ('info', 'Info'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('exam', 'Exam'),
        ('results', 'Results'),
        ('support', 'Support'),
    ]
    candidate  = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='notifications')
    title      = models.CharField(max_length=200)
    message    = models.TextField()
    category   = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='info')
    link       = models.CharField(max_length=255, blank=True, default='')
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"[{self.category}] {self.title} → {self.candidate.name}"


# ─────────────────────────────────────────────────────────────────────
# 8. SUPPORT QUERY MODEL
# Candidate-raised questions/issues to admin via Help page
# ─────────────────────────────────────────────────────────────────────
class SupportQuery(models.Model):
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('Answered', 'Answered'),
        ('Closed', 'Closed'),
    ]
    candidate      = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='queries')
    subject        = models.CharField(max_length=200)
    message        = models.TextField()
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    admin_response = models.TextField(blank=True, default='')
    created_at     = models.DateTimeField(auto_now_add=True)
    responded_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Support Query"
        verbose_name_plural = "Support Queries"

    def __str__(self):
        return f"{self.candidate.name}: {self.subject} [{self.status}]"


# ─────────────────────────────────────────────────────────────────────
# 9. PENDING REGISTRATION MODEL (for self-registration + admin approval)
# ─────────────────────────────────────────────────────────────────────
class PendingRegistration(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    name            = models.CharField(max_length=100)
    mobile          = models.CharField(max_length=15)
    registration_id = models.CharField(max_length=50, unique=True)
    reason          = models.TextField(blank=True, null=True, help_text="Why they need access")
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    requested_at    = models.DateTimeField(auto_now_add=True)
    reviewed_at     = models.DateTimeField(null=True, blank=True)
    reviewed_by     = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.name} ({self.registration_id}) - {self.status}"

    class Meta:
        verbose_name = "Pending Registration"
        verbose_name_plural = "Pending Registrations"
        ordering = ['-requested_at']
