# Calendar Hub - Architecture Overview

## 1. AWS RESOURCES CURRENTLY BEING USED

### DynamoDB
- **Table**: `DCTechEventsSubmissions`
- **Primary Key**: `submission_id` (String)
- **Purpose**: Store event/newsletter submission data before confirmation
- **Data Stored**:
  - `submission_id`: UUID for tracking
  - `status`: 'pending' or 'confirmed'
  - `type`: submission type (event, newsletter, etc.)
  - `site_slug`: which site the submission is for
  - `email`: submitter's email address
  - `data`: JSON object containing submission details
  - `created_at`: ISO timestamp
  - `confirmation_sent`: boolean flag
  - `pr_url`: GitHub PR URL (set after confirmation)
- **Billing**: PAY_PER_REQUEST (serverless)
- **Recovery**: Point-in-time recovery enabled

### SES (Simple Email Service)
- **Purpose**: Send confirmation emails to event submitters
- **Service**: AWS SES (SendEmail)
- **Configuration**:
  - Sender email configurable per site
  - Default: `outgoing@dctech.events`
  - Verified email identity required

### SESv2 (Simple Email Service v2)
- **Purpose**: Newsletter contact management and bulk email sending
- **Features**:
  - Contact lists for organizing subscribers
  - Topic-based subscriptions (opt-in/opt-out management)
  - HTML email support
  - Contact list: `newsletters`
  - Topics: `dctech` (one per site)
- **Operations**:
  - `create_contact`: Subscribe new email
  - `get_contact`: Check subscription status
  - `update_contact`: Update topic preferences
  - `delete_contact`: Remove contact

### KMS (Key Management Service)
- **Purpose**: Generate and verify HMAC signatures for newsletter confirmation links
- **Key Type**: HMAC_256
- **Key Usage**: GENERATE_VERIFY_MAC
- **Purpose of Signatures**: 
  - Create tamper-proof confirmation URLs
  - No database lookup needed to verify links
  - 6-hour expiry enforced by timestamp validation
- **Message Format**: `{email}:{contact_list_name}:{topic_name}:{timestamp}`

### Secrets Manager
- **Purpose**: Store sensitive credentials securely
- **Secrets Stored**:
  1. `dctech-events/csrf-secret` - CSRF token secret
  2. `dctech-events/github-token` - GitHub personal access token
  3. `newsletter/csrf_secret` - Newsletter CSRF secret
- **Access**: EC2 IAM role retrieves at runtime
- **No hardcoded credentials** in code

### S3 (Not currently used)
- Mentioned in refactor branch name but not implemented
- Could be used for file uploads in future

## 2. AUTHENTICATION SYSTEM & MAGIC LINK IMPLEMENTATION

### Magic Link Overview
The application uses **email-based magic links** (not traditional passwords) for both event submissions and newsletter confirmations.

### Event Submission Magic Link Flow
1. **User submits form** → `/[site_slug]/submit` (POST)
   - Email validation via WTForms
   - CSRF token validation (HMAC-based)
   - Data stored in DynamoDB as `status: 'pending'`
   - Submission ID: UUID (v4)

2. **Confirmation email sent** via SES
   - Contains magic link: `https://domain/[site_slug]/confirm/[submission_id]`
   - No token in URL - link itself is the token
   - Link is valid indefinitely until confirmed

3. **User clicks link** → `/[site_slug]/confirm/[submission_id]` (GET)
   - Display preview page with submission details
   - Generate CSRF token for the confirmation form
   - Validate submission exists and is pending

4. **User confirms** → `/[site_slug]/confirm/[submission_id]/submit` (POST)
   - CSRF token validation
   - Create GitHub PR with submission data
   - Update DynamoDB: `status: 'confirmed'`, store `pr_url`
   - Show success page with PR link

**Security**:
- Submission ID is unique UUID (not sequential/guessable)
- CSRF protection on both form steps
- Email ownership verified (user must receive email)
- Status check prevents double-confirmation

### Newsletter Confirmation Magic Link Flow
1. **User signs up** → `/[site_slug]/newsletter/signup` (POST)
   - Email validation
   - CSRF token validation
   - NO data stored in database (stateless)

2. **Signed confirmation URL generated** via KMS HMAC
   - Components: `encoded_email:encoded_timestamp:kms_signature`
   - Link: `/[site_slug]/newsletter/confirm/{encoded_email}/{encoded_timestamp}/{signature}`
   - Signature proves email without database lookup

3. **User clicks link** → `/[site_slug]/newsletter/confirm/[...]/[...]?/[...]` (GET)
   - Verify KMS signature (proves this email was requested)
   - Check timestamp (fail if > 6 hours old)
   - Display final confirmation page

4. **User confirms** → `/[site_slug]/newsletter/confirm` (POST)
   - Verify signature again
   - Add email to SES contact list with topic subscription
   - Redirect to success page

**Security**:
- KMS signatures cannot be forged (requires AWS credentials)
- Timestamp validation prevents replay attacks
- No database needed for validation (stateless, scalable)
- Email is encoded in signature itself

