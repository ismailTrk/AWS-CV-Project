# utils/ec2_utils.py
"""
EC2 utilities for SSL renewal instance management
Handles all EC2 interactions with proper error handling and state management
"""
import boto3
from botocore.exceptions import ClientError
from config.ssl_settings import EC2_CONFIG, SSL_INSTANCE_ID

class EC2Error(Exception):
    """Custom exception for EC2-related errors"""
    pass

class InstanceNotFoundError(EC2Error):
    """Exception for missing instance scenarios"""
    pass

class InstanceStateError(EC2Error):
    """Exception for invalid instance state operations"""
    pass

# Initialize EC2 client
ec2 = boto3.client('ec2', config=EC2_CONFIG)

def start_ssl_renewal_instance():
    """
    Start the SSL renewal EC2 instance
    
    Returns:
        str: Instance ID of started instance
        
    Raises:
        InstanceNotFoundError: If instance doesn't exist
        InstanceStateError: If instance is in invalid state
        EC2Error: For other EC2 errors
    """
    try:
        # Check current instance state
        response = ec2.describe_instances(InstanceIds=[SSL_INSTANCE_ID])
        
        instance = response['Reservations'][0]['Instances'][0]
        current_state = instance['State']['Name']
        
        if current_state == 'running':
            print("Instance already running, SSL renewal may be in progress")
            return SSL_INSTANCE_ID  # Error vermek yerine instance ID döndür
        elif current_state in ['stopping', 'pending']:
            raise InstanceStateError(f"Instance is {current_state}, please wait")
        elif current_state not in ['stopped']:
            raise InstanceStateError(f"Instance in {current_state} state cannot be started")
        
        # Start the instance
        start_response = ec2.start_instances(InstanceIds=[SSL_INSTANCE_ID])
        
        print(f"SSL renewal instance {SSL_INSTANCE_ID} start initiated")
        return SSL_INSTANCE_ID
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"EC2 start_instances error: {error_code} - {str(e)}")
        
        if error_code == 'InvalidInstanceId.NotFound':
            raise InstanceNotFoundError(f"SSL renewal instance {SSL_INSTANCE_ID} not found")
        elif error_code == 'IncorrectInstanceState':
            raise InstanceStateError("Instance in incorrect state for starting")
        else:
            raise EC2Error(f"EC2 error: {error_code}")
    
    except IndexError:
        raise InstanceNotFoundError(f"Instance {SSL_INSTANCE_ID} not found in response")
    
    except Exception as e:
        print(f"Unexpected error in start_ssl_renewal_instance: {str(e)}")
        raise EC2Error("Unexpected EC2 error occurred")

def get_renewal_instance_status():
    """
    Get detailed status of SSL renewal instance
    
    Returns:
        dict: Instance status information
        
    Raises:
        InstanceNotFoundError: If instance doesn't exist
        EC2Error: For other EC2 errors
    """
    try:
        response = ec2.describe_instances(InstanceIds=[SSL_INSTANCE_ID])
        
        instance = response['Reservations'][0]['Instances'][0]
        
        status_info = {
            'instanceId': SSL_INSTANCE_ID,
            'state': instance['State']['Name'],
            'stateReason': instance['State'].get('Reason', 'N/A'),
            'instanceType': instance['InstanceType'],
            'launchTime': instance.get('LaunchTime'),
            'privateIpAddress': instance.get('PrivateIpAddress', 'N/A'),
            'publicIpAddress': instance.get('PublicIpAddress', 'N/A')
        }
        
        # Add estimated completion time if running
        if instance['State']['Name'] == 'running':
            status_info['estimatedCompletion'] = '10-15 minutes from start'
            status_info['renewalStatus'] = 'in_progress'
        elif instance['State']['Name'] == 'stopped':
            status_info['renewalStatus'] = 'completed_or_idle'
        else:
            status_info['renewalStatus'] = 'transitioning'
        
        return status_info
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"EC2 describe_instances error: {error_code} - {str(e)}")
        
        if error_code == 'InvalidInstanceId.NotFound':
            raise InstanceNotFoundError(f"SSL renewal instance {SSL_INSTANCE_ID} not found")
        else:
            raise EC2Error(f"EC2 error: {error_code}")
    
    except IndexError:
        raise InstanceNotFoundError(f"Instance {SSL_INSTANCE_ID} not found in response")
    
    except Exception as e:
        print(f"Unexpected error in get_renewal_instance_status: {str(e)}")
        raise EC2Error("Unexpected EC2 error occurred")

def ssl_service_health_check():
    """
    Perform health check for SSL renewal service
    
    Returns:
        dict: Health status information
    """
    try:
        # Check EC2 service connectivity and permissions
        response = ec2.describe_instances(InstanceIds=[SSL_INSTANCE_ID])
        
        instance = response['Reservations'][0]['Instances'][0]
        instance_state = instance['State']['Name']
        
        # Check if instance is in a valid state
        valid_states = ['running', 'stopped', 'stopping', 'pending']
        is_healthy = instance_state in valid_states
        
        return {
            'status': 'healthy' if is_healthy else 'unhealthy',
            'ec2Service': 'accessible',
            'instanceId': SSL_INSTANCE_ID,
            'instanceState': instance_state,
            'lastChecked': 'now'
        }
        
    except Exception as e:
        print(f"SSL service health check failed: {str(e)}")
        return {
            'status': 'unhealthy',
            'ec2Service': 'inaccessible',
            'error': str(e),
            'lastChecked': 'now'
        }