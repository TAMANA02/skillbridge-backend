import django_filters
from rest_framework import filters
from api.models import Project, Job, StudentProfile


class ProjectFilter(django_filters.FilterSet):
    """Filter projects by category, status, budget, skills, etc."""
    category = django_filters.CharFilter(field_name='category', lookup_expr='iexact')
    status = django_filters.CharFilter(field_name='status', lookup_expr='iexact')
    experience_level = django_filters.CharFilter(field_name='experience_level', lookup_expr='iexact')
    budget_min_range = django_filters.NumberFilter(field_name='budget_min', lookup_expr='gte')
    budget_max_range = django_filters.NumberFilter(field_name='budget_max', lookup_expr='lte')
    is_featured = django_filters.BooleanFilter(field_name='is_featured')
    
    class Meta:
        model = Project
        fields = ['category', 'status', 'experience_level', 'is_featured']


class JobFilter(django_filters.FilterSet):
    """Filter jobs by type, status, location, salary, etc."""
    job_type = django_filters.CharFilter(field_name='job_type', lookup_expr='iexact')
    status = django_filters.CharFilter(field_name='status', lookup_expr='iexact')
    experience_level = django_filters.CharFilter(field_name='experience_level', lookup_expr='iexact')
    location = django_filters.CharFilter(field_name='location', lookup_expr='icontains')
    salary_min_range = django_filters.NumberFilter(field_name='salary_min', lookup_expr='gte')
    salary_max_range = django_filters.NumberFilter(field_name='salary_max', lookup_expr='lte')
    
    class Meta:
        model = Job
        fields = ['job_type', 'status', 'experience_level', 'location']


class StudentFilter(django_filters.FilterSet):
    """Filter students by skills, experience level, availability, rating"""
    skills = django_filters.CharFilter(field_name='skills', lookup_expr='icontains')
    experience_level = django_filters.CharFilter(field_name='experience_level', lookup_expr='iexact')
    availability = django_filters.CharFilter(field_name='availability', lookup_expr='iexact')
    min_rating = django_filters.NumberFilter(field_name='rating', lookup_expr='gte')
    max_rating = django_filters.NumberFilter(field_name='rating', lookup_expr='lte')
    is_featured = django_filters.BooleanFilter(field_name='is_featured')
    
    class Meta:
        model = StudentProfile
        fields = ['experience_level', 'availability', 'is_featured']