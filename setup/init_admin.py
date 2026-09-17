"""
Initialize Django admin superuser script
Run with: python manage.py shell < setup/init_admin.py
"""

from django.contrib.auth import get_user_model
from api.models import StudentProfile, ClientProfile, Project, Job
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

# Delete existing test data if exists
User.objects.filter(email__in=['admin@skillbridge.com', 'demo_student@example.com', 'demo_client@example.com']).delete()

print("=" * 80)
print("SKILLBRIDGE - INITIAL DATA SETUP")
print("=" * 80)

# ============================================================================
# CREATE SUPERUSER/ADMIN
# ============================================================================

print("\n[1/5] Creating Admin User...")
admin_user = User.objects.create_superuser(
    email='admin@skillbridge.com',
    password='AdminPassword123!',
    first_name='Admin',
    last_name='User',
)
print(f"✓ Admin created: {admin_user.email}")
print(f"  - URL: http://localhost:8000/admin/")
print(f"  - Email: admin@skillbridge.com")
print(f"  - Password: AdminPassword123!")

# ============================================================================
# CREATE DEMO STUDENT
# ============================================================================

print("\n[2/5] Creating Demo Student...")
demo_student_user = User.objects.create_user(
    email='demo_student@example.com',
    password='StudentPassword123!',
    first_name='John',
    last_name='Doe',
    phone='+1-555-0101',
    role='student',
    bio='Passionate full-stack developer with 3+ years of experience'
)

demo_student = StudentProfile.objects.create(
    user=demo_student_user,
    headline='Full Stack Developer | React & Django Expert',
    bio='I love building scalable web applications with modern technologies. Experienced in React, Node.js, Django, and PostgreSQL.',
    skills=['React', 'Node.js', 'Django', 'PostgreSQL', 'MongoDB', 'Docker', 'AWS'],
    verified_skills=['React', 'Django', 'PostgreSQL'],
    experience_level='advanced',
    availability='part_time',
    hourly_rate=Decimal('75.00'),
    portfolio_url='https://johndoe-portfolio.com',
    github_url='https://github.com/johndoe',
    linkedin_url='https://linkedin.com/in/johndoe',
    rating=4.8,
    total_reviews=15,
    projects_completed=12,
    is_featured=True
)
print(f"✓ Student created: {demo_student_user.email}")
print(f"  - Name: {demo_student_user.get_full_name()}")
print(f"  - Skills: {', '.join(demo_student.skills)}")
print(f"  - Hourly Rate: ${demo_student.hourly_rate}")
print(f"  - Rating: {demo_student.rating}/5.0 ({demo_student.total_reviews} reviews)")

# Create additional sample students
print("\n  Creating additional sample students...")
for i in range(3):
    student_user = User.objects.create_user(
        email=f'student{i+2}@example.com',
        password='StudentPassword123!',
        first_name=f'Student{i+2}',
        last_name='User',
        role='student'
    )
    StudentProfile.objects.create(
        user=student_user,
        headline=f'Developer {i+2}',
        skills=['React', 'Python', 'JavaScript'],
        experience_level='intermediate',
        availability='full_time',
        hourly_rate=Decimal('50.00') + Decimal(i * 10),
        rating=4.0 + (i * 0.3),
        total_reviews=5 + i,
        projects_completed=3 + i,
        is_featured=(i == 0)
    )
    print(f"  ✓ student{i+2}@example.com created")

# ============================================================================
# CREATE DEMO CLIENT
# ============================================================================

print("\n[3/5] Creating Demo Client...")
demo_client_user = User.objects.create_user(
    email='demo_client@example.com',
    password='ClientPassword123!',
    first_name='Jane',
    last_name='Smith',
    phone='+1-555-0201',
    role='client',
    bio='CEO at TechCorp, leading digital transformation'
)

