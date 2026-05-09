"""
urls.py - All URL patterns for Talent Hire Exam Portal

Candidate URLs:  /  /login/  /exam/  /submit/  /result/<id>/  /logout/
Admin Portal:    /portal/login/  /portal/  /portal/candidates/  /portal/questions/  /portal/results/
"""

from django.urls import path
from . import views

urlpatterns = [

    # ── Candidate URLs ───────────────────────────────────────────
    path('',                        views.home_view,           name='home'),
    path('login/',                  views.login_view,          name='login'),
    path('register/',               views.candidate_register,  name='candidate_register'),
    path('profile/',                views.candidate_profile,   name='candidate_profile'),
    path('change-password/',        views.change_password_view, name='change_password'),
    path('dashboard/',              views.candidate_dashboard, name='candidate_dashboard'),
    path('active-exams/',           views.candidate_active_exams, name='candidate_active_exams'),
    path('exam/<int:exam_id>/',      views.exam_view,           name='exam'),
    path('submit/<int:exam_id>/',    views.submit_exam,         name='submit_exam'),
    path('result/<int:attempt_id>/', views.result_view,        name='result'),
    path('results/',                 views.candidate_results_view, name='candidate_results'),
    path('logout/',                 views.logout_view,         name='logout'),
    path('rules/',                  views.exam_rules,          name='exam_rules'),
    path('pre-check/<int:exam_id>/', views.pre_exam_check,      name='pre_exam_check'),
    path('help/',                   views.help_support,        name='help_support'),
    path('notifications/',          views.notifications,       name='notifications'),
    path('notifications/<int:pk>/read/', views.notification_mark_read, name='notification_mark_read'),
    path('notifications/read-all/', views.notification_mark_all_read, name='notification_mark_all_read'),

    # ── Admin Portal URLs ────────────────────────────────────────
    path('portal/login/',           views.admin_login_view,     name='admin_login'),
    path('portal/logout/',          views.admin_logout_view,    name='admin_logout'),
    path('portal/',                 views.admin_dashboard_view, name='admin_dashboard'),

    # Candidates CRUD
    path('portal/candidates/',               views.admin_candidates_view,  name='admin_candidates'),
    path('portal/candidates/add/',           views.admin_add_candidate,    name='admin_add_candidate'),
    path('portal/candidates/import/',        views.admin_bulk_import_candidates, name='admin_bulk_import_candidates'),
    path('portal/candidates/bulk-delete/',   views.admin_bulk_delete_candidates, name='admin_bulk_delete_candidates'),
    path('portal/candidates/edit/<int:pk>/', views.admin_edit_candidate,   name='admin_edit_candidate'),
    path('portal/candidates/delete/<int:pk>/', views.admin_delete_candidate, name='admin_delete_candidate'),

    # Questions CRUD
    path('portal/questions/',               views.admin_questions_view, name='admin_questions'),
    path('portal/questions/add/',           views.admin_add_question,   name='admin_add_question'),
    path('portal/questions/import/',        views.admin_bulk_import_questions, name='admin_bulk_import_questions'),
    path('portal/questions/bulk-delete/',   views.admin_bulk_delete_questions, name='admin_bulk_delete_questions'),
    path('portal/questions/edit/<int:pk>/', views.admin_edit_question,  name='admin_edit_question'),
    path('portal/questions/delete/<int:pk>/', views.admin_delete_question, name='admin_delete_question'),

    # Results + Export
    path('portal/results/',         views.admin_results_view, name='admin_results'),
    path('portal/results/publish-all/', views.admin_publish_all_results, name='admin_publish_all_results'),
    path('portal/results/hold-all/',    views.admin_hold_all_results,    name='admin_hold_all_results'),
    path('portal/results/toggle/<int:pk>/', views.admin_toggle_result_publish, name='admin_toggle_result_publish'),
    path('portal/export/',          views.export_results,     name='export_results'),
    path('portal/queries/',         views.admin_queries_view, name='admin_queries'),
    path('portal/queries/<int:pk>/', views.admin_queries_view, name='admin_query_detail'),

    # Settings & Exams
    path('portal/settings/',        views.admin_settings_view, name='admin_settings'),
    path('portal/exams/',           views.admin_settings_view, name='admin_exams'),
    path('portal/exams/add/',       views.admin_add_exam,      name='admin_add_exam'),
    path('portal/exams/<int:pk>/',  views.admin_exam_detail,   name='admin_exam_detail'),
    path('portal/exams/edit/<int:pk>/', views.admin_edit_exam, name='admin_edit_exam'),
    path('portal/exams/delete/<int:pk>/', views.admin_delete_exam, name='admin_delete_exam'),

    # Pending Registrations (new self-register approval)
    path('portal/pending/',                    views.admin_pending_registrations, name='admin_pending_registrations'),
    path('portal/pending/approve/<int:pk>/',   views.admin_approve_registration, name='admin_approve_registration'),
    path('portal/pending/reject/<int:pk>/',    views.admin_reject_registration, name='admin_reject_registration'),
]
