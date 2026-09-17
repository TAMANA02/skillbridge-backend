from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import transaction, IntegrityError
from django.utils.text import slugify
import json

from api.models import (
    User, StudentProfile, ClientProfile, Project, Job, 
        Application, Message, Review, Notification,
    College, Team, TeamMember, FeedPost, FeedComment, FeedLike, FeedSave, FeedShare, UserFollow

)


def get_or_create_college(name):
    """Resolve a free-text college name to a real College record (case-insensitive),
    creating one if it doesn't exist yet. Shared by student registration and team registration
    so the college leaderboard aggregates correctly instead of splitting on text variants."""
    name = (name or '').strip()
    if not name:
        return None
    college = College.objects.filter(name__iexact=name).first()
    if college:
        return college
    try:
        with transaction.atomic():
            return College.objects.create(name=name)
    except IntegrityError:
        return College.objects.get(name__iexact=name)


# ============================================================================
# USER & AUTHENTICATION SERIALIZERS
# ============================================================================

class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer for public profiles"""
    class Meta:
        model = User
        fields = [
    'id',
    'email',
    'first_name',
    'last_name',
    'phone',
    'avatar',
    'bio',
    'role',
    'created_at'
]
        read_only_fields = ['id', 'created_at']


class CollegeSerializer(serializers.ModelSerializer):
    """Serializer for the college leaderboard / list view"""
    total_developers = serializers.ReadOnlyField()
    total_teams = serializers.ReadOnlyField()
    projects_completed = serializers.ReadOnlyField()
    client_rating = serializers.ReadOnlyField()
    success_rate = serializers.ReadOnlyField()
    performance_score = serializers.ReadOnlyField()

    class Meta:
        model = College
        fields = [
            'id', 'name', 'slug', 'location', 'logo', 'description', 'website',
            'is_verified', 'total_developers', 'total_teams', 'projects_completed',
            'client_rating', 'success_rate', 'performance_score', 'created_at'
        ]
        read_only_fields = ['id', 'slug', 'is_verified', 'created_at']


class CollegeDetailSerializer(serializers.ModelSerializer):
    """College profile page: stats + top developers + top teams"""
    total_developers = serializers.ReadOnlyField()
    total_teams = serializers.ReadOnlyField()
    projects_completed = serializers.ReadOnlyField()
    client_rating = serializers.ReadOnlyField()
    success_rate = serializers.ReadOnlyField()
    performance_score = serializers.ReadOnlyField()
    top_developers = serializers.SerializerMethodField()
    top_teams = serializers.SerializerMethodField()

    class Meta:
        model = College
        fields = [
            'id', 'name', 'slug', 'location', 'logo', 'description', 'website',
            'email_domain', 'is_verified', 'total_developers', 'total_teams',
            'projects_completed', 'client_rating', 'success_rate', 'performance_score',
            'top_developers', 'top_teams', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'is_verified', 'created_at', 'updated_at']

    def get_top_developers(self, obj):
        students = obj.students.order_by('-rating', '-projects_completed')[:6]
        return StudentProfileSerializer(students, many=True).data

    def get_top_teams(self, obj):
        teams = obj.teams.order_by('-rating', '-completed_projects')[:6]
        return TeamSerializer(teams, many=True).data


class TeamMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    email = serializers.SerializerMethodField()

    def get_email(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and user.is_authenticated and (user == obj.team.leader or user == obj.user):
            return obj.email
        return None

    class Meta:
        model = TeamMember
        fields = ['id', 'user', 'name', 'role', 'email', 'is_leader', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class TeamMemberCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamMember
        fields = ['name', 'role', 'email']
        extra_kwargs = {'email': {'required': False, 'allow_blank': True}}


class TeamSerializer(serializers.ModelSerializer):
    leader = UserSerializer(read_only=True)
    members = TeamMemberSerializer(many=True, read_only=True)
    college_name = serializers.CharField(source='college.name', read_only=True, default=None)
    college_slug = serializers.CharField(source='college.slug', read_only=True, default=None)
    is_verified = serializers.SerializerMethodField()

    def get_is_verified(self, obj):
        return obj.verification_status == 'verified'

    class Meta:
        model = Team
        fields = [
            'id', 'name', 'slug', 'leader', 'college', 'college_name', 'college_slug',
            'description', 'skills', 'website_url', 'github_url', 'availability', 'verification_status',
            'is_verified', 'completed_projects', 'rating', 'success_rate',
            'members', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'leader', 'college', 'verification_status', 'is_verified', 'completed_projects', 'rating', 'success_rate', 'created_at', 'updated_at']


class TeamCreateSerializer(serializers.ModelSerializer):
    # Keep the write contract as a plain college name (what the registration form already sends);
    # it's resolved to a real College record so the leaderboard can aggregate on it.
    college = serializers.CharField(max_length=255, required=True, allow_blank=False)
    members = TeamMemberCreateSerializer(many=True, required=True)

    class Meta:
        model = Team
        fields = ['name', 'college', 'description', 'skills', 'website_url', 'github_url', 'availability', 'members']

    def validate_members(self, members):
        if not members:
            raise serializers.ValidationError('Add at least one team member.')
        emails = [member.get('email', '').lower() for member in members if member.get('email')]
        if len(emails) != len(set(emails)):
            raise serializers.ValidationError('Team member emails must be unique.')
        return members

    @transaction.atomic
    def create(self, validated_data):
        members = validated_data.pop('members')
        request = self.context['request']
        college_name = validated_data.pop('college').strip()
        college = get_or_create_college(college_name)
        base_slug = slugify(validated_data['name']) or 'team'
        slug = base_slug
        suffix = 2
        while Team.objects.filter(slug=slug).exists():
            slug = f'{base_slug}-{suffix}'
            suffix += 1
        team = Team.objects.create(leader=request.user, slug=slug, college=college, **validated_data)
        for index, member in enumerate(members):
            email = member.get('email', '')
            linked_user = User.objects.filter(email__iexact=email).first() if email else None
            TeamMember.objects.create(team=team, user=linked_user, is_leader=index == 0, **member)
            # If the member is a registered student without a college yet, attribute them to this college
            if linked_user and hasattr(linked_user, 'student_profile') and not linked_user.student_profile.college:
                linked_user.student_profile.college = college
                linked_user.student_profile.save(update_fields=['college'])
        return team


class FeedCommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = FeedComment
        fields = ['id', 'author', 'body', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']


class FeedPostSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    comments = FeedCommentSerializer(many=True, read_only=True)
    likes_count = serializers.IntegerField(source='likes.count', read_only=True)
    comments_count = serializers.IntegerField(source='comments.count', read_only=True)
    shares_count = serializers.IntegerField(source='shares.count', read_only=True)
    viewer_liked = serializers.SerializerMethodField()
    viewer_saved = serializers.SerializerMethodField()
    viewer_following = serializers.SerializerMethodField()

    class Meta:
        model = FeedPost
        fields = [
            'id', 'author', 'team', 'project', 'body', 'tags', 'image_url',
            'project_url', 'is_published', 'comments', 'likes_count',
            'comments_count', 'shares_count', 'viewer_liked', 'viewer_saved',
            'viewer_following', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'author', 'is_published', 'comments', 'likes_count', 'comments_count', 'shares_count', 'viewer_liked', 'viewer_saved', 'viewer_following', 'created_at', 'updated_at']

    def _user(self):
        request = self.context.get('request')
        return request.user if request and request.user.is_authenticated else None

    def get_viewer_liked(self, obj):
        user = self._user()
        return bool(user and obj.likes.filter(user=user).exists())

    def get_viewer_saved(self, obj):
        user = self._user()
        return bool(user and obj.saves.filter(user=user).exists())

    def get_viewer_following(self, obj):
        user = self._user()
        return bool(user and UserFollow.objects.filter(follower=user, following=obj.author).exists())


class FeedPostCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedPost
        fields = ['team', 'project', 'body', 'tags', 'image_url', 'project_url']
        extra_kwargs = {'body': {'max_length': 5000}, 'tags': {'required': False}}


class FeedCommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedComment
        fields = ['body']
        extra_kwargs = {'body': {'max_length': 1000}}


class UserDetailSerializer(serializers.ModelSerializer):
    """Detailed user serializer for authenticated users"""
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone', 'avatar', 'bio', 'role', 'is_verified', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration (student & client)"""
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password', 'password2', 'phone', 'role']
    
    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password2'):
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError("Invalid email or password.")
            attrs['user'] = user
        else:
            raise serializers.ValidationError("Must include email and password.")
        return attrs


