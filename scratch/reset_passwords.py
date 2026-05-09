import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'talent_hire.settings')
django.setup()

from exam.models import Candidate
from django.contrib.auth.hashers import make_password

candidates = Candidate.objects.all()
print(f"Updating {candidates.count()} candidates...")

for c in candidates:
    c.password = make_password(c.registration_id)
    c.is_activated = True
    c.save()

print("Done! All candidates can now login using their Registration ID as both username and password.")
