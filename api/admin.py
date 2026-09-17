from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from api.models import (
    User, StudentProfile, ClientProfile, Project, Job,
    Application, Message, Review, Notification,
    College, Team, TeamMember, FeedPost, FeedComment, FeedLike, FeedSave, FeedShare, UserFollow
)


# ============================================================================
# CUSTOM USER ADMIN
# ============================================================================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User Admin"""
    list_display = ('email', 'get_full_name', 'role_badge', 'is_verified', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'is_verified', 'created_at')
    search_fields = ('email', 'first_name', 'last_name', 'phone')
    ordering = ('-created_at',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('phone', 'role', 'avatar', 'bio', 'is_verified')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('phone', 'role')
        }),
    )
    
    def role_badge(self, obj):
        """Display role with color badge"""
        colors = {
            'student': '#28a745',
            'client': '#007bff',
            'admin': '#dc3545'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.role, '#6c757d'),
            obj.get_role_display()
        )
    role_badge.short_description = 'Role'


# ============================================================================
# STUDENT PROFILE ADMIN
# ============================================================================

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    """Student Profile Admin"""
    list_display = ('get_user_name', 'experience_level', 'rating', 'projects_completed', 'is_featured', 'created_at')
    list_filter = ('experience_level', 'availability', 'is_featured', 'created_at', 'rating')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'headline', 'skills')
    readonly_fields = ('id', 'rating', 'total_reviews', 'projects_completed', 'created_at', 'updated_at')
    ordering = ('-rating', '-created_at')
    
    fieldsets = (
        ('User', {
            'fields': ('id', 'user')
        }),
        ('Profile Info', {
            'fields': ('headline', 'bio', 'cover_image')
        }),
        ('Skills & Experience', {
            'fields': ('skills', 'verified_skills', 'experience_level')
        }),
        ('Availability & Rates', {
            'fields': ('availability', 'hourly_rate')
        }),
        ('Links', {
            'fields': ('portfolio_url', 'github_url', 'linkedin_url', 'resume')
        }),
        ('Performance', {
            'fields': ('rating', 'total_reviews', 'projects_completed')
        }),
        ('Status', {
            'fields': ('is_featured', 'created_at', 'updated_at')
        }),
    )
    
    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    get_user_name.short_description = 'Student Name'


# ============================================================================
# CLIENT PROFILE ADMIN
# ============================================================================

@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    """Client Profile Admin"""
    list_display = ('company_name', 'get_owner_name', 'industry', 'company_size', 'rating', 'is_verified', 'created_at')
    list_filter = ('industry', 'company_size', 'is_verified', 'created_at', 'rating')
    search_fields = ('company_name', 'user__email', 'user__first_name', 'user__last_name', 'location')
    readonly_fields = ('id', 'projects_posted', 'rating', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Owner', {
            'fields': ('id', 'user')
        }),
        ('Company Info', {
            'fields': ('company_name', 'company_logo', 'company_description')
        }),
        ('Company Details', {
            'fields': ('industry', 'company_size', 'company_website', 'location')
        }),
        ('Budget', {
            'fields': ('budget_range_min', 'budget_range_max')
        }),
        ('Performance', {
            'fields': ('projects_posted', 'rating')
        }),
        ('Status', {
            'fields': ('is_verified', 'created_at', 'updated_at')
        }),
    )
    
    def get_owner_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    get_owner_name.short_description = 'Owner'


# ============================================================================
# PROJECT ADMIN
# ============================================================================

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """Project Admin"""
    list_display = ('title', 'get_client_name', 'category', 'status_badge', 'budget_min', 'rating', 'is_featured', 'created_at')
    list_filter = ('status', 'category', 'experience_level', 'budget_type', 'is_featured', 'created_at')
    search_fields = ('title', 'description', 'client__company_name', 'category', 'required_skills')
    readonly_fields = ('id', 'applications_count', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Project Info', {
            'fields': ('id', 'title', 'description', 'cover_image')
        }),
        ('Category & Details', {
            'fields': ('category', 'required_skills', 'experience_level')
        }),
        ('Budget', {
            'fields': ('budget_type', 'budget_min', 'budget_max', 'duration_weeks')
        }),
        ('Assignment', {
            'fields': ('client', 'assigned_student')
        }),
        ('Attachments', {
            'fields': ('attachments',)
        }),
        ('Performance', {
            'fields': ('rating', 'applications_count')
        }),
        ('Status', {
            'fields': ('status', 'is_featured', 'deadline', 'created_at', 'updated_at')
        }),
    )
    
    def get_client_name(self, obj):
        return obj.client.company_name
    get_client_name.short_description = 'Client'
    
    def status_badge(self, obj):
        colors = {
            'draft': '#6c757d',
            'open': '#28a745',
            'in_progress': '#ffc107',
            'completed': '#007bff',
            'cancelled': '#dc3545'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


# ============================================================================
# JOB ADMIN
# ============================================================================

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    """Job Admin"""
    list_display = ('title', 'get_client_name', 'job_type', 'status', 'salary_min', 'applications_count', 'created_at')
    list_filter = ('job_type', 'status', 'experience_level', 'created_at')
    search_fields = ('title', 'description', 'client__company_name', 'location', 'required_skills')
    readonly_fields = ('id', 'applications_count', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Job Info', {
            'fields': ('id', 'title', 'description', 'job_type')
        }),
        ('Requirements', {
            'fields': ('required_skills', 'experience_level')
        }),
        ('Salary', {
            'fields': ('salary_min', 'salary_max')
        }),
        ('Details', {
            'fields': ('location', 'client', 'deadline')
        }),
        ('Status', {
            'fields': ('status', 'applications_count', 'created_at', 'updated_at')
        }),
    )
    
    def get_client_name(self, obj):
        return obj.client.company_name
    get_client_name.short_description = 'Client'


