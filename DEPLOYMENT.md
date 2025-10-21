# Deployment Guide for Calendar Hub

## Prerequisites

- Linux server (Ubuntu 20.04+ or similar)
- Python 3.9+
- nginx (optional but recommended)
- AWS account with configured services
- Domain name pointed to your server

## AWS Setup

### 1. Create DynamoDB Table

```bash
aws dynamodb create-table \
    --table-name DCTechEventsSubmissions \
    --attribute-definitions \
        AttributeName=submission_id,AttributeType=S \
    --key-schema \
        AttributeName=submission_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST
```

### 2. Configure SES/SESv2

Set up verified email addresses and create contact lists for newsletters:

```bash
# Verify sender email
aws sesv2 create-email-identity --email-identity outbound@yourdomain.com

# Create contact list for newsletters
aws sesv2 create-contact-list \
    --contact-list-name newsletters \
    --topics TopicName=dctech,SubscriptionStatus=OPT_IN
```

### 3. Create KMS Key for Newsletter Confirmations

```bash
aws kms create-key \
    --description "Calendar Hub Newsletter Confirmation Key" \
    --key-usage GENERATE_VERIFY_MAC

# Save the KeyId from the output
```

### 4. Store Secrets in Secrets Manager

```bash
# CSRF secret for events
aws secretsmanager create-secret \
    --name dctech-events/csrf-secret \
    --secret-string "your-random-secret-key-here"

# GitHub token
aws secretsmanager create-secret \
    --name dctech-events/github-token \
    --secret-string "ghp_your_github_personal_access_token"

# Newsletter CSRF secret
aws secretsmanager create-secret \
    --name newsletter/csrf_secret \
    --secret-string '{"csrf_secret":"your-random-secret-key-here"}'
```

### 5. Create IAM Role for EC2

Create an IAM role with the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/DCTechEventsSubmissions"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ses:SendEmail",
        "sesv2:SendEmail",
        "sesv2:CreateContact",
        "sesv2:GetContact",
        "sesv2:UpdateContact"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:GenerateMac",
        "kms:VerifyMac"
      ],
      "Resource": "arn:aws:kms:*:*:key/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:*:*:secret:dctech-events/*",
        "arn:aws:secretsmanager:*:*:secret:newsletter/*"
      ]
    }
  ]
}
```

## Server Installation

### 1. Install System Dependencies

```bash
sudo apt update
sudo apt install -y python3.9 python3.9-venv python3-pip nginx git
```

### 2. Create Application User

```bash
sudo useradd -m -s /bin/bash calendar-hub
sudo mkdir -p /opt/calendar-hub
sudo chown calendar-hub:calendar-hub /opt/calendar-hub
```

### 3. Clone and Setup Application

```bash
sudo su - calendar-hub
cd /opt/calendar-hub

# Clone your repository
git clone https://github.com/yourusername/calendar-hub.git .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create `/opt/calendar-hub/.env`:

```bash
FLASK_ENV=production
SECRET_KEY=your-flask-secret-key-here
SUBMISSIONS_TABLE=DCTechEventsSubmissions
SENDER_EMAIL=outbound@yourdomain.com
CSRF_SECRET_NAME=dctech-events/csrf-secret
GITHUB_TOKEN_SECRET_NAME=dctech-events/github-token
NEWSLETTER_CSRF_SECRET_NAME=newsletter/csrf_secret
CONFIRMATION_KEY_ID=your-kms-key-id-here
DOMAIN_NAME=yourdomain.com
```

### 5. Setup systemd Service

Copy the service file:

```bash
sudo cp /opt/calendar-hub/deployment/calendar-hub.service /etc/systemd/system/
```

Edit if needed, then enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable calendar-hub
sudo systemctl start calendar-hub
sudo systemctl status calendar-hub
```

### 6. Configure nginx (Optional)

```bash
sudo cp /opt/calendar-hub/deployment/nginx.conf.example /etc/nginx/sites-available/calendar-hub

# Edit with your domain name
sudo nano /etc/nginx/sites-available/calendar-hub

# Enable site
sudo ln -s /etc/nginx/sites-available/calendar-hub /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7. Setup SSL with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

## Verify Deployment

### Check Application Status

```bash
sudo systemctl status calendar-hub
sudo journalctl -u calendar-hub -f
```

### Test Endpoints

```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy","version":"1.0.0"}

curl http://localhost:8000/
# Should redirect to /dctech
```

### Check Logs

```bash
tail -f /var/log/calendar-hub/access.log
tail -f /var/log/calendar-hub/error.log
tail -f /opt/calendar-hub/logs/calendar-hub.log
```

## Monitoring and Maintenance

### Log Rotation

Logs are automatically rotated by the RotatingFileHandler (10MB max, 10 backups).

### Update Application

```bash
sudo su - calendar-hub
cd /opt/calendar-hub
git pull
source venv/bin/activate
pip install -r requirements.txt
exit

sudo systemctl restart calendar-hub
```

### Backup DynamoDB

```bash
aws dynamodb create-backup \
    --table-name DCTechEventsSubmissions \
    --backup-name calendar-hub-$(date +%Y%m%d)
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u calendar-hub -n 50

# Check permissions
sudo ls -la /opt/calendar-hub
sudo ls -la /var/log/calendar-hub

# Test gunicorn manually
cd /opt/calendar-hub
source venv/bin/activate
gunicorn --bind 127.0.0.1:8000 wsgi:app
```

### AWS Permission Issues

```bash
# Verify IAM role is attached to EC2 instance
aws sts get-caller-identity

# Test AWS access
python3 -c "import boto3; print(boto3.client('dynamodb').list_tables())"
```

### Database Connection Issues

```bash
# Test DynamoDB access
aws dynamodb describe-table --table-name DCTechEventsSubmissions
```

## Security Best Practices

1. Keep all dependencies updated
2. Use strong secret keys
3. Enable CloudWatch logging for production
4. Regular security audits with `safety check`
5. Monitor failed login attempts
6. Keep SSL certificates current
7. Restrict SSH access to specific IPs
8. Regular backups of DynamoDB tables

## Support

For issues, check:
- Application logs: `/opt/calendar-hub/logs/`
- System logs: `sudo journalctl -u calendar-hub`
- nginx logs: `/var/log/nginx/`
