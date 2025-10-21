# Calendar Hub

A unified Flask application for managing event submissions and newsletter subscriptions across multiple sites.

## Overview

Calendar Hub consolidates two previously separate Chalice applications into a single Flask-based platform:
- **Event Submission Tool**: Allows users to submit events, meetup groups, and iCal feeds via web forms
- **Newsletter Management**: Handles newsletter subscriptions with double opt-in confirmation

## Features

- **Multi-site Support**: Configure multiple sites from a single application
- **HTMX-Powered UI**: Modern, dynamic user interface without heavy JavaScript frameworks
- **AWS Integration**: Uses DynamoDB, SES/SESv2, KMS, and Secrets Manager
- **GitHub Integration**: Automatically creates pull requests for event submissions
- **IAM Role-Based Auth**: Designed for EC2 deployment with instance profiles

## Project Structure

```
calendar-hub/
├── app.py                  # Main Flask application
├── config.py               # Configuration management
├── wsgi.py                 # WSGI entry point
├── sites.json              # Multi-site configuration
├── requirements.txt        # Python dependencies
├── blueprints/             # Flask blueprints
│   ├── events/             # Event submission module
│   └── newsletters/        # Newsletter module
├── services/               # AWS service wrappers
├── templates/              # Jinja2 templates
├── static/                 # Static assets (CSS, JS)
├── utils/                  # Shared utilities
└── deployment/             # Deployment configs (systemd, nginx)
```

## Installation

### Development Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and configure
5. Run the development server:
   ```bash
   python app.py
   ```

### Production Deployment (EC2)

1. Install the application to `/opt/calendar-hub`
2. Create virtual environment and install dependencies
3. Configure environment variables
4. Copy systemd service file:
   ```bash
   sudo cp deployment/calendar-hub.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable calendar-hub
   sudo systemctl start calendar-hub
   ```
5. Configure nginx (optional but recommended):
   ```bash
   sudo cp deployment/nginx.conf.example /etc/nginx/sites-available/calendar-hub
   # Edit the file with your domain
   sudo ln -s /etc/nginx/sites-available/calendar-hub /etc/nginx/sites-enabled/
   sudo systemctl reload nginx
   ```

## Configuration

### Sites Configuration

Edit `sites.json` to configure multiple sites:

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

### Environment Variables

See `.env.example` for required environment variables.

### IAM Permissions

The EC2 instance role requires:
- DynamoDB: Read/Write on submissions table
- SES: Send email permissions
- SESv2: Contact list management
- KMS: GenerateMac and VerifyMac permissions
- Secrets Manager: Read access to secrets

## Development Status

- [x] Phase 1: Project Setup & Architecture
- [ ] Phase 2: Event Submission Module
- [ ] Phase 3: Newsletter Module
- [ ] Phase 4: Shared Infrastructure
- [ ] Phase 5: Deployment Configuration
- [ ] Phase 6: Testing & Migration

## Migration from Chalice

The original Chalice applications are preserved in:
- `add.dctech.events/` - Event submission tool
- `dctech-newsletter/` - Newsletter management

These will remain until the Flask migration is complete and tested.

## License

[Your License Here]