demo_client = ClientProfile.objects.create(
    user=demo_client_user,
    company_name='TechCorp Solutions',
    industry='tech',
    company_size='medium',
    company_description='We build innovative software solutions for Fortune 500 companies.',
    company_website='https://techcorp.com',
    location='San Francisco, CA',
    budget_range_min=Decimal('5000.00'),
    budget_range_max=Decimal('50000.00'),
    projects_posted=8,
    rating=4.9,
    is_verified=True
)
print(f"✓ Client created: {demo_client_user.email}")
print(f"  - Company: {demo_client.company_name}")
print(f"  - Industry: {demo_client.get_industry_display()}")
print(f"  - Budget Range: ${demo_client.budget_range_min} - ${demo_client.budget_range_max}")
print(f"  - Verified: {demo_client.is_verified}")

# Create additional sample clients
print("\n  Creating additional sample clients...")
for i in range(2):
    client_user = User.objects.create_user(
        email=f'client{i+2}@example.com',
        password='ClientPassword123!',
        first_name=f'Client{i+2}',
        last_name='Company',
        role='client'
    )
    ClientProfile.objects.create(
        user=client_user,
        company_name=f'Company {i+2} Inc',
        industry='tech' if i % 2 == 0 else 'finance',
        company_size='medium',
        budget_range_min=Decimal('3000.00'),
        budget_range_max=Decimal('20000.00'),
        projects_posted=3 + i
    )
    print(f"  ✓ client{i+2}@example.com created")

# ============================================================================
# CREATE DEMO PROJECTS
# ============================================================================

print("\n[4/5] Creating Demo Projects...")

projects_data = [
    {
        'title': 'E-Commerce Platform Redesign',
        'description': 'Modernize our e-commerce platform with React and Node.js. We need a developer who can handle both frontend and backend.',
        'category': 'web_dev',
        'required_skills': ['React', 'Node.js', 'MongoDB'],
        'budget_min': Decimal('5000.00'),
        'budget_max': Decimal('8000.00'),
        'duration_weeks': 6,
        'experience_level': 'advanced',
    },
    {
        'title': 'Mobile App Development - iOS & Android',
        'description': 'Build a cross-platform mobile app for our new fitness tracking service using React Native.',
        'category': 'mobile_dev',
        'required_skills': ['React Native', 'Firebase', 'TypeScript'],
        'budget_min': Decimal('8000.00'),
        'budget_max': Decimal('12000.00'),
        'duration_weeks': 8,
        'experience_level': 'advanced',
    },
    {
        'title': 'Dashboard Design & Frontend Implementation',
        'description': 'Create a beautiful and responsive admin dashboard with React and Tailwind CSS.',
        'category': 'design',
        'required_skills': ['React', 'Tailwind CSS', 'UI/UX'],
        'budget_min': Decimal('2000.00'),
        'budget_max': Decimal('4000.00'),
        'duration_weeks': 3,
        'experience_level': 'intermediate',
    },
    {
        'title': 'Django REST API Development',
        'description': 'Build a robust REST API using Django and PostgreSQL for our data analytics platform.',
        'category': 'web_dev',
        'required_skills': ['Django', 'PostgreSQL', 'DRF'],
        'budget_min': Decimal('4000.00'),
        'budget_max': Decimal('6000.00'),
        'duration_weeks': 4,
        'experience_level': 'intermediate',
    },
    {
        'title': 'DevOps & Infrastructure Setup',
        'description': 'Set up CI/CD pipelines and deploy applications on AWS using Docker and Kubernetes.',
        'category': 'devops',
        'required_skills': ['Docker', 'Kubernetes', 'AWS', 'CI/CD'],
        'budget_min': Decimal('3000.00'),
        'budget_max': Decimal('5000.00'),
        'duration_weeks': 2,
        'experience_level': 'advanced',
    },
    {
        'title': 'Data Science & Machine Learning',
        'description': 'Build ML models for predictive analytics using Python, TensorFlow, and Scikit-learn.',
        'category': 'data_science',
        'required_skills': ['Python', 'TensorFlow', 'Pandas', 'SQL'],
        'budget_min': Decimal('6000.00'),
        'budget_max': Decimal('10000.00'),
        'duration_weeks': 5,
        'experience_level': 'advanced',
    },
]