# ============================================================================
# APPLICATION ADMIN
# ============================================================================

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    """Application Admin"""
    list_display = ('get_student_name', 'get_target', 'status_badge', 'proposed_rate', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('student__user__email', 'student__user__first_name', 'project__title', 'job__title')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Application Info', {
            'fields': ('id', 'student')
        }),
        ('Target', {
            'fields': ('project', 'job')
        }),
        ('Application Details', {
            'fields': ('cover_letter', 'proposed_rate', 'proposed_duration')
        }),
        ('Status', {
            'fields': ('status', 'created_at', 'updated_at')
        }),
    )
    
    def get_student_name(self, obj):
        return f"{obj.student.user.first_name} {obj.student.user.last_name}"
    get_student_name.short_description = 'Student'
    
    def get_target(self, obj):
        if obj.project:
            return f"Project: {obj.project.title}"
        return f"Job: {obj.job.title}"
    get_target.short_description = 'Applied To'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'accepted': '#28a745',
            'rejected': '#dc3545',
            'withdrawn': '#6c757d'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


# ============================================================================
# MESSAGE ADMIN
# ============================================================================

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Message Admin"""
    list_display = ('get_sender_email', 'get_recipient_email', 'is_read_badge', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('sender__email', 'recipient__email', 'content')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Message Info', {
            'fields': ('id', 'content')
        }),
        ('Participants', {
            'fields': ('sender', 'recipient')
        }),
        ('Context', {
            'fields': ('project', 'job', 'attachments')
        }),
        ('Status', {
            'fields': ('is_read', 'created_at', 'updated_at')
        }),
    )
    
    def get_sender_email(self, obj):
        return obj.sender.email
    get_sender_email.short_description = 'From'
    
    def get_recipient_email(self, obj):
        return obj.recipient.email
    get_recipient_email.short_description = 'To'
    
    def is_read_badge(self, obj):
        if obj.is_read:
            return format_html('<span style="color: green;">✓ Read</span>')
        return format_html('<span style="color: red;">Unread</span>')
    is_read_badge.short_description = 'Status'


# ============================================================================
# REVIEW ADMIN
# ============================================================================

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """Review Admin"""
    list_display = ('get_reviewer_email', 'get_reviewee_email', 'rating_stars', 'get_target', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('reviewer__email', 'reviewee__email', 'comment')
    readonly_fields = ('id', 'created_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Review Info', {
            'fields': ('id', 'rating', 'comment')
        }),
        ('Participants', {
            'fields': ('reviewer', 'reviewee')
        }),
        ('Context', {
            'fields': ('project', 'job')
        }),
        ('Created', {
            'fields': ('created_at',)
        }),
    )
    
    def get_reviewer_email(self, obj):
        return obj.reviewer.email
    get_reviewer_email.short_description = 'Reviewer'
    
    def get_reviewee_email(self, obj):
        return obj.reviewee.email
    get_reviewee_email.short_description = 'Reviewed'
    
    def rating_stars(self, obj):
        stars = '⭐' * obj.rating
        return format_html('<span>{}</span>', stars)
    rating_stars.short_description = 'Rating'
    
    def get_target(self, obj):
        if obj.project:
            return f"Project: {obj.project.title}"
        return f"Job: {obj.job.title}"
    get_target.short_description = 'For'


# ============================================================================
# NOTIFICATION ADMIN
# ============================================================================

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Notification Admin"""
    list_display = ('title', 'notification_type', 'get_recipient_email', 'is_read_badge', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__email', 'title', 'message')
    readonly_fields = ('id', 'created_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Notification Info', {
            'fields': ('id', 'title', 'message', 'notification_type')
        }),
        ('Recipient', {
            'fields': ('user', 'related_user')
        }),
        ('Context', {
            'fields': ('related_project', 'related_job', 'action_url')
        }),
        ('Status', {
            'fields': ('is_read', 'created_at')
        }),
    )
    
    def get_recipient_email(self, obj):
        return obj.user.email
    get_recipient_email.short_description = 'Recipient'
    
    def is_read_badge(self, obj):
        if obj.is_read:
            return format_html('<span style="color: green;">✓ Read</span>')
        return format_html('<span style="color: red;">Unread</span>')
    is_read_badge.short_description = 'Status'

