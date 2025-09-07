# services/ssl_service.py
"""
SSL renewal service - Business logic for SSL certificate renewal operations
Orchestrates EC2 instance management for certificate renewal automation
"""
from utils import ec2_utils, response_utils, error_handler
from utils.ec2_utils import (
    EC2Error,
    InstanceNotFoundError,
    InstanceStateError
)

def trigger_ssl_renewal():
    """
    Service method to trigger SSL certificate renewal process
    Starts EC2 instance that runs the renewal script
    
    Returns:
        dict: HTTP response with operation status or error
    """
    try:
        instance_id = ec2_utils.start_ssl_renewal_instance()
        
        return response_utils.success_response(
            data={
                'instanceId': instance_id,
                'status': 'SSL renewal process initiated',
                'estimatedDuration': '10-15 minutes'
            },
            message='SSL renewal instance started successfully'
        )
        
    except InstanceNotFoundError:
        return response_utils.resource_not_found_response('SSL renewal EC2 instance')
        
    except InstanceStateError as e:
        return response_utils.error_response(
            400,
            'Instance cannot be started',
            error_details={'reason': str(e)}
        )
        
    except EC2Error as e:
        return error_handler.handle_ec2_error(e)
        
    except Exception as e:
        error_handler.log_error_details(e)
        return response_utils.internal_server_error_response()

def get_ssl_renewal_status():
    """
    Service method to check status of SSL renewal process
    
    Returns:
        dict: HTTP response with current renewal status
    """
    try:
        status_info = ec2_utils.get_renewal_instance_status()
        
        return response_utils.success_response(
            data=status_info,
            message='SSL renewal status retrieved successfully'
        )
        
    except InstanceNotFoundError:
        return response_utils.resource_not_found_response('SSL renewal instance')
        
    except EC2Error as e:
        return error_handler.handle_ec2_error(e)
        
    except Exception as e:
        error_handler.log_error_details(e)
        return response_utils.internal_server_error_response()

def get_ssl_service_health():
    """
    Health check for SSL renewal service
    Verifies EC2 permissions and instance availability
    
    Returns:
        dict: HTTP response with SSL service health status
    """
    try:
        health_data = ec2_utils.ssl_service_health_check()
        
        overall_status = 'healthy' if health_data['status'] == 'healthy' else 'unhealthy'
        status_code = 200 if overall_status == 'healthy' else 503
        
        return response_utils.create_response(
            status_code,
            {
                'service': 'ssl-renewal',
                'status': overall_status,
                **health_data
            }
        )
        
    except Exception as e:
        error_handler.log_error_details(e)
        return response_utils.error_response(
            503,
            'SSL service health check failed',
            error_details={'error': str(e)}
        )