"""
Counter service - Business logic for visitor counter operations
Implements core business rules and orchestrates database operations
"""
from utils import db_utils, response_utils, error_handler
from utils.db_utils import (
    DatabaseError, 
    ThrottlingError, 
    ResourceNotFoundError
)

def get_visitor_count():
    """
    Service method to retrieve current visitor count
    Handles business logic and error scenarios
    
    Returns:
        dict: HTTP response with visitor count or error
    """
    try:
        count = db_utils.get_visitor_count()
        
        return response_utils.success_response(
            data={'count': count},
            message='Visitor count retrieved successfully'
        )
        
    except ResourceNotFoundError:
        # Table or counter doesn't exist - return 0 as default
        return response_utils.success_response(
            data={'count': 0},
            message='Counter initialized with default value'
        )
        
    except ThrottlingError:
        return response_utils.throttling_response()
        
    except DatabaseError as e:
        return error_handler.handle_database_error(e)
        
    except Exception as e:
        error_handler.log_error_details(e)
        return response_utils.internal_server_error_response()

def increment_visitor_count():
    """
    Service method to increment visitor count
    Handles atomic increment with proper error handling
    
    Returns:
        dict: HTTP response with new count or error
    """
    try:
        new_count = db_utils.increment_visitor_count()
        
        return response_utils.success_response(
            data={'count': new_count},
            message='Visitor count updated successfully'
        )
        
    except ResourceNotFoundError:
        return response_utils.resource_not_found_response('Visitor counter table')
        
    except ThrottlingError:
        return response_utils.throttling_response()
        
    except DatabaseError as e:
        return error_handler.handle_database_error(e)
        
    except Exception as e:
        error_handler.log_error_details(e)
        return response_utils.internal_server_error_response()

def initialize_counter_service():
    """
    Initialize visitor counter with business validation
    
    Returns:
        dict: HTTP response indicating initialization status
    """
    try:
        success = db_utils.initialize_counter()
        
        if success:
            return response_utils.success_response(
                data={'initialized': True},
                message='Visitor counter initialized successfully'
            )
        else:
            return response_utils.error_response(
                500,
                'Failed to initialize visitor counter'
            )
            
    except DatabaseError as e:
        return error_handler.handle_database_error(e)
        
    except Exception as e:
        error_handler.log_error_details(e)
        return response_utils.internal_server_error_response()

def get_service_health():
    """
    Get comprehensive service health information
    Includes database connectivity and service status
    
    Returns:
        dict: HTTP response with health status
    """
    try:
        # Check database health
        db_health = db_utils.health_check()
        
        # Check table information
        table_info = db_utils.get_table_info()
        
        # Determine overall service health
        overall_status = 'healthy' if db_health['status'] == 'healthy' else 'unhealthy'
        
        health_data = {
            'service': 'visitor-counter',
            'status': overall_status,
            'database': db_health,
            'table': table_info
        }
        
        status_code = 200 if overall_status == 'healthy' else 503
        
        return response_utils.create_response(
            status_code,
            health_data
        )
        
    except Exception as e:
        error_handler.log_error_details(e)
        return response_utils.error_response(
            503,
            'Service health check failed',
            error_details={'error': str(e)}
        )

def get_counter_analytics():
    """
    Get analytics information about the counter
    Future enhancement for dashboard analytics
    
    Returns:
        dict: HTTP response with analytics data
    """
    try:
        current_count = db_utils.get_visitor_count()
        table_info = db_utils.get_table_info()
        
        analytics_data = {
            'currentCount': current_count,
            'tableStatus': table_info['status'],
            'lastUpdate': 'calculated_timestamp_here'  # TODO: Add timestamp tracking
        }
        
        return response_utils.success_response(
            data=analytics_data,
            message='Analytics data retrieved successfully'
        )
        
    except Exception as e:
        error_handler.log_error_details(e)
        return response_utils.internal_server_error_response()
