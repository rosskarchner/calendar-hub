# Implementation Plan: Flask-based Calendar Hub

## Overview
Consolidate two Chalice apps (add.dctech.events and dctech-newsletter) into a single Flask application with multi-site support, HTMX frontend, and deployment to Linux VPS/EC2.

## Phase 1: Project Setup & Architecture ✓
1. **Initialize Flask project structure**
   - Create unified Flask app in root directory
   - Set up virtual environment with Flask, boto3, PyGithub, wtforms, jinja2, htmx dependencies
   - Create modular blueprint structure for events and newsletters
   - Configure for EC2 deployment with systemd/gunicorn

2. **Multi-tenant site configuration**
   - Port `sites.json` concept from add.dctech.events
   - Create site model/config with: slug, name, github_repo, contact_list_name, from_email
   - Add site context middleware to inject site data into requests
   - Store configuration in JSON or environment variables

## Phase 2: Event Submission Module (from add.dctech.events)
3. **Event submission blueprint**
   - Convert Chalice routes to Flask blueprint with `/{site_slug}` prefix
   - Port WTForms validation (EventForm, EventSubmissionForm, MeetupGroupForm, ICalGroupForm)
   - Keep CSRF protection using Flask-WTF or existing custom implementation
   - Render HTMX-compatible HTML templates (form.html, meetup_form.html, ical_form.html)

4. **Event submission workflow**
   - POST handlers return HTML fragments for HTMX (not JSON)
   - DynamoDB integration for pending submissions (boto3)
   - SES email confirmation flow with signed URLs
   - Confirmation preview page with CSRF-protected confirm button

5. **GitHub PR creation**
   - Port GitHub PR creation logic using PyGithub
   - Create event YAML files in `_single_events/` directory
   - Create meetup group YAML files in `_groups/` directory
   - Handle iCal feed submissions similarly
   - Success page returns HTML with PR link

## Phase 3: Newsletter Module (from dctech-newsletter)
6. **Newsletter subscription blueprint**
   - Convert Chalice routes to Flask blueprint
   - Multi-newsletter support per site using SES contact lists and topics
   - HTMX signup form returning HTML fragments
   - KMS-signed confirmation URLs for email verification

7. **Newsletter management endpoints**
   - Signup form with CSRF protection
   - Email confirmation handler with KMS signature verification
   - Unsubscribe endpoint with signed tokens
   - Management page for viewing subscription status (optional)

## Phase 4: Shared Infrastructure
8. **Shared services layer**
   - AWS service clients (DynamoDB, SES/SESv2, KMS, Secrets Manager, GitHub)
   - Use EC2 IAM role for authentication (no hardcoded credentials)
   - Secrets Manager for CSRF secrets, GitHub tokens, KMS key IDs
   - Error handling and logging

9. **Template system**
   - Jinja2 templates with HTMX attributes
   - Shared layout with site branding
   - Partials for forms, errors, success messages
   - HTMX response headers (HX-Trigger, HX-Retarget, etc.)

## Phase 5: Deployment Configuration
10. **EC2 deployment setup**
    - gunicorn/uWSGI WSGI server configuration
    - systemd service file for auto-start
    - nginx reverse proxy configuration (optional but recommended)
    - Environment variable management
    - Logging to CloudWatch (optional) or local files

11. **IAM role requirements**
    - DynamoDB read/write access to submissions table
    - SES send email permissions
    - SESv2 contact list management
    - KMS GenerateMac and VerifyMac permissions
    - Secrets Manager read access
    - GitHub personal access token stored in Secrets Manager

## Phase 6: Testing & Migration
12. **Testing**
    - Port existing tests from both apps
    - Integration tests for multi-site functionality
    - Test HTMX interactions
    - Validate email flows

13. **Documentation**
    - Deployment guide for Linux VPS/EC2
    - Site configuration documentation
    - Environment variables reference
    - Migration notes from Chalice