### CSRF Protection System
**Location**: `/utils/csrf.py`

- **Token Format**: `{random_token}:{expiry_timestamp}:{hmac_signature}`
- **Algorithm**: HMAC-SHA256
- **Expiry**: 1 hour (configurable)
- **Secret Source**:
  - Development: from `config.SECRET_KEY`
  - Production: from Secrets Manager
- **Validation**: 
  - Signature verification
  - Timestamp expiry check
  - Constant-time comparison (timing attack protection)

## 3. TEMPORARY DATA STORAGE

### DynamoDB (Semi-permanent)
- Event/newsletter submissions awaiting confirmation
- Stored until user confirms (indefinite duration)
- Archived in the repo after PR is merged

### Session-like Data
- **No sessions/cookies**: Application is stateless
- **CSRF tokens**: Generated fresh for each page load
  - Not stored anywhere
  - Validated via HMAC on submission
- **User data**: Only stored if explicitly submitted

### Email Queue
- SES handles email delivery asynchronously
- No retry queue (relies on SES reliability)
- Confirmation emails sent immediately

### Temporary States
- Newsletter signup creates NO temp data
- Event submission stored in DynamoDB until confirmed
- After confirmation: PR created on GitHub, status updated in DynamoDB

## 4. APPLICATION STRUCTURE & ENTRY POINTS

### Architecture Pattern: Flask Blueprints + Modular Services

```
calendar-hub/
├── app.py                    # Flask factory pattern, app setup
├── wsgi.py                   # WSGI entry for gunicorn/production
├── config.py                 # Configuration management
├── sites.json                # Multi-site configuration
├── blueprints/               # Feature modules
│   ├── events/
│   │   ├── __init__.py      # Blueprint registration
│   │   ├── routes.py        # Event endpoints
│   │   └── forms.py         # WTForms validation
│   └── newsletters/
│       ├── __init__.py
│       ├── routes.py
│       └── forms.py
├── services/                 # AWS service wrappers
│   ├── aws_clients.py       # Singleton AWS client instances
│   ├── dynamodb.py          # DynamoDB operations (SubmissionsService)
│   ├── ses.py               # SES email (EmailService)
│   ├── sesv2.py             # SESv2 newsletters (NewsletterService)
│   ├── kms.py               # KMS HMAC (KMSService)
│   └── github_service.py    # GitHub PR creation
├── templates/               # Jinja2 templates
│   ├── base.html           # Master template with Bootstrap
│   ├── site_index.html     # Landing page
│   ├── events/             # Event submission templates
│   │   ├── form.html
│   │   ├── confirm.html
│   │   └── success.html
│   ├── newsletters/        # Newsletter templates
│   │   ├── index.html
│   │   ├── confirm.html
│   │   ├── success.html
│   │   ├── partials/       # HTMX fragments
│   │   └── confirmation_email.html
│   └── errors/             # Error pages (404, 500, etc.)
├── static/                 # Frontend assets
│   ├── css/main.css
│   └── js/htmx.min.js      # HTMX library (local)
├── utils/                  # Shared utilities
│   ├── csrf.py            # CSRF token generation/validation
│   ├── validators.py      # Input validation helpers
│   └── error_handlers.py  # Flask error handlers & logging
└── requirements.txt        # Python dependencies
```

### Entry Points

1. **Development**: `python app.py` or `python wsgi.py`
2. **Production**: `gunicorn wsgi:app` (via EC2 systemd service)
3. **WSGI**: `wsgi.py` exports `app` object for ASGI servers

### Request Flow Example

```
GET /dctech
├── Flask routes to events_bp.site_index('dctech')
├── Load site config: config.get_site_by_slug('dctech')
├── Inject into g.site context
├── Render site_index.html with site data
└── Response: HTML with Newsletter & Submit buttons

POST /dctech/submit (event submission)
├── Validate CSRF token
├── Validate form via WTForms
├── Create submission_id (UUID)
├── Store in DynamoDB: pending status
├── Send email via SES with confirmation URL
└── Response: "Check your email" message

GET /dctech/confirm/{submission_id}
├── Load submission from DynamoDB
├── Verify pending status
├── Generate CSRF token
├── Render preview page
└── Response: HTML form asking to confirm

POST /dctech/confirm/{submission_id}/submit
├── Validate CSRF token
├── Load submission again
├── Initialize GitHub service
├── Create PR with event YAML files
├── Update submission: status=confirmed, pr_url=...
└── Response: Success page with PR link

GET /dctech/newsletter/signup
├── Generate CSRF token
├── Render signup form
└── Response: HTML form or HTMX fragment

POST /dctech/newsletter/signup
├── Validate email
├── Generate KMS-signed confirmation URL
├── Render HTML email template
├── Send via SESv2
└── Response: "Check your email" message
```

## 5. CONFIGURATION FILES

### `.env.example`
Environment variables used by the application:
```
FLASK_ENV=production          # Flask environment
SECRET_KEY=...                # Flask session secret
SUBMISSIONS_TABLE=...         # DynamoDB table name
SENDER_EMAIL=...              # SES sender email
CSRF_SECRET_NAME=...          # Secrets Manager secret
GITHUB_TOKEN_SECRET_NAME=...
NEWSLETTER_CSRF_SECRET_NAME=...
CONFIRMATION_KEY_ID=...       # KMS key ID
DOMAIN_NAME=...               # Application domain
```

