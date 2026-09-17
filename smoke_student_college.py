import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skillbridge.settings')
import django

django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS.append('testserver')

from rest_framework.test import APIClient
from api.models import User, StudentProfile, College


def assert_status(response, expected):
    if response.status_code != expected:
        payload = getattr(response, 'data', getattr(response, 'content', b'').decode(errors='replace'))
        raise AssertionError(f'Expected {expected}, got {response.status_code}: {payload}')


email = 'student-signup-college-smoke@example.com'
User.objects.filter(email=email).delete()
College.objects.filter(name='Signup Smoke College').delete()

client = APIClient()
try:
    # This mirrors what AuthContext.jsx now sends after the fix: `college` is included.
    response = client.post('/api/auth/register/student/', {
        'email': email,
        'password': 'TestPassword123!',
        'password2': 'TestPassword123!',
        'first_name': 'Signup',
        'last_name': 'Smoke',
        'college': 'Signup Smoke College',
        'experience_level': 'intermediate',
        'availability': 'part_time',
    }, format='json')
    assert_status(response, 201)

    user = User.objects.get(email=email)
    profile = StudentProfile.objects.get(user=user)
    assert profile.college is not None, 'Student signup did not attribute a college (regression!)'
    assert profile.college.name == 'Signup Smoke College'
    print('student registration -> college attribution: ok')
finally:
    college = StudentProfile.objects.filter(user__email=email).first()
    college_id = college.college_id if college else None
    StudentProfile.objects.filter(user__email=email).delete()
    User.objects.filter(email=email).delete()
    if college_id:
        College.objects.filter(pk=college_id).delete()
