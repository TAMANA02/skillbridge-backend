import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skillbridge.settings')
import django

django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS.append('testserver')

from rest_framework.test import APIClient
from api.models import User, StudentProfile, Team, FeedPost, College


def assert_status(response, expected):
    if response.status_code != expected:
        payload = getattr(response, 'data', getattr(response, 'content', b'').decode(errors='replace'))
        raise AssertionError(f'Expected {expected}, got {response.status_code}: {payload}')


email = 'api-smoke-new-features@example.com'
FeedPost.objects.filter(author__email=email).delete()
Team.objects.filter(leader__email=email).delete()
User.objects.filter(email=email).delete()
College.objects.filter(name='API Smoke College').delete()
user = User.objects.create_user(
    email=email,
    password='TestPassword123!',
    first_name='API',
    last_name='Smoke',
    role='student',
)
StudentProfile.objects.create(user=user, experience_level='intermediate', availability='part_time')
client = APIClient()
client.force_authenticate(user=user)

try:
    team_response = client.post('/api/teams/', {
        'name': 'API Smoke Team',
        'college': 'API Smoke College',
        'description': 'A team created by the integration smoke test.',
        'skills': ['React', 'Django'],
        'availability': 'taking_projects',
        'members': [{'name': 'API Smoke', 'role': 'Full Stack Lead', 'email': email}],
    }, format='json')
    assert_status(team_response, 201)
    team = Team.objects.get(pk=team_response.data['id'])
    assert team.college is not None, 'Team.college was not resolved to a real College record'
    assert team.college.name == 'API Smoke College'

    # The member (also the requester) should get attributed to the team's college.
    user.student_profile.refresh_from_db()
    assert user.student_profile.college_id == team.college_id, 'Team member was not attributed to the college'

    post_response = client.post('/api/feed/', {
        'team': str(team.id),
        'body': 'API smoke post for the SkillBridge community feed.',
        'tags': ['React', 'Django'],
    }, format='json')
    assert_status(post_response, 201)
    post = FeedPost.objects.get(pk=post_response.data['id'])

    assert_status(client.post(f'/api/feed/{post.id}/like/'), 200)
    assert_status(client.post(f'/api/feed/{post.id}/save/'), 200)
    assert_status(client.post(f'/api/feed/{post.id}/share/'), 201)
    assert_status(client.post(f'/api/feed/{post.id}/comments/', {'body': 'Looks good.'}, format='json'), 201)
    assert_status(client.get('/api/feed/'), 200)
    assert_status(client.get('/api/teams/'), 200)
    print('team registration: ok')
    print('feed create/list/reaction/comment actions: ok')

    # --- College leaderboard ---
    college_list = client.get('/api/colleges/')
    assert_status(college_list, 200)
    names = [c['name'] for c in college_list.data['results']] if 'results' in college_list.data else [c['name'] for c in college_list.data]
    assert 'API Smoke College' in names, 'New college did not appear in /api/colleges/'

    college_detail = client.get(f'/api/colleges/{team.college.slug}/')
    assert_status(college_detail, 200)
    assert college_detail.data['total_developers'] == 1, f"expected 1 developer, got {college_detail.data['total_developers']}"
    assert college_detail.data['total_teams'] == 1, f"expected 1 team, got {college_detail.data['total_teams']}"

    leaderboard = client.get('/api/colleges/leaderboard/')
    assert_status(leaderboard, 200)
    print('college registration attribution + leaderboard: ok')
finally:
    FeedPost.objects.filter(pk=locals().get('post', None).pk if 'post' in locals() else None).delete()
    college_id = locals().get('team', None).college_id if 'team' in locals() else None
    Team.objects.filter(pk=locals().get('team', None).pk if 'team' in locals() else None).delete()
    StudentProfile.objects.filter(user=user).delete()
    User.objects.filter(pk=user.pk).delete()
    if college_id:
        College.objects.filter(pk=college_id).delete()
