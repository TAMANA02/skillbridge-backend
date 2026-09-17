import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skillbridge.settings')
import django

django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS.append('testserver')

from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from api.models import User, StudentProfile, ClientProfile, Project, Application, Review


def assert_status(response, expected, label=''):
    if response.status_code != expected:
        payload = getattr(response, 'data', getattr(response, 'content', b'').decode(errors='replace'))
        raise AssertionError(f'{label}: expected {expected}, got {response.status_code}: {payload}')


EMAILS = [
    'audit-student-a@example.com', 'audit-student-b@example.com',
    'audit-client-a@example.com', 'audit-client-b@example.com',
]
User.objects.filter(email__in=EMAILS).delete()

student_a = User.objects.create_user(email=EMAILS[0], password='TestPassword123!', first_name='Student', last_name='A', role='student')
student_b = User.objects.create_user(email=EMAILS[1], password='TestPassword123!', first_name='Student', last_name='B', role='student')
client_a = User.objects.create_user(email=EMAILS[2], password='TestPassword123!', first_name='Client', last_name='A', role='client')
client_b = User.objects.create_user(email=EMAILS[3], password='TestPassword123!', first_name='Client', last_name='B', role='client')

profile_a = StudentProfile.objects.create(user=student_a, experience_level='intermediate', availability='part_time')
StudentProfile.objects.create(user=student_b, experience_level='intermediate', availability='part_time')
cprofile_a = ClientProfile.objects.create(user=client_a, company_name='Acme A')
ClientProfile.objects.create(user=client_b, company_name='Acme B')

project = Project.objects.create(
    client=cprofile_a, title='Audit Test Project', description='desc', category='web',
    required_skills=['React'], budget_type='fixed', budget_min=100, budget_max=200,
    experience_level='intermediate', status='open',
)

anon = APIClient()
as_student_a = APIClient(); as_student_a.force_authenticate(user=student_a)
as_student_b = APIClient(); as_student_b.force_authenticate(user=student_b)
as_client_a = APIClient(); as_client_a.force_authenticate(user=client_a)
as_client_b = APIClient(); as_client_b.force_authenticate(user=client_b)

try:
    # --- 1. Public browsing (previously blocked entirely by IsAuthenticated) ---
    assert_status(anon.get('/api/students/'), 200, 'anon can browse student directory')
    assert_status(anon.get('/api/projects/'), 200, 'anon can browse project showcase')
    assert_status(anon.get(f'/api/students/{profile_a.id}/'), 200, 'anon can view a student profile')

    # --- 2. Cross-role profile IDOR (client editing another user's student profile) ---
    r = as_client_a.patch(f'/api/students/{profile_a.id}/', {'headline': 'hacked'}, format='json')
    assert r.status_code in (403, 404), f'client should not be able to edit a student profile, got {r.status_code}'
    profile_a.refresh_from_db()
    assert profile_a.headline != 'hacked', 'student profile was modified by a non-owner!'

    # --- 3. Project delete IDOR (any client could delete any project) ---
    r = as_client_b.delete(f'/api/projects/{project.id}/')
    assert r.status_code in (403, 404), f'client B should not be able to delete client A\'s project, got {r.status_code}'
    assert Project.objects.filter(pk=project.id).exists(), 'project was deleted by a non-owner!'

    # Owner can still delete/update their own project
    r = as_client_a.patch(f'/api/projects/{project.id}/', {'title': 'Updated by owner'}, format='json')
    assert_status(r, 200, 'owner should be able to update their own project')

    # --- 4. Application status privilege escalation ---
    app = Application.objects.create(student=profile_a, project=project, cover_letter='hire me')
    r = as_student_a.patch(f'/api/applications/{app.id}/', {'status': 'accepted'}, format='json')
    app.refresh_from_db()
    assert app.status == 'pending', f'student was able to self-accept their own application! status={app.status}'

    # Client can legitimately accept via the dedicated action, which also assigns the student
    r = as_client_a.patch(f'/api/applications/{app.id}/accept/')
    assert_status(r, 200, 'client accepts application')
    app.refresh_from_db()
    project.refresh_from_db()
    assert app.status == 'accepted'
    assert project.assigned_student_id == profile_a.id, 'accepting an application did not assign the student to the project'
    assert project.status == 'in_progress', 'project status did not move to in_progress after a hire'

    # --- 5. Review spoofing ---
    # An unrelated student (not hired, not the client) tries to review the client.
    r = as_student_b.post('/api/reviews/', {
        'reviewee': str(client_a.id), 'project': str(project.id), 'rating': 1, 'comment': 'spoofed review',
    }, format='json')
    assert r.status_code == 400, f'unrelated user should not be able to post a review, got {r.status_code}'

    # The actual hired student CAN review the client.
    r = as_student_a.post('/api/reviews/', {
        'reviewee': str(client_a.id), 'project': str(project.id), 'rating': 5, 'comment': 'Great client!',
    }, format='json')
    assert_status(r, 201, 'legitimate participant should be able to post a review')
    review_id = r.data['id']

    # A different, uninvolved user cannot delete that review.
    r = as_client_b.delete(f'/api/reviews/{review_id}/')
    assert r.status_code in (403, 404), f'unrelated user should not be able to delete a review, got {r.status_code}'
    assert Review.objects.filter(pk=review_id).exists(), 'review was deleted by a non-author!'

    # Public read of reviews still works
    assert_status(anon.get('/api/reviews/'), 200, 'anon can read reviews')

    # --- 6. Token refresh / logout endpoints exist and work ---
    refresh = RefreshToken.for_user(student_a)
    r = anon.post('/api/auth/refresh/', {'refresh': str(refresh)}, format='json')
    assert_status(r, 200, 'token refresh endpoint should work')
    assert 'access' in r.data

    # Use a separate, un-rotated token for the logout check - the one above was already
    # blacklisted by rotation (ROTATE_REFRESH_TOKENS + BLACKLIST_AFTER_ROTATION), so reusing
    # it here would correctly 400 regardless of whether logout itself works.
    logout_token = RefreshToken.for_user(student_a)
    r = as_student_a.post('/api/auth/logout/', {'refresh': str(logout_token)}, format='json')
    assert_status(r, 200, 'logout should blacklist the refresh token')
    r2 = anon.post('/api/auth/refresh/', {'refresh': str(logout_token)}, format='json')
    assert r2.status_code == 401, f'blacklisted refresh token should be rejected, got {r2.status_code}'

    print('public directory access: ok')
    print('cross-role profile IDOR blocked: ok')
    print('project delete IDOR blocked, owner update still works: ok')
    print('application self-accept blocked, legitimate accept assigns student + updates project: ok')
    print('review spoofing blocked, legitimate review works, non-author delete blocked: ok')
    print('token refresh + logout/blacklist: ok')
finally:
    Review.objects.filter(reviewer__in=[student_a, student_b]).delete()
    Application.objects.filter(student__user__in=[student_a, student_b]).delete()
    Project.objects.filter(pk=project.id).delete()
    StudentProfile.objects.filter(user__in=[student_a, student_b]).delete()
    ClientProfile.objects.filter(user__in=[client_a, client_b]).delete()
    User.objects.filter(email__in=EMAILS).delete()