for idx, project_data in enumerate(projects_data):
    project = Project.objects.create(
        client=demo_client,
        status='open',
        budget_type='fixed',
        rating=4.5 + (idx * 0.1),
        applications_count=3 + idx,
        is_featured=(idx < 3),
        deadline=timezone.now() + timedelta(days=30),
        **project_data
    )
    print(f"✓ Project {idx+1}: {project.title}")

print(f"\n  Total projects created: {Project.objects.count()}")

# ============================================================================
# CREATE DEMO JOBS
# ============================================================================

print("\n[5/5] Creating Demo Jobs...")

jobs_data = [
    {
        'title': 'Senior React Developer',
        'description': 'We are looking for an experienced React developer to join our team full-time.',
        'job_type': 'full_time',
        'required_skills': ['React', 'TypeScript', 'Redux'],
        'location': 'San Francisco, CA',
        'salary_min': Decimal('120000.00'),
        'salary_max': Decimal('160000.00'),
        'experience_level': 'advanced',
    },
    {
        'title': 'Django Backend Developer (Remote)',
        'description': 'Remote position: Build scalable backend systems with Django and PostgreSQL.',
        'job_type': 'full_time',
        'required_skills': ['Django', 'PostgreSQL', 'REST APIs'],
        'location': 'Remote',
        'salary_min': Decimal('100000.00'),
        'salary_max': Decimal('140000.00'),
        'experience_level': 'intermediate',
    },
    {
        'title': 'Frontend Contractor - Part Time',
        'description': 'Contract work: 20 hours/week. Build responsive UIs with React and Tailwind.',
        'job_type': 'contract',
        'required_skills': ['React', 'CSS', 'JavaScript'],
        'location': 'San Francisco, CA',
        'salary_min': Decimal('60.00'),
        'salary_max': Decimal('80.00'),
        'experience_level': 'intermediate',
    },
    {
        'title': 'Python Intern - Data Science',
        'description': 'Internship: Learn data science and machine learning with our team.',
        'job_type': 'internship',
        'required_skills': ['Python', 'SQL', 'Data Analysis'],
        'location': 'San Francisco, CA',
        'salary_min': Decimal('20.00'),
        'salary_max': Decimal('25.00'),
        'experience_level': 'beginner',
    },
]

for idx, job_data in enumerate(jobs_data):
    job = Job.objects.create(
        client=demo_client,
        status='open',
        applications_count=2 + idx,
        deadline=timezone.now() + timedelta(days=45),
        **job_data
    )
    print(f"✓ Job {idx+1}: {job.title}")

print(f"\n  Total jobs created: {Job.objects.count()}")

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 80)
print("SETUP COMPLETE!")
print("=" * 80)

print("\n📊 DATA SUMMARY:")
print(f"  • Users: {User.objects.count()}")
print(f"  • Students: {StudentProfile.objects.count()}")
print(f"  • Clients: {ClientProfile.objects.count()}")
print(f"  • Projects: {Project.objects.count()}")
print(f"  • Jobs: {Job.objects.count()}")

print("\n🔐 DEFAULT CREDENTIALS:")
print("  Admin:")
print("    Email: admin@skillbridge.com")
print("    Password: AdminPassword123!")
print("  ")
print("  Demo Student:")
print("    Email: demo_student@example.com")
print("    Password: StudentPassword123!")
print("  ")
print("  Demo Client:")
print("    Email: demo_client@example.com")
print("    Password: ClientPassword123!")

print("\n🌐 ENDPOINTS:")
print("  • Admin: http://localhost:8000/admin/")
print("  • API: http://localhost:8000/api/")
print("  • Projects: http://localhost:8000/api/projects/")
print("  • Students: http://localhost:8000/api/students/")
print("  • Clients: http://localhost:8000/api/clients/")
print("  • Jobs: http://localhost:8000/api/jobs/")

print("\n✨ Next Steps:")
print("  1. Run: python manage.py runserver")
print("  2. Visit: http://localhost:8000/admin/")
print("  3. Login with admin credentials")
print("  4. Test API endpoints with Postman or cURL")
print("  5. Connect your React frontend to http://localhost:8000/api/")

print("\n" + "=" * 80)