# ============================================================================
# STUDENT SERIALIZERS
# ============================================================================

class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    college_name = serializers.CharField(
        source='college.name',
        read_only=True,
        default=None
    )
    college_slug = serializers.CharField(
        source='college.slug',
        read_only=True,
        default=None
    )

    class Meta:
        model = StudentProfile
        fields = [
            'id',
            'user',
            'college',
            'college_name',
            'college_slug',

            # Personal
            'student_id',
            'date_of_birth',
            'gender',
            'address',
            'city',
            'state',
            'country',

            # Education
            'university_name',
            'course',
            'branch',
            'current_year',
            'graduation_year',

            # Professional
            'headline',
            'bio',
            'career_objective',
            'skills',
            'tech_stack',
            'languages_known',
            'experience',
            'experience_level',
            'availability',
            'hourly_rate',

            # Links
            'portfolio_url',
            'github_url',
            'linkedin_url',
            'behance_url',
            'dribbble_url',

            # Files
            'resume',
            'profile_photo',
            'college_id_document',
            'cover_image',

            # Statistics
            'is_verified_student',
            'rating',
            'total_reviews',
            'projects_completed',
            'verified_skills',
            'is_featured',

            'created_at',
            'updated_at',
        ]

        read_only_fields = [
            'id',
            'user',
            'is_verified_student',
            'rating',
            'total_reviews',
            'projects_completed',
            'created_at',
            'updated_at',
        ]