### `config.py`
Flask configuration class-based system:
- **DevelopmentConfig**: DEBUG=True, uses dev secrets
- **ProductionConfig**: DEBUG=False, uses Secrets Manager
- **Config.SITES_CONFIG_PATH**: Points to sites.json

### `sites.json`
Multi-tenant configuration:
```json
{
  "sites": [
    {
      "slug": "dctech",
      "name": "DC Tech Events",
      "url": "https://dctech.events",
      "github_repo": "https://github.com/rosskarchner/dctech.events",
      "contact_list_name": "newsletters",
      "topic_name": "dctech",
      "from_email": "outbound@dctech.events",
      "reply_to_email": "ross@karchner.com"
    }
  ]
}
```

### `cloudformation-prerequisites.yaml`
Infrastructure-as-Code template defining all AWS resources:
- DynamoDB table
- KMS key for HMAC
- Secrets Manager secrets
- SES email identity & contact list
- IAM role for EC2 with permissions
- Instance profile for EC2 instances

### `cloudformation-parameters.json`
CloudFormation input parameters (domain, email, secrets)

## 6. DEPENDENCIES IN requirements.txt

```
Flask==3.1.2                    # Web framework
boto3==1.40.55                 # AWS SDK
PyGithub==2.6.0               # GitHub API
WTForms==3.2.1                # Form validation
Jinja2==3.1.5                 # Template engine
PyYAML==6.0.2                 # YAML processing (for GitHub PR content)
gunicorn==23.0.0              # WSGI HTTP server
python-dotenv==1.0.1          # Load .env files
email-validator==2.2.0        # Email validation
```

### Key Dependency Roles
- **Flask**: Web framework, routing, context management
- **boto3**: AWS SDK for DynamoDB, SES, KMS, Secrets Manager
- **PyGithub**: Create pull requests on GitHub
- **WTForms**: Server-side form validation (not used for CSRF, custom impl)
- **Jinja2**: HTML template rendering
- **PyYAML**: Convert event data to YAML for GitHub PR
- **gunicorn**: Production WSGI application server
- **python-dotenv**: Load environment variables from .env in development
- **email-validator**: Validate email addresses before SES submission

### Frontend (No Heavy JS Framework)
- **Bootstrap 5**: CSS framework (via CDN)
- **HTMX**: Dynamic HTML without JavaScript (local copy)
- **htmx.min.js**: Enables AJAX form submissions returning HTML fragments

## DEPLOYMENT APPROACH

### Current Deployment
- **Target**: EC2 Linux instance (Ubuntu 20.04+)
- **Server**: gunicorn + systemd service
- **Reverse Proxy**: nginx (recommended)
- **Database**: AWS DynamoDB (managed)
- **Email**: AWS SES/SESv2 (managed)
- **Authentication**: IAM role (no hardcoded AWS credentials)

### AWS IAM Permissions Required
EC2 instance needs IAM role with:
- DynamoDB: PutItem, GetItem, UpdateItem, Query, Scan
- SES: SendEmail, SendRawEmail
- SESv2: SendEmail, CreateContact, GetContact, UpdateContact, DeleteContact
- KMS: GenerateMac, VerifyMac, DescribeKey
- Secrets Manager: GetSecretValue

## CURRENT PROJECT STATUS

Based on git history:
- **Phase 1-4: COMPLETE** (✅ Setup, Events, Newsletters, Infrastructure)
- **Phase 5-6: NOT STARTED** (Deployment config, Testing)

Recent commits:
- `a6678f9`: "Try again" 
- `3993bf7`: "First crack at building the hub"
- `b7587eb`: "Initial commit"

Current branch: `claude/refactor-remove-aws-docker-011CUpsLbRBc8zFTeTZbVAHN`

## KEY DESIGN PATTERNS

1. **Singleton AWS Clients**: `AWSClients` class caches boto3 connections
2. **Service Classes**: Business logic separated from routes
3. **Blueprint Pattern**: Modular Flask blueprints for events & newsletters
4. **Factory Pattern**: `create_app()` factory for testing
5. **Configuration Objects**: Class-based config with environment-aware secrets
6. **HMAC-based Tokens**: No database needed for CSRF or newsletter links
7. **Stateless Design**: No sessions, all state either in URL or DynamoDB
8. **Server-Side Rendering**: Jinja2 templates, HTMX for interactivity

## WHAT NEEDS REFACTORING

Based on the branch name "refactor-remove-aws-docker", the refactoring effort should address:

1. **Remove Docker dependency** - Currently uses Docker for local development
2. **Remove unnecessary AWS abstractions** - Simplify boto3 usage
3. **Reduce AWS service complexity** - Streamline KMS/SES configuration
4. **Improve local development** - Make dev environment not require AWS
5. **Simplify deployment** - Remove Docker from deployment pipeline
