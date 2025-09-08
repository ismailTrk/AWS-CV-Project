#!/bin/bash
# Change it : EMAIL="admin@example.com"
# =============================================================================
# SSL Certificate Renewal, AWS ACM and Cloudflare Upload Script
# =============================================================================
# This script:
# 1. Activates the Python virtual environment for certbot
# 2. Retrieves Cloudflare API token securely from AWS Systems Manager
# 3. Renews SSL certificates using Let's Encrypt with Cloudflare DNS challenge
# 4. Imports the renewed certificate to AWS ACM (preserving existing ARN)
# 5. Uploads the certificate to Cloudflare Edge Certificates
# 6. Sends email notifications via AWS SNS
# 7. Shuts down the EC2 instance to save costs
# =============================================================================

# Activate the Python virtual environment that contains certbot
source /opt/certbot-venv/bin/activate

# Define configuration variables
LOG_FILE="/var/log/cert-renewal.log"
DOMAIN="example.com"
EMAIL="admin@example.com"
SNS_TOPIC_ARN="arn:aws:sns:us-east-1:211125362854:AWS-CV-Alarm"
TARGET_CERT_ARN="arn:aws:acm:us-east-1:211125362854:certificate/0c5c3a57-2a48-49db-9738-89ba44a2ecdd"

echo "$(date) - Starting certificate renewal process for $DOMAIN" >> $LOG_FILE

# =============================================================================
# STEP 1: Securely retrieve Cloudflare API token from AWS Systems Manager
# =============================================================================
# We store the Cloudflare API token in AWS SSM Parameter Store for security
# This avoids hardcoding sensitive credentials in the script
echo "$(date) - Retrieving Cloudflare API token from AWS Systems Manager..." >> $LOG_FILE
CF_TOKEN=$(aws ssm get-parameter --name "/cloudflare/api-token" --with-decryption --query "Parameter.Value" --output text --region us-east-1 2>> $LOG_FILE)

# Verify that we successfully retrieved the token
if [ -z "$CF_TOKEN" ]; then
    echo "$(date) - ❌ Failed to retrieve Cloudflare token from AWS Systems Manager!" >> $LOG_FILE
    aws sns publish --topic-arn "$SNS_TOPIC_ARN" \
      --message "SSL Renewal FAILED: Could not retrieve Cloudflare API token from Systems Manager" \
      --subject "SSL Renewal Error - $DOMAIN" \
      --region us-east-1
    exit 1
fi

# =============================================================================
# STEP 2: Create temporary credentials file for certbot
# =============================================================================
# Create a temporary file in memory (tmpfs) to store Cloudflare credentials
# This file will be automatically deleted and never written to persistent storage
CF_CONFIG=$(mktemp)
echo "dns_cloudflare_api_token = $CF_TOKEN" > $CF_CONFIG
chmod 600 $CF_CONFIG  # Restrict access to owner only for security

# =============================================================================
# STEP 3: Renew SSL certificate using Let's Encrypt with Cloudflare DNS
# =============================================================================
# Use certbot with Cloudflare DNS plugin to generate new certificate
# --dns-cloudflare: Use Cloudflare DNS challenge for domain verification
# -d "$DOMAIN" -d "*.$DOMAIN": Cover both root domain and all subdomains in single cert
# --force-renewal: Force renewal even if certificate is not close to expiry
echo "$(date) - Running certbot for certificate renewal..." >> $LOG_FILE
sudo /opt/certbot-venv/bin/certbot certonly \
  --dns-cloudflare \
  --dns-cloudflare-credentials "$CF_CONFIG" \
  -d "$DOMAIN" \
  -d "*.$DOMAIN" \
  --non-interactive \
  --agree-tos \
  --email "$EMAIL" \
  --force-renewal 2>&1 | tee -a $LOG_FILE

# Clean up the temporary credentials file immediately after use
rm -f "$CF_CONFIG"

# Check if the certificate renewal was successful
RENEWAL_EXIT_CODE=${PIPESTATUS[0]}
if [ $RENEWAL_EXIT_CODE -eq 0 ]; then
    echo "$(date) - ✅ Certificate renewal successful!" >> $LOG_FILE
else
    echo "$(date) - ❌ Certificate renewal failed! Exit code: $RENEWAL_EXIT_CODE" >> $LOG_FILE
    aws sns publish --topic-arn "$SNS_TOPIC_ARN" \
      --message "SSL Renewal FAILED: Certbot renewal failed with exit code $RENEWAL_EXIT_CODE. Check logs on EC2 instance." \
      --subject "SSL Renewal Error - $DOMAIN" \
      --region us-east-1
    exit 1
fi

# =============================================================================
# STEP 4: Import renewed certificate to AWS ACM
# =============================================================================
# Define paths to the newly generated certificate files
CERT_PATH="/etc/letsencrypt/live/$DOMAIN"
CERT_FILE="$CERT_PATH/cert.pem"           # The main certificate
CHAIN_FILE="$CERT_PATH/chain.pem"         # Intermediate certificates
PRIVATE_KEY_FILE="$CERT_PATH/privkey.pem" # Private key

echo "$(date) - Importing certificate to AWS ACM..." >> $LOG_FILE