class StudentDetailSerializer(serializers.ModelSerializer):
    user = UserDetailSerializer(read_only=True)
    college_name = serializers.CharField(
        source='college.name',
        read_only=True,
        default=None
    )
    college_slug = serializers.CharField(
        source='college.slug',
        read_only=True,
        default=None
    )

    class Meta:
        model = StudentProfile

        fields = [
            'id',
            'user',
            'college',
            'college_name',
            'college_slug',

            'student_id',
            'date_of_birth',
            'gender',
            'address',
            'city',
            'state',
            'country',

            'university_name',
            'course',
            'branch',
            'current_year',
            'graduation_year',

            'headline',
            'bio',
            'career_objective',
            'skills',
            'tech_stack',
            'languages_known',
            'experience',
            'experience_level',
            'availability',
            'hourly_rate',

            'portfolio_url',
            'github_url',
            'linkedin_url',
            'behance_url',
            'dribbble_url',

            'resume',
            'profile_photo',
            'college_id_document',
            'cover_image',

            'is_verified_student',
            'rating',
            'total_reviews',
            'projects_completed',
            'verified_skills',
            'is_featured',

            'created_at',
            'updated_at',
        ]

        read_only_fields = [
            'id',
            'user',
            'is_verified_student',
            'rating',
            'total_reviews',
            'projects_completed',
            'created_at',
            'updated_at',
        ]

    def validate_resume(self, value):
        if value and value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError('Resume must be smaller than 5 MB.')
        if value and getattr(value, 'content_type', '') not in ('application/pdf', 'application/octet-stream'):
            raise serializers.ValidationError('Resume must be a PDF file.')
        return value

