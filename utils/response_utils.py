"""
HTTP response utilities for Lambda function
Handles HTTP response formatting, CORS headers, and error responses
"""
import json
from decimal import Decimal
from datetime import datetime
from config.settings import CORS_HEADERS, SECURITY_HEADERS, HTTP_STATUS

class DecimalEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle AWS-specific data types that are not natively JSON serializable
    
    Handles:
    - Decimal: DynamoDB returns numbers as Decimal objects 
    - datetime: AWS API responses contain datetime objects (EC2 LaunchTime, etc.)
    
    Converts these types to JSON-compatible formats automatically during response serialization
    """
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj)  # Convert DynamoDB Decimal to integer
        elif isinstance(obj, datetime):
            return obj.isoformat()  # Convert datetime to ISO 8601 string format
        return super(DecimalEncoder, self).default(obj)

def create_response(status_code, body, additional_headers=None):
    """
    Create standardized HTTP response with CORS and security headers
    
    Args:
        status_code (int): HTTP status code
        body (dict): Response body data
        additional_headers (dict): Additional headers to include
    
    Returns:
        dict: Lambda HTTP response format compatible with API Gateway
    """
    # Start with CORS headers for all responses
    headers = CORS_HEADERS.copy()
    
    # Add security headers for production hardening
    headers.update(SECURITY_HEADERS)
    
    # Add any additional headers if provided
    if additional_headers:
        headers.update(additional_headers)
    
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(body, cls=DecimalEncoder)
    }

def success_response(data, message="Operation completed successfully"):
    """
    Create successful HTTP response (200 OK)
    
    Args:
        data (dict): Response data
        message (str): Success message
        
    Returns:
        dict: HTTP response
    """
    body = {'message': message, **data}
    return create_response(HTTP_STATUS['OK'], body)

def error_response(status_code, message, error_details=None, include_retry=False):
    """
    Create error HTTP response with appropriate status codes
    
    Args:
        status_code (int): HTTP error status code
        message (str): User-friendly error message
        error_details (str): Additional error information (optional)
        include_retry (bool): Whether to suggest retry
        
    Returns:
        dict: HTTP error response
    """
    body = {'message': message}
    
    if error_details:
        body['details'] = error_details
        
    if include_retry:
        body['retry'] = True
        body['retryAfter'] = 30  # seconds
    
    return create_response(status_code, body)

def cors_preflight_response():
    """
    Handle CORS preflight OPTIONS request
    Browser sends this before actual request to check CORS policy
    
    Returns:
        dict: CORS preflight response (200 OK)
    """
    return create_response(
        HTTP_STATUS['OK'], 
        {'message': 'CORS preflight successful'}
    )

def method_not_allowed_response(method):
    """
    Handle unsupported HTTP methods
    
    Args:
        method (str): The unsupported HTTP method
        
    Returns:
        dict: HTTP 405 Method Not Allowed response
    """
    return error_response(
        HTTP_STATUS['METHOD_NOT_ALLOWED'],
        f'Method {method} not allowed',
        error_details={'supportedMethods': ['GET', 'POST', 'OPTIONS']}
    )

def validation_error_response(validation_errors):
    """
    Handle request validation errors
    
    Args:
        validation_errors (list): List of validation error messages
        
    Returns:
        dict: HTTP 400 Bad Request response
    """
    return error_response(
        HTTP_STATUS['BAD_REQUEST'],
        'Request validation failed',
        error_details={'validationErrors': validation_errors}
    )

def throttling_response():
    """
    Handle DynamoDB throttling or rate limiting
    
    Returns:
        dict: HTTP 429 Too Many Requests response
    """
    return error_response(
        HTTP_STATUS['TOO_MANY_REQUESTS'],
        'Service temporarily busy, please try again',
        include_retry=True
    )

def resource_not_found_response(resource_name):
    """
    Handle resource not found scenarios
    
    Args:
        resource_name (str): Name of the missing resource
        
    Returns:
        dict: HTTP 404 Not Found response
    """
    return error_response(
        HTTP_STATUS['NOT_FOUND'],
        f'{resource_name} not found or not initialized'
    )

def internal_server_error_response(include_debug_info=False):
    """
    Handle unexpected errors - don't expose internal details in production
    
    Args:
        include_debug_info (bool): Whether to include debug information
        
    Returns:
        dict: HTTP 500 Internal Server Error response
    """
    message = 'Internal server error occurred'
    details = None
    
    if include_debug_info:
        # Only include in development environment
        details = 'Check CloudWatch logs for detailed error information'
    
    return error_response(
        HTTP_STATUS['INTERNAL_SERVER_ERROR'],
        message,
        error_details=details
    )
