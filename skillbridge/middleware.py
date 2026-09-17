"""
Custom middleware for SkillBridge Django project.
"""

import logging
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied

logger = logging.getLogger(__name__)


class CustomExceptionMiddleware(MiddlewareMixin):
    """Handle custom exceptions and return JSON responses"""
    
    def process_exception(self, request, exception):
        """Process exceptions and return JSON response"""
        
        if isinstance(exception, PermissionDenied):
            return JsonResponse({
                'error': 'Permission denied',
                'detail': str(exception)
            }, status=403)
        
        # Log the exception
        logger.error(f"Exception: {str(exception)}", exc_info=True)
        
        # Return generic error for unhandled exceptions
        return JsonResponse({
            'error': 'An error occurred',
            'detail': 'Please try again later'
        }, status=500)


class RequestLoggingMiddleware(MiddlewareMixin):
    """Log all incoming requests"""
    
    def process_request(self, request):
        """Log request details"""
        logger.info(f"{request.method} {request.path} - {request.META.get('REMOTE_ADDR')}")
        return None
    
    def process_response(self, request, response):
        """Log response status"""
        logger.info(f"{request.method} {request.path} - {response.status_code}")
        return response


class APIResponseMiddleware(MiddlewareMixin):
    """Standardize API responses"""
    
    def process_response(self, request, response):
        """Add metadata to API responses"""
        
        # Only process API endpoints
        if request.path.startswith('/api/'):
            try:
                # Add request ID for tracking
                if hasattr(request, 'id'):
                    response['X-Request-ID'] = request.id
                
                # Add timestamp
                from django.utils import timezone
                response['X-Timestamp'] = timezone.now().isoformat()
                
            except Exception as e:
                logger.error(f"Error in APIResponseMiddleware: {str(e)}")
        
        return response


class AuthenticationMiddleware(MiddlewareMixin):
    """Handle authentication-related middleware"""
    
    def process_request(self, request):
        """Process authentication on every request"""
        
        # Skip authentication for public endpoints
        public_paths = ['/api/auth/login/', '/api/auth/register/']
        
        if any(request.path.startswith(path) for path in public_paths):
            return None
        
        # Log authenticated user
        if request.user.is_authenticated:
            logger.debug(f"Authenticated user: {request.user.email}")
        
        return None


class ErrorHandlingMiddleware(MiddlewareMixin):
    """Handle and log errors"""
    
    def process_exception(self, request, exception):
        """Log and handle exceptions"""
        
        error_type = type(exception).__name__
        error_message = str(exception)
        
        logger.error(
            f"Error Type: {error_type}\n"
            f"Error Message: {error_message}\n"
            f"Path: {request.path}\n"
            f"Method: {request.method}\n"
            f"User: {request.user.email if request.user.is_authenticated else 'Anonymous'}"
        )
        
        # Return appropriate error response
        if error_type == 'ValidationError':
            return JsonResponse({
                'error': 'Validation Error',
                'details': error_message
            }, status=400)
        
        elif error_type == 'PermissionDenied':
            return JsonResponse({
                'error': 'Permission Denied',
                'details': error_message
            }, status=403)
        
        elif error_type == 'ObjectDoesNotExist':
            return JsonResponse({
                'error': 'Not Found',
                'details': 'The requested resource was not found'
            }, status=404)
        
        # Generic error response
        return JsonResponse({
            'error': 'Internal Server Error',
            'details': 'An unexpected error occurred'
        }, status=500)