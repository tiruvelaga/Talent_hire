"""
admin.py - Django Admin Configuration for Talent Hire

Registers all models so admin can:
- Add/Edit/Delete candidates
- Add/Edit/Delete questions
- View exam results
"""

from django.contrib import admin
from .models import Candidate, Question, ExamAttempt, Answer


# ─────────────────────────────────────────────────────────────────────
# CANDIDATE ADMIN
# Admin can register candidates who will take the exam
# ─────────────────────────────────────────────────────────────────────
@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    # Columns shown in the list view
    list_display = ('name', 'mobile', 'registration_id')

    # Add a search box to search candidates by name or registration ID
    search_fields = ('name', 'registration_id', 'mobile')

    # Fields shown when adding/editing a candidate
    fields = ('name', 'mobile', 'registration_id')


# ─────────────────────────────────────────────────────────────────────
# QUESTION ADMIN
# Admin can add, edit, update, and delete exam questions
# ─────────────────────────────────────────────────────────────────────
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    # Show these columns in the list view
    list_display  = ('id', 'short_question', 'correct_answer')

    # Filter sidebar - filter by correct answer
    list_filter   = ('correct_answer',)

    # Search box - search by question text
    search_fields = ('question_text',)

    # Fields shown on add/edit form
    fields = ('question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer')

    def short_question(self, obj):
        """Show only first 80 characters of question in list view"""
        return obj.question_text[:80] + '...' if len(obj.question_text) > 80 else obj.question_text
    short_question.short_description = 'Question'  # Column header


# ─────────────────────────────────────────────────────────────────────
# EXAM ATTEMPT ADMIN
# Admin can view all exam results here
# ─────────────────────────────────────────────────────────────────────
@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    # Show these columns in the list view
    list_display = ('candidate', 'score', 'total', 'percentage', 'status', 'date_taken')

    # Filter sidebar - filter by status
    list_filter  = ('status',)

    # Search box - search by candidate name
    search_fields = ('candidate__name', 'candidate__registration_id')

    # Don't allow editing results (read-only)
    readonly_fields = ('candidate', 'score', 'total', 'percentage', 'status', 'date_taken')

    # Prevent adding attempts from admin (only created programmatically)
    def has_add_permission(self, request):
        return False


# ─────────────────────────────────────────────────────────────────────
# ANSWER ADMIN
# Admin can see individual answers (for debugging/audit)
# ─────────────────────────────────────────────────────────────────────
@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('attempt', 'question', 'selected_answer', 'is_correct')
    list_filter  = ('is_correct',)
    readonly_fields = ('attempt', 'question', 'selected_answer', 'is_correct')

    def has_add_permission(self, request):
        return False


# ─────────────────────────────────────────────────────────────────────
# CUSTOMIZE ADMIN PANEL TITLE
# ─────────────────────────────────────────────────────────────────────
admin.site.site_header  = "Talent Hire Admin"
admin.site.site_title   = "Talent Hire Admin Panel"
admin.site.index_title  = "Welcome to Talent Hire Admin"