# ============================================================================
# COLLEGE ADMIN
# ============================================================================

@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    """College Admin - verify colleges and inspect leaderboard stats"""
    list_display = ('name', 'location', 'is_verified', 'admin_total_developers', 'admin_total_teams', 'admin_performance_score', 'created_at')
    list_filter = ('is_verified',)
    search_fields = ('name', 'location')
    readonly_fields = ('id', 'slug', 'created_at', 'updated_at', 'admin_total_developers', 'admin_total_teams', 'admin_projects_completed', 'admin_client_rating', 'admin_success_rate', 'admin_performance_score')
    ordering = ('name',)

    fieldsets = (
        ('College Info', {
            'fields': ('id', 'name', 'slug', 'location', 'logo', 'description', 'website', 'email_domain')
        }),
        ('Verification', {
            'fields': ('is_verified',)
        }),
        ('Leaderboard Stats (computed)', {
            'fields': ('admin_total_developers', 'admin_total_teams', 'admin_projects_completed', 'admin_client_rating', 'admin_success_rate', 'admin_performance_score')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def admin_total_developers(self, obj):
        return obj.total_developers
    admin_total_developers.short_description = 'Developers'

    def admin_total_teams(self, obj):
        return obj.total_teams
    admin_total_teams.short_description = 'Teams'

    def admin_projects_completed(self, obj):
        return obj.projects_completed
    admin_projects_completed.short_description = 'Projects completed'

    def admin_client_rating(self, obj):
        return obj.client_rating
    admin_client_rating.short_description = 'Client rating'

    def admin_success_rate(self, obj):
        return obj.success_rate
    admin_success_rate.short_description = 'Success rate'

    def admin_performance_score(self, obj):
        return obj.performance_score
    admin_performance_score.short_description = 'Performance score'


# ============================================================================
# TEAM ADMIN
# ============================================================================

class TeamMemberInline(admin.TabularInline):
    model = TeamMember
    extra = 0
    readonly_fields = ('user', 'created_at')


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    """Team Admin - approve/reject team verification"""
    list_display = ('name', 'get_college_name', 'leader', 'verification_status', 'rating', 'completed_projects', 'created_at')
    list_filter = ('verification_status', 'availability', 'college')
    search_fields = ('name', 'leader__email', 'college__name')
    readonly_fields = ('id', 'slug', 'leader', 'completed_projects', 'rating', 'success_rate', 'created_at', 'updated_at')
    inlines = [TeamMemberInline]
    actions = ['verify_teams', 'reject_teams']

    def get_college_name(self, obj):
        return obj.college.name if obj.college else '-'
    get_college_name.short_description = 'College'

    def verify_teams(self, request, queryset):
        queryset.update(verification_status='verified')
    verify_teams.short_description = 'Mark selected teams as verified'

    def reject_teams(self, request, queryset):
        queryset.update(verification_status='rejected')
    reject_teams.short_description = 'Mark selected teams as rejected'


# ============================================================================
# DEVELOPER FEED ADMIN
# ============================================================================

class FeedCommentInline(admin.TabularInline):
    model = FeedComment
    extra = 0
    readonly_fields = ('author', 'created_at')


@admin.register(FeedPost)
class FeedPostAdmin(admin.ModelAdmin):
    """Feed Post Admin"""
    list_display = ('get_author_email', 'short_body', 'get_team_name', 'is_published', 'created_at')
    list_filter = ('is_published', 'created_at')
    search_fields = ('body', 'author__email', 'team__name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = [FeedCommentInline]

    def get_author_email(self, obj):
        return obj.author.email
    get_author_email.short_description = 'Author'

    def get_team_name(self, obj):
        return obj.team.name if obj.team else '-'
    get_team_name.short_description = 'Team'

    def short_body(self, obj):
        return obj.body[:60] + ('...' if len(obj.body) > 60 else '')
    short_body.short_description = 'Post'


@admin.register(UserFollow)
class UserFollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'following', 'created_at')
    search_fields = ('follower__email', 'following__email')
