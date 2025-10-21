# Multi-Newsletter Setup

This codebase now supports multiple newsletters. Each newsletter is configured in `newsletters.json` and has its own URL slug.

## Configuration

Edit `newsletters.json` to add or modify newsletters:

```json
{
  "dctech": {
    "name": "DC Tech Events Weekly",
    "description": "Weekly newsletter about DC tech events",
    "from_email": "outbound@dctech.events",
    "reply_to_email": "ross@karchner.com",
    "contact_list_name": "newsletters",
    "topic_name": "dctech",
    "template_name": "dctech-newsletter",
    "content_url": "https://dctech.events/newsletter.html",
    "subject": "DC Tech Events Weekly",
    "schedule": "cron(0 11 ? * MON *)"
  },
  "another-newsletter": {
    "name": "Another Newsletter",
    "description": "Description of another newsletter",
    "from_email": "sender@example.com",
    "reply_to_email": "reply@example.com",
    "contact_list_name": "another-list",
    "topic_name": "another-topic",
    "template_name": "another-template",
    "content_url": "https://example.com/newsletter.html",
    "subject": "Another Newsletter",
    "schedule": "cron(0 9 ? * FRI *)"
  }
}
```

## CLI Management

Use the `manage_newsletters.py` script to set up newsletters in AWS SES:

```bash
# List all configured newsletters
python manage_newsletters.py list

# Set up a specific newsletter
python manage_newsletters.py setup --slug dctech

# Set up all newsletters
python manage_newsletters.py setup-all
```

## URL Structure

Each newsletter has its own URL slug:

- Newsletter signup: `/{slug}` (e.g., `/dctech`)
- Newsletter signup form submission: `/{slug}/signup`
- Confirmation page: `/{slug}/confirm/{encoded_email}/{encoded_timestamp}/{signature}`
- Confirmation form submission: `/{slug}/confirm`
- Success page: `/{slug}/confirm/success`

## Adding a New Newsletter

1. Add the newsletter configuration to `newsletters.json`
2. Run `python manage_newsletters.py setup --slug your-new-slug`
3. Deploy the application: `chalice deploy`

## Scheduled Sending

Each newsletter can have its own schedule. Update the `@app.schedule` decorators in `app.py` to match your newsletter schedules, or create separate scheduled functions for each newsletter.

## Templates

The following templates support newsletter-specific content:

- `index.html` - Newsletter signup page
- `confirmation_email.html` - Confirmation email
- `confirm.html` - Confirmation page
- `success.html` - Success page
- `newsletter_list.html` - Lists all available newsletters (root page)

All templates receive a `newsletter` variable with the newsletter configuration and a `newsletter_slug` variable with the URL slug.