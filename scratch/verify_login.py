import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'talent_hire.settings')
django.setup()

from exam.models import Candidate
from django.contrib.auth.hashers import check_password, make_password

# Check a specific candidate (e.g., Arjun Reddy - TH-2024-003)
reg_id = "TH-2024-003"
try:
    c = Candidate.objects.get(registration_id=reg_id)
    print(f"Found Candidate: {c.name}")
    print(f"Password in DB (hashed): {c.password}")
    
    # Try to verify with reg_id as password
    is_valid = check_password(reg_id, c.password)
    print(f"Is '{reg_id}' a valid password? {is_valid}")
    
    if not is_valid:
        print("Re-hashing password to Registration ID...")
        c.password = make_password(reg_id)
        c.save()
        print("Password updated. Testing again...")
        is_valid = check_password(reg_id, c.password)
        print(f"Is '{reg_id}' a valid password now? {is_valid}")

except Candidate.DoesNotExist:
    print(f"Candidate {reg_id} not found.")
