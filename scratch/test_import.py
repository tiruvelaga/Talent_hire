import os
import django
import io
import csv

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'talent_hire.settings')
django.setup()

from exam.models import Candidate

# Create a mock CSV file
csv_content = """Name,Mobile,Registration ID
Test User 1,1234567890,TEST-001
Test User 2,0987654321,TEST-002
"""
file = io.StringIO(csv_content)
reader = csv.reader(file)
next(reader, None) # Skip header

print("Simulating Bulk Import...")
count = 0
for row in reader:
    name, mobile, reg_id = row[0], row[1], row[2]
    if not Candidate.objects.filter(registration_id=reg_id).exists():
        Candidate.objects.create(name=name, mobile=mobile, registration_id=reg_id)
        count += 1
        print(f"Created: {name}")

print(f"Imported {count} candidates.")

# Verify TEST-001 can login
from django.contrib.auth.hashers import check_password
c = Candidate.objects.get(registration_id="TEST-001")
is_valid = check_password("TEST-001", c.password)
print(f"Login Verification for TEST-001: {is_valid}")
