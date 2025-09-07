# config/ssl_settings.py
"""
SSL renewal service configuration
Centralizes SSL-specific configuration parameters and EC2 settings

Change it : 
1   SSL_SNS_TOPIC_ARN ,
2   SSL_CERTIFICATE_CONFIG = {
3        'domain': 'example.com',
4        'acm_arn': 'arn:aws:acm:region:account:certificate/certificate-id',
5   SSL_INSTANCE_ID 
6   AWS_REGION
"""
import os
from botocore.config import Config

# SSL Renewal EC2 Instance Configuration
SSL_INSTANCE_ID = os.environ.get('SSL_INSTANCE_ID', 'i-xxxxxxxxxxxxxxxxx')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

# EC2 configuration with retry logic
EC2_CONFIG = Config(
    retries={
        'max_attempts': 3,
        'mode': 'adaptive'
    },
    region_name=AWS_REGION
)

# SNS notification settings for SSL renewal
SSL_SNS_TOPIC_ARN = os.environ.get('SSL_SNS_TOPIC_ARN', 'arn:aws:sns:region:account:topic-name')

# SSL renewal timing configuration
SSL_RENEWAL_SCHEDULE = {
    'frequency_days': 20,
    'cron_expression': 'rate(20 days)',
    'estimated_duration_minutes': 15
}

# SSL certificate configuration
SSL_CERTIFICATE_CONFIG = {
    'domain': 'example.com',
    'acm_arn': 'arn:aws:acm:region:account:certificate/certificate-id',
    'validity_days': 90,
    'renewal_threshold_days': 20
}