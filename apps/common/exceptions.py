"""
Custom exception handlers for Cynosure API.
"""
import logging
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    ValidationError as DRFValidationError,
    NotAuthenticated,
    PermissionDenied,
    NotFound,
    Throttled,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error responses.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    # Get request info for logging
    request = context.get('request')
    view = context.get('view')
    
    if response is not None:
        # Customize the response data
        custom_response_data = {
            'success': False,
            'error': {
                'code': get_error_code(exc),
                'message': get_error_message(exc, response),
                'details': get_error_details(exc, response),
            }
        }
        
        # Add request ID if available
        if hasattr(request, 'id'):
            custom_response_data['request_id'] = str(request.id)
        
        response.data = custom_response_data
        
        # Log the error
        log_exception(exc, context, response)
        
        return response
    
    # Handle Django's ValidationError
    if isinstance(exc, DjangoValidationError):
        errors = exc.message_dict if hasattr(exc, 'message_dict') else {'detail': exc.messages}
        return Response(
            {
                'success': False,
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': 'Validation failed',
                    'details': errors,
                }
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Handle unexpected exceptions
    logger.exception(f"Unhandled exception in {view}: {exc}")
    
    return Response(
        {
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An unexpected error occurred',
                'details': None,
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def get_error_code(exc):
    """Get a standardized error code for the exception."""
    error_codes = {
        DRFValidationError: 'VALIDATION_ERROR',
        NotAuthenticated: 'AUTHENTICATION_REQUIRED',
        PermissionDenied: 'PERMISSION_DENIED',
        NotFound: 'NOT_FOUND',
        Http404: 'NOT_FOUND',
        Throttled: 'RATE_LIMIT_EXCEEDED',
    }
    
    for exc_class, code in error_codes.items():
        if isinstance(exc, exc_class):
            return code
    
    if hasattr(exc, 'default_code'):
        return exc.default_code.upper()
    
    return 'ERROR'


def get_error_message(exc, response):
    """Get a user-friendly error message."""
    if isinstance(exc, Throttled):
        return f'Request throttled. Try again in {exc.wait} seconds.'
    
    if isinstance(exc, NotAuthenticated):
        return 'Authentication credentials were not provided or are invalid.'
    
    if isinstance(exc, PermissionDenied):
        return str(exc.detail) if hasattr(exc, 'detail') else 'You do not have permission to perform this action.'
    
    if isinstance(exc, (NotFound, Http404)):
        return 'The requested resource was not found.'
    
    if isinstance(exc, DRFValidationError):
        return 'The submitted data was invalid.'
    
    if hasattr(exc, 'detail'):
        return str(exc.detail)
    
    return 'An error occurred'


def get_error_details(exc, response):
    """Get detailed error information."""
    if isinstance(exc, DRFValidationError):
        return response.data
    
    if hasattr(exc, 'detail') and isinstance(exc.detail, dict):
        return exc.detail
    
    return None


def log_exception(exc, context, response):
    """Log exception details."""
    request = context.get('request')
    view = context.get('view')
    
    log_data = {
        'exception': exc.__class__.__name__,
        'message': str(exc),
        'status_code': response.status_code,
        'path': request.path if request else None,
        'method': request.method if request else None,
        'user': str(request.user) if request and hasattr(request, 'user') else None,
        'view': view.__class__.__name__ if view else None,
    }
    
    if response.status_code >= 500:
        logger.error(f"Server error: {log_data}")
    elif response.status_code >= 400:
        logger.warning(f"Client error: {log_data}")


# Custom Exception Classes
class CynosureException(APIException):
    """Base exception for Cynosure-specific errors."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'A server error occurred.'
    default_code = 'error'


class ResourceNotFoundException(CynosureException):
    """Raised when a requested resource is not found."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'The requested resource was not found.'
    default_code = 'not_found'


class ResourceAlreadyExistsException(CynosureException):
    """Raised when trying to create a duplicate resource."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'This resource already exists.'
    default_code = 'already_exists'


class InvalidOperationException(CynosureException):
    """Raised when an operation is not allowed."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'This operation is not allowed.'
    default_code = 'invalid_operation'


class FileTooLargeException(CynosureException):
    """Raised when uploaded file is too large."""
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    default_detail = 'The uploaded file is too large.'
    default_code = 'file_too_large'


class InvalidFileTypeException(CynosureException):
    """Raised when file type is not allowed."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'This file type is not allowed.'
    default_code = 'invalid_file_type'


class ScrapingException(CynosureException):
    """Raised when scraping operation fails."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'Failed to scrape data.'
    default_code = 'scraping_error'


class NotificationException(CynosureException):
    """Raised when notification delivery fails."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'Failed to send notification.'
    default_code = 'notification_error'


class OTPException(CynosureException):
    """Raised for OTP-related errors."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'OTP verification failed.'
    default_code = 'otp_error'


class AccountLockedException(CynosureException):
    """Raised when account is locked due to too many failed attempts."""
    status_code = status.HTTP_423_LOCKED
    default_detail = 'Account is locked due to too many failed attempts.'
    default_code = 'account_locked'
