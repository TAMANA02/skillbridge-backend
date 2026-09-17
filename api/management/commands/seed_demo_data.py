from django.core.management.base import BaseCommand
from django.db import transaction
from api.models import FeedPost, StudentProfile, Team, TeamMember, User


class Command(BaseCommand):
    help = 'Create or refresh demo teams and community feed records for local development.'

    @transaction.atomic
    def handle(self, *args, **options):
        lead, _ = User.objects.get_or_create(
            email='amaya.kapoor@skillbridge.demo',
            defaults={
                'username': 'amaya.kapoor@skillbridge.demo',
                'first_name': 'Amaya',
                'last_name': 'Kapoor',
                'role': 'student',
                'is_verified': True,
            },
        )
        lead.set_password('DemoPassword123!')
        lead.save(update_fields=['password'])
        StudentProfile.objects.get_or_create(
            user=lead,
            defaults={
                'headline': 'Full Stack Developer',
                'bio': 'Builds thoughtful products with React and Django.',
                'skills': ['React', 'Django', 'Product Design'],
                'experience_level': 'advanced',
                'availability': 'part_time',
            },
        )

        team, _ = Team.objects.update_or_create(
            slug='team-nova',
            defaults={
                'name': 'Team Nova',
                'leader': lead,
                'college': 'IIT Delhi',
                'description': 'A cross-functional student team building polished digital products for ambitious clients.',
                'skills': ['React', 'Django', 'Figma', 'PostgreSQL'],
                'availability': 'taking_projects',
                'verification_status': 'verified',
                'completed_projects': 16,
                'rating': 4.9,
                'success_rate': 94,
                'website_url': 'https://skillbridge.demo/teams/team-nova',
                'github_url': 'https://github.com/skillbridge/team-nova',
            },
        )
        TeamMember.objects.filter(team=team).delete()
        TeamMember.objects.create(team=team, user=lead, name='Amaya Kapoor', role='Full Stack Lead', email=lead.email, is_leader=True)
        TeamMember.objects.create(team=team, name='Rohan Mehta', role='Product Designer', email='rohan.mehta@skillbridge.demo')
        TeamMember.objects.create(team=team, name='Kavya Menon', role='Data and QA Engineer', email='kavya.menon@skillbridge.demo')

        FeedPost.objects.filter(author=lead).delete()
        FeedPost.objects.create(
            author=lead,
            team=team,
            body='Team Nova just shipped our first public beta. We learned that the strongest products come from pairing sharp engineering with generous critique.',
            tags=['React', 'Product Design', 'TeamNova'],
            project_url='https://skillbridge.demo/teams/team-nova',
        )
        FeedPost.objects.create(
            author=lead,
            team=team,
            body='We are opening one project slot for a mission-driven team that needs a reliable React and Django partner.',
            tags=['TeamHiring', 'Django', 'React'],
            project_url='https://skillbridge.demo/teams/team-nova',
        )
        self.stdout.write(self.style.SUCCESS('Demo database records are ready.'))
        self.stdout.write('Demo login: amaya.kapoor@skillbridge.demo / DemoPassword123!')