class StudentRegistrationSerializer(serializers.Serializer):
    """Multi-step student registration"""

    # =========================
    # STEP 1: BASIC INFO
    # =========================
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )
    password2 = serializers.CharField(
        write_only=True,
        required=False
    )

    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)

    # =========================
    # PERSONAL INFORMATION
    # =========================
    phone = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True
    )

    date_of_birth = serializers.DateField(
        required=False,
        allow_null=True
    )

    gender = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True
    )

    address = serializers.CharField(
        required=False,
        allow_blank=True
    )

    city = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True
    )

    state = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True
    )

    country = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True
    )

    # =========================
    # EDUCATION
    # =========================
    college = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True
    )

    student_id = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True
    )

    university_name = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True
    )

    course = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True
    )

    branch = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True
    )

    current_year = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True
    )

    graduation_year = serializers.CharField(
        max_length=10,
        required=False,
        allow_blank=True
    )

    # =========================
    # PROFESSIONAL PROFILE
    # =========================
    headline = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True
    )

    bio = serializers.CharField(
        required=False,
        allow_blank=True
    )

    career_objective = serializers.CharField(
        required=False,
        allow_blank=True
    )

    skills = serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        required=False
    )

    tech_stack = serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        required=False
    )

    languages_known = serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        required=False
    )

    # =========================
    # EXPERIENCE
    # =========================
    experience = serializers.ListField(
        required=False
    )

    experience_level = serializers.ChoiceField(
        choices=StudentProfile.LEVEL_CHOICES,
        required=False,
        default='beginner'
    )

    availability = serializers.ChoiceField(
        choices=StudentProfile.AVAILABILITY_CHOICES,
        required=False,
        default='part_time'
    )

    hourly_rate = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True
    )

    # =========================
    # SOCIAL / PORTFOLIO LINKS
    # =========================
    portfolio_url = serializers.URLField(
        required=False,
        allow_blank=True
    )

    github_url = serializers.URLField(
        required=False,
        allow_blank=True
    )

    linkedin_url = serializers.URLField(
        required=False,
        allow_blank=True
    )

    behance_url = serializers.URLField(
        required=False,
        allow_blank=True
    )

    dribbble_url = serializers.URLField(
        required=False,
        allow_blank=True
    )

    # =========================
    # FILES
    # =========================
    resume = serializers.FileField(
        required=False,
        allow_null=True
    )

    profile_photo = serializers.ImageField(
        required=False,
        allow_null=True
    )

    college_id_document = serializers.FileField(
        required=False,
        allow_null=True
    )

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists. Please log in or use another email.')
        return value

    def validate_resume(self, value):
        if value and value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError('Resume must be smaller than 5 MB.')
        if value and getattr(value, 'content_type', '') not in ('application/pdf', 'application/octet-stream'):
            raise serializers.ValidationError('Resume must be a PDF file.')
        return value

    # =========================
    # VALIDATION
    # =========================
    def validate(self, attrs):

        for field in ('skills', 'tech_stack', 'languages_known', 'experience'):
            value = attrs.get(field)
            if isinstance(value, list) and len(value) == 1 and isinstance(value[0], str):
                try:
                    parsed_item = json.loads(value[0])
                except (TypeError, ValueError):
                    parsed_item = None
                if isinstance(parsed_item, list):
                    attrs[field] = parsed_item
                    continue
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                except (TypeError, ValueError):
                    raise serializers.ValidationError({field: 'Must be a valid JSON list.'})
                if not isinstance(parsed, list):
                    raise serializers.ValidationError({field: 'Must be a list.'})
                attrs[field] = parsed

        password = attrs.get('password')
        password2 = attrs.get('password2')

        if password2 and password != password2:
            raise serializers.ValidationError({
                'password': 'Passwords do not match.'
            })

        attrs.pop('password2', None)

        return attrs

    # =========================
    # CREATE USER + PROFILE
    # =========================
    def create(self, validated_data):

        student_fields = {
            'headline': validated_data.pop(
                'headline',
                ''
            ),

            'bio': validated_data.pop(
                'bio',
                ''
            ),

            'college': get_or_create_college(
                validated_data.pop(
                    'college',
                    ''
                )
            ),

            'student_id': validated_data.pop(
                'student_id',
                ''
            ),

            'university_name': validated_data.pop(
                'university_name',
                ''
            ),

            'course': validated_data.pop(
                'course',
                ''
            ),

            'branch': validated_data.pop(
                'branch',
                ''
            ),

            'current_year': validated_data.pop(
                'current_year',
                ''
            ),

            'graduation_year': validated_data.pop(
                'graduation_year',
                ''
            ),

            'date_of_birth': validated_data.pop(
                'date_of_birth',
                None
            ),

            'gender': validated_data.pop(
                'gender',
                ''
            ),

            'address': validated_data.pop(
                'address',
                ''
            ),

            'city': validated_data.pop(
                'city',
                ''
            ),

            'state': validated_data.pop(
                'state',
                ''
            ),

            'country': validated_data.pop(
                'country',
                ''
            ),

            'career_objective': validated_data.pop(
                'career_objective',
                ''
            ),

            'skills': validated_data.pop(
                'skills',
                []
            ),

            'tech_stack': validated_data.pop(
                'tech_stack',
                []
            ),

            'languages_known': validated_data.pop(
                'languages_known',
                []
            ),

            'experience': validated_data.pop(
                'experience',
                []
            ),

            'experience_level': validated_data.pop(
                'experience_level',
                'beginner'
            ),

            'availability': validated_data.pop(
                'availability',
                'part_time'
            ),

            'hourly_rate': validated_data.pop(
                'hourly_rate',
                None
            ),

            'portfolio_url': validated_data.pop(
                'portfolio_url',
                None
            ),

            'github_url': validated_data.pop(
                'github_url',
                None
            ),

            'linkedin_url': validated_data.pop(
                'linkedin_url',
                None
            ),

            'behance_url': validated_data.pop(
                'behance_url',
                None
            ),

            'dribbble_url': validated_data.pop(
                'dribbble_url',
                None
            ),

            'resume': validated_data.pop(
                'resume',
                None
            ),

            'profile_photo': validated_data.pop(
                'profile_photo',
                None
            ),

            'college_id_document': validated_data.pop(
                'college_id_document',
                None
            ),
        }

        # Create User
        user = User.objects.create_user(
            role='student',
            **validated_data
        )

        # Create Student Profile
        StudentProfile.objects.create(
            user=user,
            **student_fields
        )

        return user

