# Calendar Hub - Quick Reference Guide

## AWS Resources at a Glance

| Service | Purpose | Config | Key Operations |
|---------|---------|--------|-----------------|
| **DynamoDB** | Store submissions awaiting confirmation | Table: `DCTechEventsSubmissions` | PutItem, GetItem, UpdateItem |
| **SES** | Send event confirmation emails | Email: `outgoing@dctech.events` | SendEmail |
| **SESv2** | Manage newsletter subscriptions | Contact List: `newsletters` | CreateContact, GetContact, UpdateContact |
| **KMS** | Generate HMAC signatures for links | Key: `HMAC_256` | GenerateMac, VerifyMac |
| **Secrets Manager** | Store sensitive credentials | 3 secrets (CSRF, GitHub token, Newsletter CSRF) | GetSecretValue |

## Magic Link Security Model

### Event Submission (Database-backed)
```
User → Email Submitted → UUID stored in DynamoDB → Email sent → User clicks link (UUID in URL) → 
DynamoDB lookup → Confirmation form (CSRF protected) → GitHub PR created
```
**Key**: UUID is unique, unguessable; status prevents replay

### Newsletter (Stateless, KMS-signed)
```
User → Email Submitted → KMS-signed URL generated (no DB) → Email sent → 
User clicks link → KMS verification → Confirmation form → SES contact list updated
```
**Key**: No database needed for validation; KMS signature proves legitimacy

## File Locations for Key Features

### Magic Link Routes
- **Event confirmation**: `/blueprints/events/routes.py` (lines 118-198)
  - Preview: `preview_confirmation()` function
  - Confirm: `confirm_submission()` function
- **Newsletter confirmation**: `/blueprints/newsletters/routes.py` (lines 125-232)
  - Preview: `confirm_preview()` function
  - Confirm: `confirm_subscription()` function
  - Unsubscribe: `unsubscribe()` function

### Authentication/Security
- **CSRF implementation**: `/utils/csrf.py` - HMAC-based tokens
- **Email validation**: `/blueprints/events/forms.py` and `/blueprints/newsletters/forms.py`
- **KMS signatures**: `/services/kms.py` - HMAC_256 generation/verification

### AWS Integration
- **Client factory**: `/services/aws_clients.py` - Singleton pattern
- **DynamoDB**: `/services/dynamodb.py` - SubmissionsService class
- **Email (SES)**: `/services/ses.py` - EmailService class
- **Email (SESv2)**: `/services/sesv2.py` - NewsletterService class
- **GitHub**: `/services/github_service.py` - GitHubService class

### Configuration
- **Environment variables**: `.env` (copy from `.env.example`)
- **Site configuration**: `sites.json` - Multi-tenant setup
- **Flask config**: `config.py` - DevelopmentConfig vs ProductionConfig
- **CloudFormation**: `cloudformation-prerequisites.yaml` - AWS infrastructure as code

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     EC2 Linux Instance                    │
│  ┌───────────────────────────────────────────────────┐  │
│  │  nginx (reverse proxy, static files)              │  │
│  └─────────────────┬─────────────────────────────────┘  │
│                    │                                     │
│  ┌─────────────────▼─────────────────────────────────┐  │
│  │  gunicorn (WSGI app server)                       │  │
│  │  - Flask app instance                             │  │
│  │  - Multiple worker processes                      │  │
│  └─────────────────┬─────────────────────────────────┘  │
│                    │                                     │
│  ┌─────────────────▼─────────────────────────────────┐  │
│  │  Python Application (Flask + Blueprints)         │  │
│  │  - /app.py (factory)                              │  │
│  │  - /blueprints/events                             │  │
│  │  - /blueprints/newsletters                        │  │
│  │  - /services (AWS wrappers)                       │  │
│  └─────────────────┬─────────────────────────────────┘  │
│                    │                                     │
│  ┌─────────────────▼─────────────────────────────────┐  │
│  │  boto3 SDK (AWS credentials via IAM role)        │  │
│  └─────────────────┬─────────────────────────────────┘  │
└────────────────────┼────────────────────────────────────┘
                     │
        ┌────────────┴────────────┬──────────────┐
        ▼                         ▼              ▼
    DynamoDB              SES/SESv2           GitHub
    (submissions)         (emails)         (PRs with
    (stateless for        (newsletters)    event data)
     newsletter)          KMS (HMAC)
                          Secrets Manager
                          (credentials)
