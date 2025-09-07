"""
Configuration settings for the visitor counter service
Centralizes all configuration parameters and AWS connection settings
"""
import os
from botocore.config import Config

# Environment variables
TABLE_NAME = os.environ.get('VISITOR_COUNTER_TABLE')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

# DynamoDB configuration with connection pooling and retry logic
DYNAMODB_CONFIG = Config(
    retries={
        'max_attempts': 3,        # Retry failed requests up to 3 times
        'mode': 'adaptive'        # Use exponential backoff (1s, 2s, 4s)
    },
    max_pool_connections=10,      # Connection pool for concurrent requests
    region_name=AWS_REGION
)

# CORS configuration for browser compatibility
CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
}

# Security headers for production
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000'
}

# DynamoDB table configuration
COUNTER_ITEM_KEY = {'counterId': 'homePage'}
COUNTER_INITIAL_VALUE = 0

# HTTP status codes
HTTP_STATUS = {
    'OK': 200,
    'BAD_REQUEST': 400,
    'NOT_FOUND': 404,
    'METHOD_NOT_ALLOWED': 405,
    'TOO_MANY_REQUESTS': 429,
    'INTERNAL_SERVER_ERROR': 500
}
