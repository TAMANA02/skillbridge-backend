from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly, IsAdminUser

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg
from django.utils import timezone

from api.models import (
    User, StudentProfile, ClientProfile, Project, Job,
        Application, Message, Review, Notification,
    College, Team, TeamMember, FeedPost, FeedComment, FeedLike, FeedSave, FeedShare, UserFollow

)
from api.serializers import (
    UserSerializer, UserDetailSerializer, RegisterSerializer, LoginSerializer,
    StudentProfileSerializer, StudentDetailSerializer, StudentRegistrationSerializer,
    ClientProfileSerializer, ClientDetailSerializer, ClientRegistrationSerializer,
    ProjectListSerializer, ProjectDetailSerializer, ProjectCreateUpdateSerializer,
    JobListSerializer, JobDetailSerializer, JobCreateUpdateSerializer,
    ApplicationSerializer, ApplicationCreateSerializer,
    MessageSerializer, MessageCreateSerializer,
    ReviewSerializer, ReviewCreateSerializer,
    NotificationSerializer,
    CollegeSerializer, CollegeDetailSerializer,
    TeamSerializer, TeamCreateSerializer, TeamMemberSerializer,
    FeedPostSerializer, FeedPostCreateSerializer,
    FeedCommentSerializer, FeedCommentCreateSerializer
)
from api.permissions import (
    IsStudent, IsClient, IsClientOwner, IsStudentOwner,
    IsApplicationOwner, IsMessageParticipant
)
from api.filters import ProjectFilter, JobFilter, StudentFilter
from api.pagination import StandardResultsSetPagination, ProjectPagination, StudentPagination


# ============================================================================
# PART 1: AUTHENTICATION VIEWS
# ============================================================================

