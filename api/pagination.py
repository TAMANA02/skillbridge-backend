from rest_framework.pagination import PageNumberPagination
from decouple import config


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for list views"""
    page_size = config('API_PAGINATION_SIZE', default=20, cast=int)
    page_size_query_param = 'page_size'
    max_page_size = 100


class ProjectPagination(PageNumberPagination):
    """Pagination for projects"""
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 100


class StudentPagination(PageNumberPagination):
    """Pagination for student profiles"""
    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 100