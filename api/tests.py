from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from api.models import StudentProfile, ClientProfile, Project, Job, Application, Team
from decimal import Decimal

User = get_user_model()


# ============================================================================
# AUTHENTICATION TESTS
# ============================================================================

class StudentRegistrationTestCase(APITestCase):
    """Test student registration"""
    
    def test_student_registration(self):
        """Test successful student registration"""
        data = {
            'email': 'student@example.com',
            'password': 'TestPassword123!',
            'first_name': 'John',
            'last_name': 'Doe',
            'headline': 'Full Stack Developer',
            'bio': 'Passionate about web development',
            'skills': ['React', 'Django', 'PostgreSQL'],
            'experience_level': 'intermediate',
            'availability': 'part_time',
            'hourly_rate': '50.00'
        }
        response = self.client.post('/api/auth/register/student/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        
        # Verify user was created
        user = User.objects.get(email='student@example.com')
        self.assertEqual(user.role, 'student')
        self.assertTrue(StudentProfile.objects.filter(user=user).exists())
    
    def test_student_registration_password_mismatch(self):
        """Test registration fails with mismatched passwords"""
        data = {
            'email': 'student@example.com',
            'password': 'TestPassword123!',
            'password2': 'DifferentPassword123!',
            'first_name': 'John',
            'last_name': 'Doe',
            'experience_level': 'beginner',
            'availability': 'full_time'
        }
        response = self.client.post('/api/auth/register/student/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_student_email_returns_validation_error(self):
        User.objects.create_user(email='existing@example.com', password='TestPassword123!', role='student')
        response = self.client.post('/api/auth/register/student/', {
            'email': 'EXISTING@example.com',
            'password': 'TestPassword123!',
            'first_name': 'Existing',
            'last_name': 'Student',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already exists', str(response.data).lower())


class ClientRegistrationTestCase(APITestCase):
    """Test client registration"""
    
    def test_client_registration(self):
        """Test successful client registration"""
        data = {
            'email': 'client@example.com',
            'password': 'TestPassword123!',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'company_name': 'TechCorp Inc',
            'industry': 'tech',
            'company_size': 'medium',
            'budget_range_min': '1000.00',
            'budget_range_max': '5000.00'
        }
        response = self.client.post('/api/auth/register/client/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        
        # Verify user was created
        user = User.objects.get(email='client@example.com')
        self.assertEqual(user.role, 'client')
        self.assertTrue(ClientProfile.objects.filter(user=user).exists())


class CourseResumeAndTeamTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='team-owner@example.com',
            password='TestPassword123!',
            first_name='Team',
            last_name='Owner',
            role='student',
        )
        StudentProfile.objects.create(user=self.user)
        self.client.force_authenticate(user=self.user)

    def test_student_fields_persist_and_resume_upload_is_returned(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        response = self.client.post('/api/auth/register/student/', {
            'email': 'new-student@example.com',
            'password': 'TestPassword123!',
            'password2': 'TestPassword123!',
            'first_name': 'New',
            'last_name': 'Student',
            'course': 'BCA',
            'branch': '',
            'university_name': 'Example University',
            'languages_known': '["Hindi"]',
            'resume': SimpleUploadedFile('resume.pdf', b'%PDF-1.4 test', content_type='application/pdf'),
        }, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        profile = StudentProfile.objects.get(user__email='new-student@example.com')
        self.assertEqual(profile.course, 'BCA')
        self.assertEqual(profile.university_name, 'Example University')
        self.assertEqual(profile.languages_known, ['Hindi'])
        self.assertTrue(profile.resume.name.endswith('.pdf'))

    def test_team_is_searchable_after_creation(self):
        response = self.client.post('/api/teams/', {
            'name': 'Database Builders',
            'college': 'Example University',
            'description': 'A team building useful products.',
            'skills': ['React', 'Django'],
            'availability': 'taking_projects',
            'members': [{'name': 'Team Owner', 'role': 'Lead', 'email': 'team-owner@example.com'}],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.client.force_authenticate(user=None)
        search = self.client.get('/api/teams/?search=Database')
        self.assertEqual(search.status_code, status.HTTP_200_OK)
        items = search.data['results'] if isinstance(search.data, dict) else search.data
        self.assertTrue(any(item['name'] == 'Database Builders' for item in items))


class ProjectMatchingTestCase(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(email='matching-client@example.com', password='TestPassword123!', role='client')
        self.client_profile = ClientProfile.objects.create(user=self.client_user, company_name='Matching Co', industry='tech', company_size='startup')
        self.student_user = User.objects.create_user(email='matching-student@example.com', password='TestPassword123!', role='student')
        self.student_profile = StudentProfile.objects.create(user=self.student_user, skills=['React', 'Django', 'PostgreSQL'], tech_stack=['React', 'Django', 'PostgreSQL'], headline='Full Stack Developer')

    def test_real_project_match_and_student_response_persist(self):
        self.client.force_authenticate(user=self.client_user)
        created = self.client.post('/api/projects/', {
            'title': 'Real React Django Project',
            'description': 'Build a production web application.',
            'category': 'Web Development',
            'required_skills': ['React', 'Django', 'PostgreSQL'],
            'budget_min': '1000.00',
            'experience_level': 'intermediate',
        }, format='json')
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        project_id = created.data['id']

        self.client.force_authenticate(user=self.student_user)
        matched = self.client.get('/api/projects/matched/')
        self.assertEqual(matched.status_code, status.HTTP_200_OK)
        self.assertEqual(matched.data[0]['project']['id'], project_id)
        application = self.client.post('/api/applications/', {'project': project_id, 'cover_letter': 'Relevant experience.'}, format='json')
        self.assertEqual(application.status_code, status.HTTP_201_CREATED)
        accepted = self.client.patch(f"/api/applications/{application.data['id']}/accept/", {}, format='json')
        self.assertEqual(accepted.status_code, status.HTTP_200_OK)
        self.assertEqual(accepted.data['status'], 'accepted')
        duplicate = self.client.patch(f"/api/applications/{application.data['id']}/accept/", {}, format='json')
        self.assertEqual(duplicate.status_code, status.HTTP_409_CONFLICT)


class ResumeReplacementTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='resume-owner@example.com', password='TestPassword123!', role='student')
        self.profile = StudentProfile.objects.create(user=self.user)
        self.client.force_authenticate(user=self.user)

    def test_invalid_and_valid_resume_replacement(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        invalid = self.client.patch(f'/api/students/{self.profile.id}/', {'resume': SimpleUploadedFile('resume.txt', b'not pdf', content_type='text/plain')}, format='multipart')
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)
        valid = self.client.patch(f'/api/students/{self.profile.id}/', {'resume': SimpleUploadedFile('resume.pdf', b'%PDF-1.4 test', content_type='application/pdf')}, format='multipart')
        self.assertEqual(valid.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.resume.name.endswith('.pdf'))


class LoginTestCase(APITestCase):
    """Test user login"""
    
    def setUp(self):
        """Create a test user"""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User',
            role='student'
        )
        StudentProfile.objects.create(user=self.user)
    
    def test_login_success(self):
        """Test successful login"""
        data = {
            'email': 'test@example.com',
            'password': 'TestPassword123!'
        }
        response = self.client.post('/api/auth/login/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
    
    def test_login_invalid_password(self):
        """Test login with invalid password"""
        data = {
            'email': 'test@example.com',
            'password': 'WrongPassword123!'
        }
        response = self.client.post('/api/auth/login/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ============================================================================
# STUDENT PROFILE TESTS
# ============================================================================

class StudentProfileTestCase(APITestCase):
    """Test student profile endpoints"""
    
    def setUp(self):
        """Create test user and authenticate"""
        self.user = User.objects.create_user(
            email='student@example.com',
            password='TestPassword123!',
            first_name='John',
            last_name='Doe',
            role='student'
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.user,
            headline='Full Stack Developer',
            skills=['React', 'Django'],
            experience_level='intermediate',
            availability='part_time',
            hourly_rate=Decimal('50.00')
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
    
    def test_get_my_profile(self):
        """Test getting own profile"""
        response = self.client.get('/api/students/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['email'], 'student@example.com')
    
    def test_update_profile(self):
        """Test updating profile"""
        data = {
            'headline': 'Senior Full Stack Developer',
            'hourly_rate': '75.00'
        }
        response = self.client.patch(f'/api/students/{self.student_profile.id}/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['headline'], 'Senior Full Stack Developer')
    
    def test_leaderboard(self):
        """Test leaderboard endpoint"""
        response = self.client.get('/api/students/leaderboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ============================================================================
# PROJECT TESTS
# ============================================================================

class ProjectTestCase(APITestCase):
    """Test project endpoints"""
    
    def setUp(self):
        """Create test client and project"""
        self.client_user = User.objects.create_user(
            email='client@example.com',
            password='TestPassword123!',
            first_name='Jane',
            last_name='Smith',
            role='client'
        )
        self.client_profile = ClientProfile.objects.create(
            user=self.client_user,
            company_name='TechCorp Inc',
            industry='tech',
            company_size='medium'
        )
        
        self.project = Project.objects.create(
            client=self.client_profile,
            title='Build React App',
            description='Create a React dashboard',
            category='web_dev',
            status='open',
            budget_min=Decimal('1000.00'),
            budget_max=Decimal('2000.00'),
            experience_level='intermediate',
            required_skills=['React', 'Node.js']
        )
        
        self.client_obj = APIClient()
        self.client_obj.force_authenticate(user=self.client_user)
    
    def test_list_projects(self):
        """Test listing projects"""
        response = self.client_obj.get('/api/projects/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_get_project_detail(self):
        """Test getting project detail"""
        response = self.client_obj.get(f'/api/projects/{self.project.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Build React App')
    
    def test_create_project(self):
        """Test creating project"""
        data = {
            'title': 'Build Mobile App',
            'description': 'Create iOS/Android app',
            'category': 'mobile_dev',
            'budget_min': '2000.00',
            'budget_max': '3000.00',
            'experience_level': 'advanced',
            'required_skills': ['React Native', 'Firebase']
        }
        response = self.client_obj.post('/api/projects/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Project.objects.count(), 2)
    
    def test_featured_projects(self):
        """Test getting featured projects"""
        self.project.is_featured = True
        self.project.save()
        response = self.client_obj.get('/api/projects/featured/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ============================================================================
# APPLICATION TESTS
# ============================================================================

class ApplicationTestCase(APITestCase):
    """Test application endpoints"""
    
    def setUp(self):
        """Create test student, client, project"""
        # Create student
        self.student_user = User.objects.create_user(
            email='student@example.com',
            password='TestPassword123!',
            role='student'
        )
        self.student_profile = StudentProfile.objects.create(user=self.student_user)
        
        # Create client and project
        self.client_user = User.objects.create_user(
            email='client@example.com',
            password='TestPassword123!',
            role='client'
        )
        self.client_profile = ClientProfile.objects.create(
            user=self.client_user,
            company_name='TechCorp'
        )
        
        self.project = Project.objects.create(
            client=self.client_profile,
            title='Test Project',
            description='Test',
            category='web_dev',
            budget_min=Decimal('1000.00'),
            experience_level='intermediate'
        )
        
        self.client_obj = APIClient()
        self.client_obj.force_authenticate(user=self.student_user)
    
    def test_apply_to_project(self):
        """Test applying to project"""
        data = {
            'project': self.project.id,
            'cover_letter': 'I am interested in this project',
            'proposed_rate': '50.00'
        }
        response = self.client_obj.post('/api/applications/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Application.objects.filter(student=self.student_profile).exists())
    
    def test_duplicate_application(self):
        """Test cannot apply twice to same project"""
        Application.objects.create(
            student=self.student_profile,
            project=self.project,
            cover_letter='First application'
        )
        
        data = {
            'project': self.project.id,
            'cover_letter': 'Second application',
        }
        response = self.client_obj.post('/api/applications/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ============================================================================
# MESSAGE TESTS
# ============================================================================

class MessageTestCase(APITestCase):
    """Test messaging endpoints"""
    
    def setUp(self):
        """Create two test users"""
        self.user1 = User.objects.create_user(
            email='user1@example.com',
            password='TestPassword123!',
            role='student'
        )
        self.user2 = User.objects.create_user(
            email='user2@example.com',
            password='TestPassword123!',
            role='student'
        )
        
        self.client_obj = APIClient()
        self.client_obj.force_authenticate(user=self.user1)
    
    def test_send_message(self):
        """Test sending message"""
        from api.models import Message
        data = {
            'recipient': self.user2.id,
            'content': 'Hello, how are you?'
        }
        response = self.client_obj.post('/api/messages/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Message.objects.filter(sender=self.user1).exists())


# ============================================================================
# PERMISSION TESTS
# ============================================================================

class PermissionTestCase(APITestCase):
    """Test permission enforcement"""
    
    def setUp(self):
        """Create test users"""
        self.student = User.objects.create_user(
            email='student@example.com',
            password='TestPassword123!',
            role='student'
        )
        self.client_user = User.objects.create_user(
            email='client@example.com',
            password='TestPassword123!',
            role='client'
        )
        
        StudentProfile.objects.create(user=self.student)
        self.client_profile = ClientProfile.objects.create(
            user=self.client_user,
            company_name='TechCorp'
        )
    
    def test_client_can_create_project(self):
        """Test only clients can create projects"""
        client = APIClient()
        client.force_authenticate(user=self.client_user)
        
        data = {
            'title': 'Test Project',
            'description': 'Test',
            'category': 'web_dev',
            'budget_min': '1000.00',
            'experience_level': 'intermediate'
        }
        response = client.post('/api/projects/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_student_cannot_create_project(self):
        """Test students cannot create projects"""
        client = APIClient()
        client.force_authenticate(user=self.student)
        
        data = {
            'title': 'Test Project',
            'description': 'Test',
            'category': 'web_dev',
            'budget_min': '1000.00',
            'experience_level': 'intermediate'
        }
        response = client.post('/api/projects/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_unauthenticated_cannot_create(self):
        """Test unauthenticated users cannot create"""
        client = APIClient()
        
        data = {
            'title': 'Test Project',
            'description': 'Test',
            'category': 'web_dev',
            'budget_min': '1000.00',
            'experience_level': 'intermediate'
        }
        response = client.post('/api/projects/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)