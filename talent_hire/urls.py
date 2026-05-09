"""
Main URL configuration for Talent Hire project.
All exam-related URLs are handled by the 'exam' app.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),               # Django admin panel
    path('', include('exam.urls')),                # All exam app URLs
]
