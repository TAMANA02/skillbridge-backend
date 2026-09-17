from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
import uuid

class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The email field is required.')
        email = self.normalize_email(email)
        extra_fields.setdefault('username', email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(email, password, **extra_fields)


# Custom User Model
class User(AbstractUser):

    ROLE_CHOICES = [
        ('student', 'Student'),
        ('client', 'Client'),
        ('admin', 'Admin'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        ordering = ['-created_at']

        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"
    
    @property
    def is_student(self):
        return self.role == 'student'
    
    @property
    def is_client(self):
        return self.role == 'client'


# Student Profile
class StudentProfile(models.Model):
    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ]
    
    AVAILABILITY_CHOICES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    college = models.ForeignKey('College', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    student_id = models.CharField(max_length=100, blank=True)
    university_name = models.CharField(max_length=200, blank=True)
    course = models.CharField(max_length=200, blank=True)
    branch = models.CharField(max_length=150, blank=True)
    current_year = models.CharField(max_length=50, blank=True)
    graduation_year = models.CharField(max_length=10, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    is_verified_student = models.BooleanField(default=False, help_text="Verified via college email/ID")
    headline = models.CharField(max_length=200, blank=True)
    bio = models.TextField(blank=True)
    career_objective = models.TextField(blank=True)
    tech_stack = models.JSONField(default=list)
    languages_known = models.JSONField(default=list)
    experience = models.JSONField(default=list)
    skills = models.JSONField(default=list)  # ["React", "Python", "Django"]
    experience_level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='beginner')
    availability = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default='part_time')
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    portfolio_url = models.URLField(blank=True, null=True)
    github_url = models.URLField(blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    behance_url = models.URLField(blank=True, null=True)
    dribbble_url = models.URLField(blank=True, null=True)
    resume = models.FileField(upload_to='resumes/', blank=True, null=True)
    profile_photo = models.ImageField(
        upload_to='profile_photos/',
        blank=True,
        null=True
    )
    college_id_document = models.FileField(
    upload_to='college_ids/',
    blank=True,
    null=True
)
    cover_image = models.ImageField(upload_to='cover_images/', blank=True, null=True)
    rating = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)])
    total_reviews = models.IntegerField(default=0)
    projects_completed = models.IntegerField(default=0)
    verified_skills = models.JSONField(default=list)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-rating', '-projects_completed']
        indexes = [
            models.Index(fields=['rating']),
            models.Index(fields=['experience_level']),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name()} - Student Profile"


# Client Profile
class ClientProfile(models.Model):
    INDUSTRY_CHOICES = [
        ('tech', 'Technology'),
        ('finance', 'Finance'),
        ('healthcare', 'Healthcare'),
        ('ecommerce', 'E-Commerce'),
        ('education', 'Education'),
        ('other', 'Other'),
    ]
    
    SIZE_CHOICES = [
        ('startup', 'Startup'),
        ('small', 'Small'),
        ('medium', 'Medium'),
        ('large', 'Large'),
        ('enterprise', 'Enterprise'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')
    company_name = models.CharField(max_length=255)
    industry = models.CharField(max_length=50, choices=INDUSTRY_CHOICES)
    company_size = models.CharField(max_length=20, choices=SIZE_CHOICES)
    company_logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    company_description = models.TextField(blank=True)
    company_website = models.URLField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True)
    budget_range_min = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    budget_range_max = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    projects_posted = models.IntegerField(default=0)
    rating = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)])
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.company_name} - Client Profile"