class RegisterViewSet(viewsets.ViewSet):
    """User registration endpoint"""
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def student(self, request):
        """Student registration (8 steps combined)"""
        serializer = StudentRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserDetailSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'message': 'Student registered successfully'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def client(self, request):
        """Client registration (4 steps combined)"""
        serializer = ClientRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserDetailSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'message': 'Client registered successfully'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginViewSet(viewsets.ViewSet):
    """User login endpoint"""
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def create(self, request):
        """Login with email and password"""
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserDetailSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'message': 'Login successful'
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """Blacklist the refresh token so it can no longer be used to mint new access tokens."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get('refresh')
        if not refresh:
            return Response({'error': 'refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            RefreshToken(refresh).blacklist()
        except TokenError:
            return Response({'error': 'Invalid or already-expired refresh token'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)


# ============================================================================
# PART 2: STUDENT & CLIENT PROFILE VIEWS
# ============================================================================

class StudentViewSet(viewsets.ModelViewSet):
    """Student profile management"""
    queryset = StudentProfile.objects.select_related('user').all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = StudentFilter
    pagination_class = StudentPagination
    search_fields = ['user__first_name', 'user__last_name', 'headline', 'bio', 'skills', 'tech_stack', 'course', 'branch', 'university_name']
    ordering_fields = ['rating', 'projects_completed', 'created_at']
    ordering = ['-rating', '-projects_completed']
    
    def get_serializer_class(self):
        if self.action == 'retrieve' or self.action == 'update' or self.action == 'partial_update':
            return StudentDetailSerializer
        return StudentProfileSerializer
    
    def get_permissions(self):
        """Public directory: anyone can browse/search developer profiles.
        Only the profile's own user can edit or delete it."""
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsStudentOwner()]
        if self.action == 'me':
            return [IsAuthenticated()]
        return [AllowAny()]
    
    def get_queryset(self):
        """The public developer directory: everyone (list/search/leaderboard/public_profile)."""
        return StudentProfile.objects.select_related('user', 'college').all()
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current student's profile"""
        try:
            profile = StudentProfile.objects.get(user=request.user)
            serializer = StudentDetailSerializer(profile)
            return Response(serializer.data)
        except StudentProfile.DoesNotExist:
            return Response(
                {'error': 'Student profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def leaderboard(self, request):
        """Hall of Fame leaderboard"""
        students = StudentProfile.objects.filter(
            is_featured=True
        ).order_by('-rating', '-projects_completed')[:10]
        serializer = StudentProfileSerializer(students, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search developers by skills, name, etc."""
        queryset = self.get_queryset()
        
        # Filter by skills
        skills = request.query_params.get('skills', '').split(',')
        if skills and skills[0]:
            for skill in skills:
                queryset = queryset.filter(skills__icontains=skill.strip())
        
        # Filter by experience level
        experience = request.query_params.get('experience_level')
        if experience:
            queryset = queryset.filter(experience_level=experience)
        
        # Filter by availability
        availability = request.query_params.get('availability')
        if availability:
            queryset = queryset.filter(availability=availability)
        
        # Search by name or bio
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(bio__icontains=search) |
                Q(headline__icontains=search) |
                Q(skills__icontains=search) |
                Q(tech_stack__icontains=search) |
                Q(course__icontains=search) |
                Q(branch__icontains=search)
            )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def public_profile(self, request, pk=None):
        """Get public student profile (like Amaya Kapoor page)"""
        try:
            student = StudentProfile.objects.get(user__id=pk)
            serializer = StudentDetailSerializer(student)
            return Response(serializer.data)
        except StudentProfile.DoesNotExist:
            return Response(
                {'error': 'Profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class ClientViewSet(viewsets.ModelViewSet):
    """Client profile management"""
    queryset = ClientProfile.objects.select_related('user').all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    pagination_class = StandardResultsSetPagination
    search_fields = ['company_name', 'company_description', 'location']
    ordering_fields = ['rating', 'projects_posted', 'created_at']
    ordering = ['-rating', '-created_at']
    
    def get_serializer_class(self):
        if self.action == 'retrieve' or self.action == 'update' or self.action == 'partial_update':
            return ClientDetailSerializer
        return ClientProfileSerializer
    
    def get_permissions(self):
        """Only the profile's own user can edit or delete it - previously any authenticated
        non-client user could edit/delete ANY client's profile because get_queryset() only
        scoped role='client' users to their own row and left everyone else unrestricted."""
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsProfileOwner()]
        if self.action == 'me':
            return [IsAuthenticated()]
        return [AllowAny()]
    
    def get_queryset(self):
        return ClientProfile.objects.select_related('user').all()
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current client's profile"""
        try:
            profile = ClientProfile.objects.get(user=request.user)
            serializer = ClientDetailSerializer(profile)
            return Response(serializer.data)
        except ClientProfile.DoesNotExist:
            return Response(
                {'error': 'Client profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )


# ============================================================================
# PART 3: PROJECT & JOB VIEWS
# ============================================================================

class ProjectViewSet(viewsets.ModelViewSet):
    """Project showcase and management"""
    queryset = Project.objects.select_related('client', 'assigned_student').all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProjectFilter
    pagination_class = ProjectPagination
    search_fields = ['title', 'description', 'category', 'required_skills']
    ordering_fields = ['rating', 'created_at', 'applications_count']
    ordering = ['-is_featured', '-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_authenticated and self.request.user.role == 'client':
            return queryset.filter(client__user=self.request.user)
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create' or self.action == 'update' or self.action == 'partial_update':
            return ProjectCreateUpdateSerializer
        elif self.action == 'retrieve':
            return ProjectDetailSerializer
        return ProjectListSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsClient()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsClient(), IsClientOwner()]
        if self.action == 'manage':
            return [IsAuthenticated(), IsClient()]
        if self.action == 'matched':
            return [IsAuthenticated(), IsStudent()]
        if self.action == 'matching_developers':
            return [IsAuthenticated(), IsStudent()]
        return [AllowAny()]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client = ClientProfile.objects.get(user=request.user)
        project = serializer.save(client=client)
        output = ProjectDetailSerializer(project, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def matched(self, request):
        """Return open database projects that match the authenticated student's profile."""
        student = StudentProfile.objects.get(user=request.user)
        student_values = {str(value).lower() for value in (student.skills or []) + (student.tech_stack or [])}
        profile_text = ' '.join([student.headline or '', student.bio or '', student.course or '', student.branch or '']).lower()
        applications = Application.objects.filter(student=student, project__isnull=False)
        application_map = {str(item.project_id): item for item in applications}
        matches = []
        for project in Project.objects.select_related('client').filter(status='open'):
            project_values = {str(value).lower() for value in (project.required_skills or [])}
            skill_hits = len(project_values & student_values)
            category_text = str(project.category or '').lower()
            category_hit = bool(category_text and (category_text in profile_text or any(token in profile_text for token in category_text.split() if len(token) > 3)))
            if project_values and not skill_hits and not category_hit:
                continue
            score = round(((skill_hits + int(category_hit)) / max(len(project_values) + 1, 1)) * 100)
            matches.append({
                'project': ProjectDetailSerializer(project, context=self.get_serializer_context()).data,
                'match_score': min(score, 100),
                'application': ApplicationSerializer(application_map[str(project.id)], context=self.get_serializer_context()).data if str(project.id) in application_map else None,
            })
        return Response(matches)
    
@action(detail=True, methods=['get'], url_path='matching-developers')
def matching_developers(self, request, pk=None):
    """
    Return registered developers who match this project.
    """
    project = self.get_object()

    required_skills = {
        str(skill).strip().lower()
        for skill in (project.required_skills or [])
        if str(skill).strip()
    }

    students = StudentProfile.objects.select_related(
        'user', 'college'
    ).all()

    matches = []

    for student in students:

        student_skills = {
            str(skill).strip().lower()
            for skill in (student.skills or [])
        }

        student_tech_stack = {
            str(skill).strip().lower()
            for skill in (student.tech_stack or [])
        }

        all_student_skills = student_skills | student_tech_stack

        matched_skills = required_skills & all_student_skills

        if required_skills:
            match_score = round(
                (len(matched_skills) / len(required_skills)) * 100
            )
        else:
            match_score = 0

        matches.append({
            'student': StudentDetailSerializer(
                student,
                context=self.get_serializer_context()
            ).data,
            'match_score': match_score,
            'matched_skills': sorted(list(matched_skills)),
            'required_skills': sorted(list(required_skills)),
        })

    matches.sort(
        key=lambda item: item['match_score'],
        reverse=True
    )

    return Response(matches)

    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured projects for showcase"""
        projects = Project.objects.filter(
            is_featured=True,
            status='open'
        ).order_by('-created_at')[:6]
        serializer = ProjectListSerializer(projects, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Advanced project search with filters"""
        queryset = Project.objects.all()
        
        # Filter by category
        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # Filter by skills
        skills = request.query_params.get('skills', '').split(',')
        if skills and skills[0]:
            for skill in skills:
                queryset = queryset.filter(required_skills__icontains=skill.strip())
        
        # Filter by budget range
        budget_min = request.query_params.get('budget_min')
        budget_max = request.query_params.get('budget_max')
        if budget_min:
            queryset = queryset.filter(budget_min__gte=budget_min)
        if budget_max:
            queryset = queryset.filter(budget_max__lte=budget_max)
        
        # Filter by experience level
        experience = request.query_params.get('experience_level')
        if experience:
            queryset = queryset.filter(experience_level=experience)
        
        # Full text search
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Filter by status
        queryset = queryset.filter(status='open')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get', 'post'])
    def manage(self, request, pk=None):
        """Manage project (view/update status)"""
        project = self.get_object()
        if project.client.user != request.user:
            return Response(
                {'error': 'You do not have permission'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if request.method == 'GET':
            serializer = ProjectDetailSerializer(project)
            return Response(serializer.data)
        
        # POST to update status
        new_status = request.data.get('status')
        if new_status:
            project.status = new_status
            project.save()
            serializer = ProjectDetailSerializer(project)
            return Response(serializer.data)
        
        return Response(
            {'error': 'Status is required'},
            status=status.HTTP_400_BAD_REQUEST
        )


class JobViewSet(viewsets.ModelViewSet):
    """Job listings and management"""
    queryset = Job.objects.select_related('client').all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = JobFilter
    pagination_class = StandardResultsSetPagination
    search_fields = ['title', 'description', 'location', 'required_skills']
    ordering_fields = ['created_at', 'salary_min', 'salary_max']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create' or self.action == 'update' or self.action == 'partial_update':
            return JobCreateUpdateSerializer
        elif self.action == 'retrieve':
            return JobDetailSerializer
        return JobListSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsClient()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsClient(), IsClientOwner()]
        if self.action == 'dashboard':
            return [IsAuthenticated()]
        return [AllowAny()]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client = ClientProfile.objects.get(user=request.user)
        job = serializer.save(client=client)
        output = JobDetailSerializer(job, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Student dashboard - jobs relevant to student"""
        if request.user.role != 'student':
            return Response(
                {'error': 'Only students can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            student = StudentProfile.objects.get(user=request.user)
            # Find relevant jobs based on student's skills
            jobs = Job.objects.filter(
                status='open'
            ).order_by('-created_at')
            
            serializer = JobListSerializer(jobs, many=True)
            return Response({
                'total_jobs': jobs.count(),
                'jobs': serializer.data
            })
        except StudentProfile.DoesNotExist:
            return Response(
                {'error': 'Student profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )


# ============================================================================
# PART 4: APPLICATION VIEWS
# ============================================================================

class ApplicationViewSet(viewsets.ModelViewSet):
    """Student applications to projects/jobs"""
    queryset = Application.objects.select_related(
        'student', 'project', 'job'
    ).all()
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ApplicationCreateSerializer
        return ApplicationSerializer
    
    def perform_create(self, serializer):
        """Create application for current student"""
        student = StudentProfile.objects.get(user=self.request.user)
        serializer.save(student=student)
    
    def get_queryset(self):
        """Filter applications based on user role"""
        if self.request.user.role == 'student':
            return Application.objects.filter(
                student__user=self.request.user
            ).select_related('student', 'project', 'job')
        elif self.request.user.role == 'client':
            return Application.objects.filter(
                Q(project__client__user=self.request.user) |
                Q(job__client__user=self.request.user)
            ).select_related('student', 'project', 'job')
        return Application.objects.none()
    
    @action(detail=True, methods=['patch'])
    def accept(self, request, pk=None):
        """Accept application - assigns the student to the project (if applicable) so
        downstream stats (project status, college/team leaderboard) reflect the hire."""
        application = self.get_object()
        if application.student.user == request.user:
            if application.status != 'pending':
                return Response({'error': 'This response has already been recorded.'}, status=status.HTTP_409_CONFLICT)
            application.status = 'accepted'
            application.save(update_fields=['status', 'updated_at'])
            return Response(ApplicationSerializer(application, context=self.get_serializer_context()).data)
        if application.project:
            if application.project.client.user != request.user:
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
        elif application.job:
            if application.job.client.user != request.user:
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        application.status = 'accepted'
        application.save()

        if application.project and not application.project.assigned_student:
            application.project.assigned_student = application.student
            if application.project.status == 'open':
                application.project.status = 'in_progress'
            application.project.save(update_fields=['assigned_student', 'status', 'updated_at'])

        serializer = ApplicationSerializer(application)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def reject(self, request, pk=None):
        """Reject application"""
        application = self.get_object()
        if application.student.user == request.user:
            if application.status != 'pending':
                return Response({'error': 'This response has already been recorded.'}, status=status.HTTP_409_CONFLICT)
            application.status = 'rejected'
            application.save(update_fields=['status', 'updated_at'])
            return Response(ApplicationSerializer(application, context=self.get_serializer_context()).data)
        if application.project:
            if application.project.client.user != request.user:
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
        elif application.job:
            if application.job.client.user != request.user:
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        application.status = 'rejected'
        application.save()
        serializer = ApplicationSerializer(application)
        return Response(serializer.data)


# ============================================================================
# PART 5: MESSAGE VIEWS
# ============================================================================

class MessageViewSet(viewsets.ModelViewSet):
    """Messaging between users"""
    queryset = Message.objects.select_related(
        'sender', 'recipient', 'project', 'job'
    ).all()
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return MessageCreateSerializer
        return MessageSerializer
    
    def perform_create(self, serializer):
        """Create message from current user"""
        serializer.save(sender=self.request.user)
    
    def get_queryset(self):
        """Conversation view: sender or recipient. Only the sender may edit/delete their own message."""
        if self.action in ['update', 'partial_update', 'destroy']:
            return Message.objects.filter(sender=self.request.user)
        return Message.objects.filter(
            Q(sender=self.request.user) | Q(recipient=self.request.user)
        ).order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def conversations(self, request):
        """Get list of conversations (unique recipients)"""
        messages = Message.objects.filter(
            Q(sender=request.user) | Q(recipient=request.user)
        ).select_related('sender', 'recipient')
        
        # Get unique conversations
        conversations = {}
        for msg in messages:
            other_user = msg.recipient if msg.sender == request.user else msg.sender
            if other_user.id not in conversations:
                conversations[other_user.id] = {
                    'user': UserSerializer(other_user).data,
                    'last_message': msg.content,
                    'last_message_time': msg.created_at,
                    'unread_count': 0
                }
            if msg.recipient == request.user and not msg.is_read:
                conversations[other_user.id]['unread_count'] += 1
        
        return Response(list(conversations.values()))
    
    @action(detail=False, methods=['get'])
    def with_user(self, request):
        """Get chat with specific user"""
        recipient_id = request.query_params.get('recipient_id')
        if not recipient_id:
            return Response(
                {'error': 'recipient_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        messages = Message.objects.filter(
            Q(sender=request.user, recipient_id=recipient_id) |
            Q(sender_id=recipient_id, recipient=request.user)
        ).order_by('created_at')
        
        # Mark as read
        Message.objects.filter(
            sender_id=recipient_id,
            recipient=request.user,
            is_read=False
        ).update(is_read=True)
        
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)


# ============================================================================
# PART 6: REVIEW VIEWS
# ============================================================================

class ReviewViewSet(viewsets.ModelViewSet):
    """Reviews and ratings"""
    queryset = Review.objects.select_related(
        'reviewer', 'reviewee', 'project', 'job'
    ).all()
    pagination_class = StandardResultsSetPagination
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ReviewCreateSerializer
        return ReviewSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]
    
    def get_queryset(self):
        """Reviews are public trust signals (they feed the college/team/developer leaderboards),
        but only the reviewer who wrote a review can edit or delete it."""
        if self.action in ['update', 'partial_update', 'destroy']:
            return Review.objects.filter(reviewer=self.request.user)
        return Review.objects.select_related('reviewer', 'reviewee', 'project', 'job').all()
    
    def perform_create(self, serializer):
        """Create review from current user"""
        serializer.save(reviewer=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = serializer.save(reviewer=request.user)
        output = ReviewSerializer(review, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def for_user(self, request):
        """Get reviews for a specific user"""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reviews = Review.objects.filter(reviewee_id=user_id)
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)


# ============================================================================
# PART 7: NOTIFICATION VIEWS
# ============================================================================

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """User notifications"""
    queryset = Notification.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    pagination_class = StandardResultsSetPagination
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get notifications for current user"""
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['patch'])
    def mark_as_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'marked as read'})
    
    @action(detail=False, methods=['patch'])
    def mark_all_as_read(self, request):
        """Mark all notifications as read"""
        Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)
        return Response({'status': 'all marked as read'})
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        return Response({'unread_count': count})


class CollegeViewSet(viewsets.ModelViewSet):
    """College directory + leaderboard. Read-only to everyone; only staff can edit/delete."""
    queryset = College.objects.all()
    lookup_field = 'slug'
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'location']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CollegeDetailSerializer
        return CollegeSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        # Leaderboard ranks by performance_score, which is computed (not stored),
        # so sort in Python after evaluating the small college list.
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        colleges = list(queryset)
        colleges.sort(key=lambda c: c.performance_score, reverse=True)
        page = self.paginate_queryset(colleges)
        serializer = self.get_serializer(page if page is not None else colleges, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def leaderboard(self, request):
        """Top colleges ranked by the quality-weighted performance score."""
        colleges = list(self.get_queryset())
        colleges.sort(key=lambda c: c.performance_score, reverse=True)
        limit = int(request.query_params.get('limit', 10))
        serializer = CollegeSerializer(colleges[:limit], many=True)
        return Response(serializer.data)


class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.prefetch_related('members').select_related('leader').all()
    lookup_field = 'slug'
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'skills', 'college__name']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_queryset(self):
        queryset = self.queryset
        # Newly created teams must be discoverable immediately. Verification
        # status remains visible on the profile so clients can distinguish a
        # pending team without hiding the database record from search.
        college = self.request.query_params.get('college')
        if college:
            queryset = queryset.filter(college__name__icontains=college)
        return queryset

    def get_serializer_class(self):
        return TeamCreateSerializer if self.action == 'create' else TeamSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        team = serializer.save()
        output = TeamSerializer(team, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        if serializer.instance.leader != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only the team leader can update this team.')
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        team = self.get_object()
        if team.leader != request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only the team leader can delete this team.')
        return super().destroy(request, *args, **kwargs)


class FeedPostViewSet(viewsets.ModelViewSet):
    queryset = FeedPost.objects.select_related('author', 'team', 'project').prefetch_related('comments__author').all()
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['body', 'tags']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            queryset = self.queryset.filter(Q(is_published=True) | Q(author=self.request.user))
        else:
            queryset = self.queryset.filter(is_published=True)
        team = self.request.query_params.get('team')
        if team:
            queryset = queryset.filter(team_id=team)
        return queryset

    def get_serializer_class(self):
        return FeedPostCreateSerializer if self.action in ['create', 'update', 'partial_update'] else FeedPostSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        post = serializer.save(author=request.user)
        output = FeedPostSerializer(post, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        if serializer.instance.author != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only the author can update this post.')
        serializer.save()

    def perform_destroy(self, instance):
        if instance.author != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only the author can delete this post.')
        instance.delete()

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        post = self.get_object()
        reaction, created = FeedLike.objects.get_or_create(post=post, user=request.user)
        if not created:
            reaction.delete()
        return Response({'liked': created, 'likes_count': post.likes.count()})

    @action(detail=True, methods=['post'])
    def save(self, request, pk=None):
        post = self.get_object()
        bookmark, created = FeedSave.objects.get_or_create(post=post, user=request.user)
        if not created:
            bookmark.delete()
        return Response({'saved': created})

    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        post = self.get_object()
        FeedShare.objects.create(post=post, user=request.user)
        return Response({'shares_count': post.shares.count()}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        post = self.get_object()
        if request.method == 'GET':
            return Response(FeedCommentSerializer(post.comments.all(), many=True, context={'request': request}).data)
        serializer = FeedCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(post=post, author=request.user)
        return Response(FeedCommentSerializer(comment, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='follow-author')
    def follow_author(self, request, pk=None):
        post = self.get_object()
        if post.author == request.user:
            return Response({'detail': 'You cannot follow yourself.'}, status=status.HTTP_400_BAD_REQUEST)
        follow, created = UserFollow.objects.get_or_create(follower=request.user, following=post.author)
        if not created:
            follow.delete()
        return Response({'following': created})
