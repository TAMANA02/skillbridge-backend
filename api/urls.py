from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from api.views import (
    RegisterViewSet, LoginViewSet, LogoutView,
    StudentViewSet, ClientViewSet,
    ProjectViewSet, JobViewSet,
        ApplicationViewSet, MessageViewSet,
    ReviewViewSet, NotificationViewSet,
    CollegeViewSet, TeamViewSet, FeedPostViewSet

)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'students', StudentViewSet, basename='student')
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'jobs', JobViewSet, basename='job')
router.register(r'applications', ApplicationViewSet, basename='application')
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'colleges', CollegeViewSet, basename='college')
router.register(r'teams', TeamViewSet, basename='team')
router.register(r'feed', FeedPostViewSet, basename='feed')

# Auth routes (custom)
auth_patterns = [
    path('register/', RegisterViewSet.as_view({'post': 'student'}), name='register-student'),
    path('register/student/', RegisterViewSet.as_view({'post': 'student'}), name='student-register'),
    path('register/client/', RegisterViewSet.as_view({'post': 'client'}), name='client-register'),
    path('login/', LoginViewSet.as_view({'post': 'create'}), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
]

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include(auth_patterns)),
]