# Project Model
class Project(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    CATEGORY_CHOICES = [
        ('web_dev', 'Web Development'),
        ('mobile_dev', 'Mobile Development'),
        ('design', 'Design'),
        ('data_science', 'Data Science'),
        ('devops', 'DevOps'),
        ('other', 'Other'),
    ]
    
    BUDGET_TYPE_CHOICES = [
        ('fixed', 'Fixed Price'),
        ('hourly', 'Hourly Rate'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    required_skills = models.JSONField(default=list)  # ["React", "Node.js", "MongoDB"]
    budget_type = models.CharField(max_length=20, choices=BUDGET_TYPE_CHOICES, default='fixed')
    budget_min = models.DecimalField(max_digits=12, decimal_places=2)
    budget_max = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    duration_weeks = models.IntegerField(blank=True, null=True)
    experience_level = models.CharField(max_length=20, choices=StudentProfile.LEVEL_CHOICES)
    cover_image = models.ImageField(upload_to='project_covers/', blank=True, null=True)
    attachments = models.JSONField(default=list)  # URLs to files
    assigned_student = models.ForeignKey(StudentProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_projects')
    assigned_team = models.ForeignKey('Team', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_projects')
    rating = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)])
    applications_count = models.IntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deadline = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['category']),
            models.Index(fields=['is_featured']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"


# Job Listing Model
class Job(models.Model):
    JOB_TYPE_CHOICES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name='jobs')
    title = models.CharField(max_length=255)
    description = models.TextField()
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES)
    required_skills = models.JSONField(default=list)
    location = models.CharField(max_length=255, blank=True)
    salary_min = models.DecimalField(max_digits=12, decimal_places=2)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    experience_level = models.CharField(max_length=20, choices=StudentProfile.LEVEL_CHOICES)
    status = models.CharField(max_length=20, choices=Project.STATUS_CHOICES, default='open')
    applications_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deadline = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['job_type']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.get_job_type_display()}"


# Application Model (Student applies to Project/Job)
class Application(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='applications')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True, related_name='applications')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, null=True, blank=True, related_name='applications')
    cover_letter = models.TextField()
    proposed_rate = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    proposed_duration = models.IntegerField(blank=True, null=True)  # in days
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [('student', 'project'), ('student', 'job')]
        ordering = ['-created_at']
    
    def __str__(self):
        target = self.project or self.job
        return f"{self.student.user.get_full_name()} -> {target} ({self.get_status_display()})"


# Message/Chat Model
class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')
    job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')
    content = models.TextField()
    attachments = models.JSONField(default=list)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sender', 'recipient']),
            models.Index(fields=['is_read']),
        ]
    
    def __str__(self):
        return f"{self.sender.email} -> {self.recipient.email}"


