# Updated lambda_function.py
"""
Main Lambda handler - Routes requests to appropriate service methods
Extended to include SSL renewal endpoints
"""
import json
from services import counter_service, ssl_service
from utils import response_utils, error_handler
from config.settings import HTTP_STATUS

def lambda_handler(event, context):
    """
    Main Lambda entry point - routes HTTP requests to appropriate handlers
    """
    if event.get('source') == 'eventbridge':
        print("EventBridge triggered SSL renewal")
        return ssl_service.trigger_ssl_renewal()
    
    try:
        
        # Extract request metadata (4 spaces indented)
        http_method = event.get('httpMethod', '').upper()
        headers = event.get('headers') or {}
        origin = headers.get('origin') or headers.get('Origin', '')
        path = event.get('path', 'Unknown')
        
        print(f"Request: {http_method} {path} from {origin}")
        
        # Handle CORS preflight for all endpoints
        if http_method == 'OPTIONS':
            return response_utils.cors_preflight_response()
        
        # Route based on path
        if path.startswith('/ssl'):
            return handle_ssl_requests(http_method, path, event, context)
        elif path.startswith('/counter') or path == '/':
            return handle_counter_requests(http_method, event, context)
        elif path.startswith('/health'):
            return handle_health_requests(http_method, context)
        else:
            return response_utils.error_response(
                404, 
                f"Path {path} not found",
                error_details={'availablePaths': ['/counter', '/ssl', '/health']}
            )
    
    except Exception as e:
        error_handler.log_error_details(e, event)
        return error_handler.handle_lambda_error(e, context)

def handle_ssl_requests(http_method, path, event, context):
    """Handle SSL renewal related requests"""
    
    if path == '/ssl/renew' and http_method == 'POST':
        print("Routing to SSL renewal trigger")
        return ssl_service.trigger_ssl_renewal()
        
    elif path == '/ssl/status' and http_method == 'GET':
        print("Routing to SSL renewal status check")
        return ssl_service.get_ssl_renewal_status()
        
    elif path == '/ssl/health' and http_method == 'GET':
        print("Routing to SSL service health check")
        return ssl_service.get_ssl_service_health()
        
    else:
        return response_utils.error_response(
            404,
            f"SSL endpoint {path} not found or method {http_method} not supported",
            error_details={
                'availableEndpoints': [
                    'POST /ssl/renew',
                    'GET /ssl/status', 
                    'GET /ssl/health'
                ]
            }
        )

def handle_counter_requests(http_method, event, context):
    """Handle visitor counter requests (existing functionality)"""
    
    if http_method == 'GET':
        print("Routing to get visitor count service")
        return counter_service.get_visitor_count()
        
    elif http_method == 'POST':
        print("Routing to increment visitor count service")
        return counter_service.increment_visitor_count()
        
    else:
        return response_utils.method_not_allowed_response(http_method)

def handle_health_requests(http_method, context):
    """Handle service health check requests"""
    
    if http_method != 'GET':
        return response_utils.method_not_allowed_response(http_method)
    
    try:
        # Get health status from both services
        counter_health = counter_service.get_service_health()
        ssl_health = ssl_service.get_ssl_service_health()
        
        # Combine health statuses
        overall_healthy = (
            counter_health.get('statusCode', 500) == 200 and
            ssl_health.get('statusCode', 500) == 200
        )
        
        combined_health = {
            'service': 'multi-service-lambda',
            'status': 'healthy' if overall_healthy else 'degraded',
            'services': {
                'visitorCounter': json.loads(counter_health.get('body', '{}')),
                'sslRenewal': json.loads(ssl_health.get('body', '{}'))
            },
            'requestId': context.aws_request_id
        }
        
        status_code = 200 if overall_healthy else 503
        return response_utils.create_response(status_code, combined_health)
        
    except Exception as e:
        error_handler.log_error_details(e)
        return response_utils.error_response(
            503,
            'Health check failed',
            error_details={'error': str(e)}
        )

# Separate Lambda function for EventBridge triggered SSL renewal
def ssl_renewal_handler(event, context):
    """
    Dedicated handler for EventBridge scheduled SSL renewal
    This runs every 20 days automatically
    """
    print("EventBridge triggered SSL renewal starting...")
    
    try:
        # This is triggered by EventBridge, not API Gateway
        result = ssl_service.trigger_ssl_renewal()
        
        print(f"SSL renewal trigger result: {result}")
        return result
        
    except Exception as e:
        error_handler.log_error_details(e, event)
        print(f"SSL renewal failed: {str(e)}")
        
        # Return error but don't crash the scheduler
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'SSL renewal failed',
                'details': str(e),
                'requestId': context.aws_request_id
            })
        }