# ============================================================================
# CLIENT SERIALIZERS
# ============================================================================

class ClientProfileSerializer(serializers.ModelSerializer):
    """Serializer for client profiles"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = ClientProfile
        fields = [
            'id', 'user', 'company_name', 'industry', 'company_size',
            'company_logo', 'company_description', 'company_website',
            'location', 'budget_range_min', 'budget_range_max',
            'projects_posted', 'rating', 'is_verified', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'projects_posted', 'rating', 'created_at', 'updated_at']


class ClientDetailSerializer(serializers.ModelSerializer):
    """Detailed client profile with user info"""
    user = UserDetailSerializer(read_only=True)
    
    class Meta:
        model = ClientProfile
        fields = [
            'id', 'user', 'company_name', 'industry', 'company_size',
            'company_logo', 'company_description', 'company_website',
            'location', 'budget_range_min', 'budget_range_max',
            'projects_posted', 'rating', 'is_verified', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'projects_posted', 'rating', 'created_at', 'updated_at']


class ClientRegistrationSerializer(serializers.Serializer):
    """Multi-step client registration (4 steps)"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    company_name = serializers.CharField(max_length=255)
    industry = serializers.ChoiceField(choices=ClientProfile.INDUSTRY_CHOICES)
    company_size = serializers.ChoiceField(choices=ClientProfile.SIZE_CHOICES)
    company_description = serializers.CharField(required=False)
    company_website = serializers.URLField(required=False)
    location = serializers.CharField(required=False)
    budget_range_min = serializers.DecimalField(max_digits=12, decimal_places=2)
    budget_range_max = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists. Please log in or use another email.')
        return value
    
    def create(self, validated_data):
        client_fields = {
            'company_name': validated_data.pop('company_name'),
            'industry': validated_data.pop('industry'),
            'company_size': validated_data.pop('company_size'),
            'company_description': validated_data.pop('company_description', ''),
            'company_website': validated_data.pop('company_website', None),
            'location': validated_data.pop('location', ''),
            'budget_range_min': validated_data.pop('budget_range_min'),
            'budget_range_max': validated_data.pop('budget_range_max', None),
        }
        
        user = User.objects.create_user(role='client', **validated_data)
        ClientProfile.objects.create(user=user, **client_fields)
        
        return user


