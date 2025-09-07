"""
Database utilities for DynamoDB operations
Handles all database interactions with proper error handling and connection management
"""
import boto3
from botocore.exceptions import ClientError
from decimal import Decimal
from config.settings import DYNAMODB_CONFIG, TABLE_NAME, COUNTER_ITEM_KEY, COUNTER_INITIAL_VALUE

class DatabaseError(Exception):
    """Custom exception for database-related errors"""
    pass

class ThrottlingError(DatabaseError):
    """Exception for DynamoDB throttling scenarios"""
    pass

class ResourceNotFoundError(DatabaseError):
    """Exception for missing table or item scenarios"""
    pass

# Initialize DynamoDB client with optimized configuration
# This runs once during cold start and is reused across warm invocations
dynamodb = boto3.resource('dynamodb', config=DYNAMODB_CONFIG)
table = dynamodb.Table(TABLE_NAME)

def get_visitor_count():
    """
    Retrieve current visitor count from DynamoDB
    
    Returns:
        int: Current visitor count
        
    Raises:
        ResourceNotFoundError: If table or item doesn't exist
        ThrottlingError: If DynamoDB is throttling requests
        DatabaseError: For other DynamoDB errors
    """
    try:
        response = table.get_item(Key=COUNTER_ITEM_KEY)
        
        # Check if item exists
        if 'Item' not in response:
            print("Visitor counter item not found, returning 0")
            return 0
            
        count = response['Item'].get('visitorCount', 0)
        
        # Convert Decimal to int for JSON compatibility
        count = int(count) if isinstance(count, Decimal) else count
        
        print(f"Retrieved visitor count: {count}")
        return count
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"DynamoDB get_item error: {error_code} - {str(e)}")
        
        if error_code == 'ResourceNotFoundException':
            raise ResourceNotFoundError("Visitor counter table not found")
        elif error_code == 'ProvisionedThroughputExceededException':
            raise ThrottlingError("DynamoDB read capacity exceeded")
        else:
            raise DatabaseError(f"DynamoDB error: {error_code}")
    
    except Exception as e:
        print(f"Unexpected error in get_visitor_count: {str(e)}")
        raise DatabaseError("Unexpected database error occurred")

def increment_visitor_count():
    """
    Increment visitor count by 1 using atomic update operation
    Creates the counter if it doesn't exist (starts at 0)
    
    Returns:
        int: New visitor count after increment
        
    Raises:
        ResourceNotFoundError: If table doesn't exist
        ThrottlingError: If DynamoDB is throttling requests
        DatabaseError: For other DynamoDB errors
    """
    try:
        response = table.update_item(
            Key=COUNTER_ITEM_KEY,
            UpdateExpression='SET visitorCount = if_not_exists(visitorCount, :start) + :inc',
            ExpressionAttributeValues={
                ':inc': 1,
                ':start': COUNTER_INITIAL_VALUE
            },
            ReturnValues='UPDATED_NEW'
        )
        
        new_count = response['Attributes']['visitorCount']
        new_count = int(new_count) if isinstance(new_count, Decimal) else new_count
        
        print(f"Incremented visitor count to: {new_count}")
        return new_count
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"DynamoDB update_item error: {error_code} - {str(e)}")
        
        if error_code == 'ResourceNotFoundException':
            raise ResourceNotFoundError("Visitor counter table not found")
        elif error_code == 'ProvisionedThroughputExceededException':
            raise ThrottlingError("DynamoDB write capacity exceeded")
        else:
            raise DatabaseError(f"DynamoDB error: {error_code}")
    
    except Exception as e:
        print(f"Unexpected error in increment_visitor_count: {str(e)}")
        raise DatabaseError("Unexpected database error occurred")

def initialize_counter():
    """
    Initialize the visitor counter if it doesn't exist
    Uses conditional expression to prevent overwriting existing data
    
    Returns:
        bool: True if initialization successful, False otherwise
        
    Raises:
        DatabaseError: If initialization fails unexpectedly
    """
    try:
        table.put_item(
            Item={
                'counterId': 'homePage',
                'visitorCount': COUNTER_INITIAL_VALUE
            },
            ConditionExpression='attribute_not_exists(counterId)'
        )
        print("Visitor counter initialized successfully")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        
        if error_code == 'ConditionalCheckFailedException':
            print("Visitor counter already exists")
            return True
        else:
            print(f"Error initializing visitor counter: {str(e)}")
            raise DatabaseError(f"Counter initialization failed: {error_code}")
            
    except Exception as e:
        print(f"Unexpected error in initialization: {str(e)}")
        raise DatabaseError("Unexpected initialization error")

def health_check():
    """
    Perform health check by attempting to read from DynamoDB
    Used for monitoring and load balancer health checks
    
    Returns:
        dict: Health status information
    """
    try:
        # Simple read operation to verify connectivity
        table.get_item(Key=COUNTER_ITEM_KEY)
        
        return {
            'status': 'healthy',
            'table': TABLE_NAME,
            'connection': 'active',
            'timestamp': boto3.Session().region_name
        }
        
    except Exception as e:
        print(f"Health check failed: {str(e)}")
        return {
            'status': 'unhealthy',
            'table': TABLE_NAME,
            'error': str(e),
            'connection': 'failed'
        }

def get_table_info():
    """
    Get table metadata for monitoring and debugging
    
    Returns:
        dict: Table information
    """
    try:
        response = table.table_status
        return {
            'tableName': TABLE_NAME,
            'status': response,
            'itemCount': table.item_count
        }
    except Exception as e:
        print(f"Error getting table info: {str(e)}")
        return {
            'tableName': TABLE_NAME,
            'status': 'unknown',
            'error': str(e)
        }
