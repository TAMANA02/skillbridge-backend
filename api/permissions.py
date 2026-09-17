from rest_framework import permissions
from api.models import StudentProfile, ClientProfile


class IsStudent(permissions.BasePermission):
    """Allow access only to students"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'student'


class IsClient(permissions.BasePermission):
    """Allow access only to clients"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'client'


class IsStudentOrReadOnly(permissions.BasePermission):
    """Allow students to edit, others read-only"""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated and request.user.role == 'student'


class IsClientOrReadOnly(permissions.BasePermission):
    """Allow clients to edit, others read-only"""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated and request.user.role == 'client'


class IsClientOwner(permissions.BasePermission):
    """Allow clients to manage their own projects/jobs (obj must have a `.client` FK)"""
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.client.user == request.user


class IsProfileOwner(permissions.BasePermission):
    """Generic: only the profile's own user may write; everyone may read.
    Use for StudentProfile/ClientProfile-style objects that have a `.user` FK."""
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return getattr(obj, 'user_id', None) == request.user.id


class IsStudentOwner(permissions.BasePermission):
    """Allow students to manage their own profile"""
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return getattr(obj, 'user_id', None) == request.user.id


class IsApplicationOwner(permissions.BasePermission):
    """Allow the applicant and the relevant client to view; only the applicant may write."""
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            allowed_users = {obj.student.user_id}
            if obj.project_id:
                allowed_users.add(obj.project.client.user_id)
            if obj.job_id:
                allowed_users.add(obj.job.client.user_id)
            return request.user.id in allowed_users
        return obj.student.user == request.user


class IsMessageParticipant(permissions.BasePermission):
    """Allow message participants to view/edit messages"""
    def has_object_permission(self, request, view, obj):
        return request.user == obj.sender or request.user == obj.recipient