# ============================================================================
# PROJECT SERIALIZERS
# ============================================================================

class ProjectListSerializer(serializers.ModelSerializer):
    """Serializer for project list view (showcase)"""
    client_info = ClientProfileSerializer(source='client', read_only=True)
    
    class Meta:
        model = Project
        fields = [
            'id', 'title', 'description', 'category', 'status', 'required_skills',
            'budget_type', 'budget_min', 'budget_max', 'experience_level',
            'cover_image', 'client_info', 'rating', 'applications_count',
            'is_featured', 'created_at'
        ]
        read_only_fields = ['id', 'applications_count', 'created_at']


class ProjectDetailSerializer(serializers.ModelSerializer):
    """Serializer for project detail view"""
    client_info = ClientDetailSerializer(source='client', read_only=True)
    
    class Meta:
        model = Project
        fields = [
            'id', 'title', 'description', 'category', 'status', 'required_skills',
            'budget_type', 'budget_min', 'budget_max', 'duration_weeks',
            'experience_level', 'cover_image', 'attachments', 'client_info',
            'rating', 'applications_count', 'is_featured', 'created_at',
            'updated_at', 'deadline'
        ]
        read_only_fields = ['id', 'applications_count', 'created_at', 'updated_at']


class ProjectCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating projects"""
    category = serializers.CharField(max_length=100)

    class Meta:
        model = Project
        fields = [
            'title', 'description', 'category', 'status', 'required_skills',
            'budget_type', 'budget_min', 'budget_max', 'duration_weeks',
            'experience_level', 'cover_image', 'attachments', 'deadline'
        ]


# ============================================================================
# JOB SERIALIZERS
# ============================================================================

class JobListSerializer(serializers.ModelSerializer):
    """Serializer for job list"""
    client_info = ClientProfileSerializer(source='client', read_only=True)
    
    class Meta:
        model = Job
        fields = [
            'id', 'title', 'description', 'job_type', 'required_skills',
            'location', 'salary_min', 'salary_max', 'experience_level',
            'status', 'applications_count', 'client_info', 'created_at'
        ]
        read_only_fields = ['id', 'applications_count', 'created_at']


class JobDetailSerializer(serializers.ModelSerializer):
    """Serializer for job detail"""
    client_info = ClientDetailSerializer(source='client', read_only=True)
    
    class Meta:
        model = Job
        fields = [
            'id', 'title', 'description', 'job_type', 'required_skills',
            'location', 'salary_min', 'salary_max', 'experience_level',
            'status', 'applications_count', 'client_info', 'created_at',
            'updated_at', 'deadline'
        ]
        read_only_fields = ['id', 'applications_count', 'created_at', 'updated_at']


class JobCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating jobs"""
    class Meta:
        model = Job
        fields = [
            'title', 'description', 'job_type', 'required_skills',
            'location', 'salary_min', 'salary_max', 'experience_level', 'deadline'
        ]


# ============================================================================
# APPLICATION SERIALIZERS
# ============================================================================

class ApplicationSerializer(serializers.ModelSerializer):
    """Serializer for applications"""
    student = StudentProfileSerializer(read_only=True)
    project_title = serializers.CharField(source='project.title', read_only=True)
    job_title = serializers.CharField(source='job.title', read_only=True)
    
    class Meta:
        model = Application
        fields = [
            'id', 'student', 'project', 'job', 'project_title', 'job_title',
            'cover_letter', 'proposed_rate', 'proposed_duration', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'student', 'status', 'created_at', 'updated_at']


class ApplicationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating applications"""
    class Meta:
        model = Application
        fields = ['id', 'project', 'job', 'cover_letter', 'proposed_rate', 'proposed_duration', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']
    
    def validate(self, attrs):
        if not attrs.get('project') and not attrs.get('job'):
            raise serializers.ValidationError("Must specify either project or job.")
        if attrs.get('project') and attrs.get('job'):
            raise serializers.ValidationError("Cannot apply to both.")
        request = self.context.get('request')
        student = getattr(getattr(request, 'user', None), 'student_profile', None)
        if student and attrs.get('project') and Application.objects.filter(student=student, project=attrs['project']).exists():
            raise serializers.ValidationError({'project': 'You have already applied to this project.'})
        if student and attrs.get('job') and Application.objects.filter(student=student, job=attrs['job']).exists():
            raise serializers.ValidationError({'job': 'You have already applied to this job.'})
        return attrs


# ============================================================================
# MESSAGE SERIALIZERS
# ============================================================================

class MessageSerializer(serializers.ModelSerializer):
    """Serializer for messages"""
    sender = UserSerializer(read_only=True)
    recipient = UserSerializer(read_only=True)
    
    class Meta:
        model = Message
        fields = [
            'id', 'sender', 'recipient', 'project', 'job', 'content',
            'attachments', 'is_read', 'created_at'
        ]
        read_only_fields = ['id', 'sender', 'is_read', 'created_at']


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating messages"""
    class Meta:
        model = Message
        fields = ['recipient', 'project', 'job', 'content', 'attachments']


# ============================================================================
# REVIEW SERIALIZERS
# ============================================================================

class ReviewSerializer(serializers.ModelSerializer):
    """Serializer for reviews"""
    reviewer = UserSerializer(read_only=True)
    
    class Meta:
        model = Review
        fields = [
            'id', 'reviewer', 'project', 'job', 'rating', 'comment', 'created_at'
        ]
        read_only_fields = ['id', 'reviewer', 'created_at']


class ReviewCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating reviews. Restricted to genuine participants (the client
    and the accepted developer) of the specific project/job being reviewed, so ratings
    that feed the public leaderboards can't be spoofed by an unrelated user."""
    class Meta:
        model = Review
        fields = ['reviewee', 'project', 'job', 'rating', 'comment']

    def validate(self, attrs):
        project = attrs.get('project')
        job = attrs.get('job')
        reviewee = attrs.get('reviewee')
        request = self.context.get('request')
        user = getattr(request, 'user', None)

        if not project and not job:
            raise serializers.ValidationError("Must specify either project or job.")
        if project and job:
            raise serializers.ValidationError("Cannot review both a project and a job at once.")

        target = project or job
        client_user = target.client.user

        worker_user = None
        if project and project.assigned_student:
            worker_user = project.assigned_student.user
        else:
            accepted = Application.objects.filter(
                project=project, job=job, status='accepted'
            ).select_related('student__user').first()
            if accepted:
                worker_user = accepted.student.user

        if user == client_user:
            expected_reviewee = worker_user
        elif worker_user is not None and user == worker_user:
            expected_reviewee = client_user
        else:
            raise serializers.ValidationError("You can only review a project/job you were directly involved in.")

        if expected_reviewee is None:
            raise serializers.ValidationError("There's no accepted developer to review on this project/job yet.")
        if reviewee != expected_reviewee:
            raise serializers.ValidationError("reviewee must be the other participant in this project/job.")
        if user == reviewee:
            raise serializers.ValidationError("You cannot review yourself.")

        return attrs


# ============================================================================
# NOTIFICATION SERIALIZERS
# ============================================================================

class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications"""
    related_user = UserSerializer(read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message', 'related_user',
            'related_project', 'related_job', 'is_read', 'action_url', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']