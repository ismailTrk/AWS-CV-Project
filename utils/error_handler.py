"""
Error handling utilities for Lambda function
Centralizes error processing and provides consistent error responses
"""
import sys
from botocore.exceptions import ClientError
from utils.response_utils import (
    error_response, 
    throttling_response,
    resource_not_found_response,
    internal_server_error_response
)
from config.settings import HTTP_STATUS
def handle_ec2_error(error):
    """Handle EC2-specific errors"""
    print(f"EC2 error: {str(error)}")
    return response_utils.error_response(
        500,
        'EC2 service error',
        error_details={'error': str(error)}
    )
def handle_database_error(error):
    """
    Handle DynamoDB-specific errors and return appropriate HTTP responses
    
    Args:
        error: Exception object from database operation
        
    Returns:
        dict: Appropriate HTTP error response
    """
    if isinstance(error, ClientError):
        error_code = error.response['Error']['Code']
        error_message = error.response['Error']['Message']
        
        print(f"DynamoDB ClientError: {error_code} - {error_message}")
        
        # Map specific DynamoDB errors to HTTP responses
        if error_code == 'ResourceNotFoundException':
            return resource_not_found_response('Visitor counter table')
            
        elif error_code == 'ProvisionedThroughputExceededException':
            return throttling_response()
            
        elif error_code == 'ValidationException':
            return error_response(
                HTTP_STATUS['BAD_REQUEST'],
                'Invalid request format',
                error_details={'dbError': error_message}
            )
            
        elif error_code == 'ConditionalCheckFailedException':
            return error_response(
                HTTP_STATUS['BAD_REQUEST'], 
                'Operation condition not met',
                error_details={'reason': 'Counter may already exist'}
            )
            
        else:
            # Unknown DynamoDB error
            return error_response(
                HTTP_STATUS['INTERNAL_SERVER_ERROR'],
                'Database service error',
                error_details={'errorCode': error_code}
            )
    
    # Non-ClientError exceptions
    else:
        print(f"Unexpected database error: {str(error)}")
        return internal_server_error_response()

def handle_lambda_error(error, context=None):
    """
    Handle Lambda runtime errors
    
    Args:
        error: Exception object
        context: Lambda context (optional)
        
    Returns:
        dict: HTTP error response
    """
    error_type = type(error).__name__
    print(f"Lambda error: {error_type} - {str(error)}")
    
    # Don't expose internal error details to client
    if context:
        request_id = context.aws_request_id
        print(f"Request ID for debugging: {request_id}")
    
    return internal_server_error_response()

def log_error_details(error, event_data=None):
    """
    Log detailed error information for debugging
    
    Args:
        error: Exception object
        event_data: Lambda event data (optional)
    """
    print(f"Error Type: {type(error).__name__}")
    print(f"Error Message: {str(error)}")
    
    if hasattr(error, 'response'):
        print(f"Error Response: {error.response}")
    
    if event_data:
        print(f"Event Data: {event_data}")
    
    # Print stack trace for debugging
    import traceback
    print(f"Stack Trace: {traceback.format_exc()}")

def is_retryable_error(error):
    """
    Determine if an error is retryable
    
    Args:
        error: Exception object
        
    Returns:
        bool: True if error is retryable
    """
    if isinstance(error, ClientError):
        error_code = error.response['Error']['Code']
        
        # These errors are typically temporary and retryable
        retryable_codes = [
            'ProvisionedThroughputExceededException',
            'ThrottlingException', 
            'ServiceUnavailable',
            'InternalServerError'
        ]
        
        return error_code in retryable_codes
    
    return False
