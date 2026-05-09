"""WSGI config for talent_hire project."""
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'talent_hire.settings')
application = get_wsgi_application()