## Key Technical Decisions
- **Flask blueprints** for modular organization (events, newsletters)
- **HTMX** for all frontend interactions, no JavaScript frameworks
- **Server-side rendering** with Jinja2, returning HTML fragments
- **No database layer** beyond existing AWS services (DynamoDB, SES, GitHub)
- **IAM role-based** AWS authentication for EC2
- **Site-agnostic code** with configuration-driven multi-tenancy

## File Structure
```
calendar-hub/
├── app.py              # Main Flask app
├── config.py           # Configuration management
├── sites.json          # Multi-site configuration
├── blueprints/
│   ├── __init__.py
│   ├── events/         # Event submission module
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── forms.py
│   └── newsletters/    # Newsletter module
│       ├── __init__.py
│       ├── routes.py
│       └── forms.py
├── services/           # AWS service wrappers
│   ├── __init__.py
│   ├── aws_clients.py
│   ├── dynamodb.py
│   ├── ses.py
│   └── github_service.py
├── templates/          # Jinja2 templates
│   ├── base.html
│   ├── events/
│   └── newsletters/
├── static/             # CSS, HTMX library
│   ├── css/
│   └── js/
├── utils/              # Shared utilities
│   ├── __init__.py
│   ├── csrf.py
│   └── validators.py
├── requirements.txt    # Python dependencies
├── wsgi.py            # WSGI entry point
└── deployment/         # systemd, nginx configs
    ├── calendar-hub.service
    └── nginx.conf.example
```

## Progress Tracking
- [x] Phase 1: Project Setup & Architecture ✅ COMPLETE
  - ✅ Created Flask project structure with blueprints
  - ✅ Set up virtual environment with latest dependencies
  - ✅ Created multi-tenant site configuration (sites.json)
  - ✅ Implemented configuration management (config.py)
  - ✅ Created main Flask app with middleware (app.py)
  - ✅ Set up WSGI entry point for production (wsgi.py)
  - ✅ Created deployment configs (systemd, nginx)
  - ✅ Created AWS clients wrapper (services/aws_clients.py)
  - ✅ All basic routes tested and working
- [x] Phase 2: Event Submission Module ✅ COMPLETE
  - ✅ Created WTForms for event validation (EventForm, EventSubmissionForm, etc.)
  - ✅ Ported CSRF protection utilities
  - ✅ Created DynamoDB service for submissions
  - ✅ Created SES service for confirmation emails
  - ✅ Created GitHub service for PR creation
  - ✅ Implemented all event submission routes (events, meetups, iCal)
  - ✅ Ported HTML templates from Chalice app
  - ✅ Implemented confirmation workflow
  - ✅ All routes tested and functional
- [x] Phase 3: Newsletter Module ✅ COMPLETE
  - ✅ Created NewsletterSignupForm for validation
  - ✅ Created KMS service for signature generation/verification
  - ✅ Created SESv2 service for newsletter management
  - ✅ Implemented newsletter signup with HTMX support
  - ✅ Implemented email confirmation with KMS signatures
  - ✅ Implemented unsubscribe functionality
  - ✅ Ported all newsletter templates
  - ✅ Downloaded HTMX library to static files
  - ✅ All routes tested and functional
- [x] Phase 4: Shared Infrastructure ✅ COMPLETE
  - ✅ Created base template with navigation
  - ✅ Added comprehensive CSS styling (main.css)
  - ✅ Implemented error handlers (404, 500, 403, 400)
  - ✅ Added error templates
  - ✅ Configured logging (rotating file handlers)
  - ✅ Added health check endpoint
  - ✅ Created comprehensive deployment guide (DEPLOYMENT.md)
  - ✅ Created API documentation (API.md)
  - ✅ Created development helper script (dev.sh)
  - ✅ All infrastructure tested and working
- [ ] Phase 5: Deployment Configuration
- [ ] Phase 6: Testing & Migration