```

## Common Development Tasks

### Add a New AWS Service
1. Add method to `AWSClients` class in `/services/aws_clients.py`
2. Create new service file (e.g., `/services/my_service.py`)
3. Import and use in blueprints

### Add a New Form Field
1. Update `/blueprints/events/forms.py` or `/blueprints/newsletters/forms.py`
2. Add validation rules
3. Update template in `/templates/`
4. Update route handler to validate/process

### Add a New Site
1. Add entry to `sites.json`
2. Set up AWS resources (SES identity, SESv2 contact list, etc.)
3. Store credentials in Secrets Manager
4. Create template variations if needed (optional)

### Debug Newsletter Signatures
- KMS signature format in URL: `/confirm/{encoded_email}/{encoded_timestamp}/{signature}`
- Verification checks:
  1. KMS HMAC validation (requires AWS credentials)
  2. Timestamp < 6 hours old
  3. Base64 URL-safe encoding (with padding removed)

### Debug Event Submissions
- Submission lifecycle in DynamoDB:
  1. Created with `status: 'pending'`
  2. After user confirms: `status: 'confirmed'`, `pr_url` added
- Check logs: `logs/calendar-hub.log` and `logs/calendar-hub-errors.log`

## Environment Variables Checklist

```bash
# Development Setup
FLASK_ENV=development
SECRET_KEY=dev-secret-key-change-in-production
SUBMISSIONS_TABLE=DCTechEventsSubmissions
SENDER_EMAIL=outgoing@dctech.events
DOMAIN_NAME=localhost:5000

# AWS Resources (from CloudFormation output)
CONFIRMATION_KEY_ID=arn:aws:kms:...  # From CloudFormation
CSRF_SECRET_NAME=dctech-events/csrf-secret
GITHUB_TOKEN_SECRET_NAME=dctech-events/github-token
NEWSLETTER_CSRF_SECRET_NAME=newsletter/csrf_secret
```

## Testing Magic Links Locally

### Event Submission
```bash
1. POST to /dctech/submit with valid form
2. Check DynamoDB table for pending submission
3. Get submission_id from DB
4. Visit /dctech/confirm/{submission_id}
5. Click submit (needs real GitHub token)
```

### Newsletter
```bash
1. POST to /dctech/newsletter/signup with email
2. Check SES logs for sent email
3. Extract KMS signature from logs
4. Visit /dctech/newsletter/confirm/{encoded_email}/{encoded_timestamp}/{signature}
5. Click submit (adds to SES contact list)
```

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| "Invalid CSRF token" | Token expired (1 hour) or secret mismatch | Regenerate fresh token on page load |
| "Secret not found" in Secrets Manager | IAM role lacks permissions | Add GetSecretValue permission to IAM role |
| "KMS verification failed" | Timestamp > 6 hours or corrupted signature | Check system clock; regenerate link |
| "GitHub PR creation failed" | Invalid token or insufficient permissions | Check GitHub token in Secrets Manager |
| Email not sent | SES domain not verified | Verify email in SES console |
| "Submission not found" | Typo in submission_id or different table | Check DynamoDB table name in config |

## Performance Considerations

- **DynamoDB**: PAY_PER_REQUEST billing (no provisioned capacity)
  - Suitable for low-volume submissions
  - No cold starts unlike Lambda
  
- **SES**: Email sending is asynchronous
  - Confirmation emails sent immediately after submission
  - No guaranteed delivery order

- **KMS HMAC**: Slower than local HMAC
  - Used only for newsletter links (not CSRF)
  - Alternative: Use local HMAC for links if AWS cost is concern

- **Gunicorn workers**: Default 4 workers
  - Tune with `--workers` flag based on CPU cores
  - Use `--worker-class=sync` for CPU-bound tasks

## Code Style & Conventions

- **Service classes**: Static methods for stateless operations
- **Error handling**: Try/except with logging, return JSON or HTML as needed
- **CSRF tokens**: Always generate before rendering form
- **Environment variables**: Retrieved once at app startup when possible
- **Templates**: Use Jinja2 extends/includes, Bootstrap classes

