# DC Tech Events Newsletter Service

This is an AWS Chalice application that manages newsletter subscriptions for DC Tech Events. It handles signup, confirmation, newsletter delivery, and unsubscribe functionality.

## Features

- Double opt-in subscription process with CSRF protection
- Automated weekly newsletter delivery (Mondays at 2am Eastern Time)
- Secure unsubscribe functionality
- HTML and plaintext email support

## Prerequisites

- Python 3.8+
- AWS Account with configured credentials
- AWS SES configured and verified domain/email addresses
- AWS Secrets Manager with a secret named 'newsletter/csrf_secret'

## Setup

1. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Create the CSRF secret in AWS Secrets Manager:
```bash
aws secretsmanager create-secret --name newsletter/csrf_secret --secret-string '{"csrf_secret":"your-secure-random-string"}'
```

3. Create the DynamoDB table:
```bash
python create_table.py
```

4. Deploy the application:
```bash
chalice deploy
```

## Testing

Run the tests with:
```bash
pytest tests/
```

## API Endpoints

- POST /signup - Submit email for subscription
- GET /confirm - Display confirmation page
- POST /confirm - Confirm subscription
- GET /unsubscribe - Display unsubscribe page
- POST /unsubscribe - Process unsubscribe request

## Environment Variables

- SUBSCRIBERS_TABLE - DynamoDB table name for subscribers
- API_HOST - API Gateway host for generating URLs

## Security

- CSRF protection for all state-changing operations
- Secrets stored in AWS Secrets Manager
- Double opt-in subscription process
- Secure unsubscribe links with expiring tokens