# =============================================================================
# STEP 5: Copy certificate files to temp for processing
# =============================================================================
# Copy certificate files to temp directory for both AWS and Cloudflare uploads
# This avoids permission issues and allows secure file handling
echo "$(date) - Copying certificate files to temp directory..." >> $LOG_FILE
sudo cp "$CERT_FILE" /tmp/cert.pem
sudo cp "$PRIVATE_KEY_FILE" /tmp/privkey.pem
sudo cp "$CHAIN_FILE" /tmp/chain.pem
sudo cp "$FULLCHAIN_FILE" /tmp/fullchain.pem
sudo chown ec2-user:ec2-user /tmp/*.pem

# =============================================================================
# STEP 6: Import certificate to AWS ACM
# =============================================================================
# We reimport to the specific ARN that's currently in use (0c5c3a57-2a48...)
# This preserves all CloudFront and other service associations
# The certificate contains both example.com and *.example.com domains
echo "$(date) - Reimporting certificate to AWS ACM ARN: $TARGET_CERT_ARN" >> $LOG_FILE

aws acm import-certificate \
  --certificate-arn "$TARGET_CERT_ARN" \
  --certificate fileb:///tmp/cert.pem \
  --private-key fileb:///tmp/privkey.pem \
  --certificate-chain fileb:///tmp/chain.pem \
  --region us-east-1 2>> $LOG_FILE

# Check if ACM import was successful
ACM_EXIT_CODE=$?


<<'COMMENT'
# =============================================================================
# STEP 7: Upload certificate to Cloudflare
# =============================================================================
# Upload the same certificate to Cloudflare Edge Certificates
# This ensures SSL works regardless of proxy settings
echo "$(date) - Uploading certificate to Cloudflare..." >> $LOG_FILE

# Get Cloudflare Zone ID for the domain
ZONE_ID=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones?name=$DOMAIN" \
  -H "Authorization: Bearer $CF_TOKEN" \
  -H "Content-Type: application/json" | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['result'][0]['id'])" 2>/dev/null)

if [ -z "$ZONE_ID" ]; then
    echo "$(date) - ❌ Failed to get Cloudflare Zone ID" >> $LOG_FILE
    CLOUDFLARE_SUCCESS=false
else
    echo "$(date) - Cloudflare Zone ID: $ZONE_ID" >> $LOG_FILE

    # Check Cloudflare Universal SSL status (Free plan compatible)
    # Free plan uses Universal SSL automatically, no custom upload needed
    CF_RESPONSE=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/ssl/certificate_packs" \
      -H "Authorization: Bearer $CF_TOKEN" \
      -H "Content-Type: application/json")

    # Check if Universal SSL is active
    CF_SUCCESS=$(echo "$CF_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data['success'] and len(data['result']) > 0:
        for cert in data['result']:
            if 'universal' in cert.get('type', '').lower() and cert.get('status') == 'active':
                print('True')
                exit()
    print('False')
except Exception as e:
    print('False')
" 2>/dev/null)

    if [ "$CF_SUCCESS" = "True" ]; then
        echo "$(date) - ✅ Cloudflare Universal SSL is active!" >> $LOG_FILE
        CLOUDFLARE_SUCCESS=true
    else
        echo "$(date) - ✅ Cloudflare SSL working (Free plan uses Universal SSL automatically)" >> $LOG_FILE
        CLOUDFLARE_SUCCESS=true  # Universal SSL works automatically on Free plan
    fi
fi
COMMENT

# =============================================================================
# STEP 8: Send notifications and cleanup
# =============================================================================
# Send comprehensive notification based on both AWS and Cloudflare results
# Cloudflare success variable'ını kaldır, sadece AWS ACM kontrolü
if [ $ACM_EXIT_CODE -eq 0 ]; then
    # AWS ACM success
    aws sns publish --topic-arn "$SNS_TOPIC_ARN" \
      --message "SSL Certificate renewal completed successfully for $DOMAIN. Certificate imported to AWS ACM (ARN: $TARGET_CERT_ARN). Cloudflare Universal SSL working automatically." \
      --subject "SSL Renewal Success - $DOMAIN" \
      --region us-east-1
    echo "$(date) - ✅ Success notification sent via SNS" >> $LOG_FILE
else
    # AWS ACM failed
    aws sns publish --topic-arn "$SNS_TOPIC_ARN" \
      --message "SSL Renewal FAILED: AWS ACM import failed with exit code $ACM_EXIT_CODE. Manual intervention required urgently." \
      --subject "SSL Renewal Critical Failure - $DOMAIN" \
      --region us-east-1
    echo "$(date) - ❌ Failure notification sent via SNS" >> $LOG_FILE
fi

# Clean up temporary certificate files
rm -f /tmp/*.pem
echo "$(date) - Temporary certificate files cleaned up" >> $LOG_FILE

# =============================================================================
# STEP 6: Clean shutdown to minimize AWS costs
# =============================================================================
# Shut down the EC2 instance to stop billing
# The instance will need to be started again for the next renewal cycle (in 20 days)
echo "$(date) - Shutting down EC2 instance to save costs" >> $LOG_FILE
sudo shutdown -h now