# Review/Rating Model
class Review(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_given')
    reviewee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_received')
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')
    job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [('reviewer', 'reviewee', 'project'), ('reviewer', 'reviewee', 'job')]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Review by {self.reviewer.email} - {self.rating}/5"


# Notification Model
class Notification(models.Model):
    TYPE_CHOICES = [
        ('application', 'New Application'),
        ('message', 'New Message'),
        ('project_update', 'Project Update'),
        ('job_update', 'Job Update'),
        ('review', 'New Review'),
        ('invite', 'Project Invite'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    related_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications_from')
    related_project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    related_job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    action_url = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
        ]
    
    def __str__(self):
        return f"Notification for {self.user.email} - {self.get_notification_type_display()}"


class College(models.Model):
    """A college/institution. Backs the college leaderboard and per-college profile page."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    location = models.CharField(max_length=255, blank=True)
    logo = models.ImageField(upload_to='college_logos/', blank=True, null=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True, null=True)
    email_domain = models.CharField(max_length=100, blank=True, help_text="e.g. xyzcollege.edu - used for student verification")
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [models.Index(fields=['name'])]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or 'college'
            slug = base_slug
            suffix = 2
            while College.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{suffix}'
                suffix += 1
            self.slug = slug
        super().save(*args, **kwargs)

    # --- Aggregated, always-fresh leaderboard stats ---
    @property
    def total_developers(self):
        return self.students.count()

    @property
    def total_teams(self):
        return self.teams.count()

    @property
    def projects_completed(self):
        student_ids = self.students.values_list('id', flat=True)
        team_ids = self.teams.values_list('id', flat=True)
        return Project.objects.filter(
            models.Q(assigned_student_id__in=student_ids) | models.Q(assigned_team_id__in=team_ids),
            status='completed'
        ).distinct().count()

    @property
    def client_rating(self):
        student_avg = self.students.aggregate(avg=models.Avg('rating'))['avg'] or 0
        team_avg = self.teams.aggregate(avg=models.Avg('rating'))['avg'] or 0
        values = [v for v in [student_avg, team_avg] if v]
        return round(sum(values) / len(values), 2) if values else 0.0

    @property
    def success_rate(self):
        student_ids = self.students.values_list('id', flat=True)
        team_ids = self.teams.values_list('id', flat=True)
        qs = Project.objects.filter(
            models.Q(assigned_student_id__in=student_ids) | models.Q(assigned_team_id__in=team_ids)
        ).exclude(status__in=['draft', 'open'])
        total = qs.count()
        if total == 0:
            return 0.0
        return round((qs.filter(status='completed').count() / total) * 100, 1)

    @property
    def performance_score(self):
        """Rewards quality + activity, not just headcount, so a huge college doesn't auto-win."""
        score = (
            self.client_rating * 20 +
            min(self.projects_completed, 100) * 1.5 +
            self.success_rate * 0.3 +
            min(self.total_developers, 50) * 0.5
        )
        return round(score, 1)


class Team(models.Model):
    VERIFICATION_CHOICES = [
        ('pending', 'Pending verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    AVAILABILITY_CHOICES = [
        ('taking_projects', 'Taking new projects'),
        ('next_month', 'Available next month'),
        ('at_capacity', 'Currently at capacity'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    leader = models.ForeignKey(User, on_delete=models.PROTECT, related_name='led_teams')
    college = models.ForeignKey(College, on_delete=models.SET_NULL, null=True, blank=True, related_name='teams')
    description = models.TextField()
    skills = models.JSONField(default=list)
    website_url = models.URLField(blank=True, null=True)
    github_url = models.URLField(blank=True, null=True)
    availability = models.CharField(max_length=30, choices=AVAILABILITY_CHOICES, default='taking_projects')
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_CHOICES, default='pending')
    completed_projects = models.PositiveIntegerField(default=0)
    rating = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)])
    success_rate = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-rating', '-completed_projects', '-created_at']
        indexes = [models.Index(fields=['college']), models.Index(fields=['verification_status'])]

    def __str__(self):
        return self.name


class TeamMember(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='team_memberships')
    name = models.CharField(max_length=160)
    role = models.CharField(max_length=160)
    email = models.EmailField(blank=True)
    is_leader = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_leader', 'created_at']
        constraints = [models.UniqueConstraint(fields=['team', 'email'], condition=~models.Q(email=''), name='unique_team_member_email')]

    def __str__(self):
        return f'{self.name} - {self.team.name}'


class FeedPost(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feed_posts')
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='feed_posts')
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name='feed_posts')
    body = models.TextField(max_length=5000)
    tags = models.JSONField(default=list)
    image_url = models.URLField(blank=True)
    project_url = models.URLField(blank=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['-created_at']), models.Index(fields=['is_published'])]

    def __str__(self):
        return f'{self.author.get_full_name()} - {self.body[:40]}'


class FeedComment(models.Model):
    post = models.ForeignKey(FeedPost, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feed_comments')
    body = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']


class FeedLike(models.Model):
    post = models.ForeignKey(FeedPost, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feed_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['post', 'user'], name='unique_feed_like')]


class FeedSave(models.Model):
    post = models.ForeignKey(FeedPost, on_delete=models.CASCADE, related_name='saves')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feed_saves')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['post', 'user'], name='unique_feed_save')]


class FeedShare(models.Model):
    post = models.ForeignKey(FeedPost, on_delete=models.CASCADE, related_name='shares')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feed_shares')
    created_at = models.DateTimeField(auto_now_add=True)


class UserFollow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['follower', 'following'], name='unique_user_follow'),
            models.CheckConstraint(check=~models.Q(follower=models.F('following')), name='cannot_follow_self'),
        ]
