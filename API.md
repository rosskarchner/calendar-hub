# API Documentation

## Overview

Calendar Hub provides a REST API for event submissions and newsletter management. All endpoints support both traditional form submissions and HTMX-based partial rendering.

## Base URL

```
Production: https://yourdomain.com
Development: http://localhost:5000
```

## Authentication

Most endpoints are public. CSRF protection is implemented on all POST requests.

## Response Formats

The API returns either:
- **HTML**: For browser requests and HTMX partials
- **JSON**: For API requests with `Content-Type: application/json`

## Common Headers

### Request Headers
```
Content-Type: application/json (for JSON requests)
HX-Request: true (for HTMX requests)
```

### Response Headers
```
X-Robots-Tag: noindex, nofollow (on all HTML responses)
```

---

## Event Submission Endpoints

### GET /{site_slug}

Render event submission form.

**Parameters:**
- `site_slug` (path): Site identifier (e.g., "dctech")

**Response:** HTML form

**Example:**
```bash
curl https://yourdomain.com/dctech
```

---

### GET /{site_slug}/meetup

Render meetup group submission form.

**Parameters:**
- `site_slug` (path): Site identifier

**Response:** HTML form

---

### GET /{site_slug}/ical

Render iCal feed submission form.

**Parameters:**
- `site_slug` (path): Site identifier

**Response:** HTML form

---

### POST /{site_slug}/submit

Submit one or more events.

**Parameters:**
- `site_slug` (path): Site identifier

**Request Body:**
```json
{
  "csrf_token": "timestamp.signature",
  "submitted_by": "John Doe",
  "submitter_link": "https://example.com",
  "email": "john@example.com",
  "events": [
    {
      "title": "Tech Meetup",
      "date": "2024-01-15",
      "end_date": "2024-01-15",
      "time": "18:00",
      "url": "https://example.com/event",
      "location": "123 Main St",
      "cost": "Free"
    }
  ]
}
```

**Response (200):**
```json
{
  "message": "Submission received. Please check your email..."
}
```

**Errors:**
- `400`: Validation failed
- `403`: Invalid CSRF token
- `404`: Site not found
- `415`: Invalid content type

---

### POST /{site_slug}/submit_meetup

Submit meetup group(s).

**Request Body:**
```json
{
  "csrf_token": "timestamp.signature",
  "submitted_by": "Jane Doe",
  "email": "jane@example.com",
  "groups": [
    {
      "name": "DC Python Users",
      "url": "https://meetup.com/dc-python"
    }
  ]
}
```

---

### POST /{site_slug}/submit_ical

Submit iCal feed.

**Request Body:**
```json
{
  "csrf_token": "timestamp.signature",
  "name": "Tech Calendar",
  "url": "https://example.com",
  "ical": "https://example.com/calendar.ics",
  "fallback_url": "https://example.com/events",
  "submitted_by": "Admin",
  "email": "admin@example.com"
}
```

---

### GET /{site_slug}/confirm/{submission_id}

Preview submission before confirming.

**Parameters:**
- `site_slug` (path): Site identifier
- `submission_id` (path): UUID of submission

**Response:** HTML confirmation page

---

### POST /{site_slug}/confirm/{submission_id}/submit

Confirm submission and create GitHub PR.

**Parameters:**
- `site_slug` (path): Site identifier
- `submission_id` (path): UUID of submission

**Request Body:**
```json
{
  "csrf_token": "timestamp.signature"
}
```

**Response:** HTML success page with PR URL

---

## Newsletter Endpoints

### GET /{site_slug}/newsletter

Newsletter signup page.

**Parameters:**
- `site_slug` (path): Site identifier

**Response:** HTML signup form

**HTMX Support:**
- Add header `HX-Request: true` to get only the form partial

---

### POST /{site_slug}/newsletter/signup

Subscribe to newsletter.

**Parameters:**
- `site_slug` (path): Site identifier

**Request Body (JSON):**
```json
{
  "email": "subscriber@example.com"
}
```

**Request Body (Form):**
```
email=subscriber@example.com
```

**Response (200):**
```json
{
  "message": "Please check your email..."
}
```

**HTMX Response:** HTML success partial

---

### GET /{site_slug}/newsletter/confirm/{encoded_email}/{encoded_timestamp}/{signature}

Email confirmation link.

**Parameters:**
- `site_slug` (path): Site identifier
- `encoded_email` (path): Base64-encoded email
- `encoded_timestamp` (path): Base64-encoded timestamp
- `signature` (path): KMS HMAC signature

**Response:** HTML confirmation page

**Errors:**
- `400`: Link expired or invalid

---

### POST /{site_slug}/newsletter/confirm

Confirm newsletter subscription.

**Request Body (Form):**
```
email=subscriber@example.com
timestamp=1234567890
signature=kms_signature_here
```

**Response:** 303 redirect to success page

---

### GET /{site_slug}/newsletter/confirm/success

Subscription success page.

**Response:** HTML success message

---

### GET /{site_slug}/newsletter/unsubscribe/{encoded_email}/{encoded_timestamp}/{signature}

Unsubscribe preview page.

**Parameters:** Same as confirm link

**Response:** HTML unsubscribe confirmation page

---

### POST /{site_slug}/newsletter/unsubscribe

Process unsubscribe request.

**Request Body (Form):**
```
email=subscriber@example.com
timestamp=1234567890
signature=kms_signature_here
```

**Response:** HTML unsubscribed confirmation

---

## Health Check

### GET /health

Application health check.

**Response (200):**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

## Error Responses

### Standard Error Format (JSON)

```json
{
  "error": "Error message here"
}
```

### Standard Error Format (HTMX/HTML)

```html
<div class="alert alert-danger">Error message here</div>
```

### HTTP Status Codes

- `200`: Success
- `302/303`: Redirect
- `400`: Bad Request - Invalid input
- `403`: Forbidden - CSRF validation failed
- `404`: Not Found - Resource doesn't exist
- `415`: Unsupported Media Type - Wrong Content-Type
- `500`: Internal Server Error

---

## Rate Limiting

Currently no rate limiting is implemented. Consider adding rate limiting in production using:
- nginx rate limiting
- Flask-Limiter
- AWS WAF

---

## CSRF Protection

All POST endpoints require a valid CSRF token.

### Token Generation

Tokens are generated server-side and embedded in forms:
```html
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
```

### Token Format

```
timestamp.hmac_signature
```

- Valid for 1 hour
- HMAC-SHA256 signed with secret key

---

## HTMX Integration

### Triggering HTMX Requests

Add `hx-*` attributes to HTML elements:

```html
<form hx-post="/dctech/newsletter/signup" hx-target="#message">
  <input type="email" name="email" required>
  <button type="submit">Subscribe</button>
</form>
<div id="message"></div>
```

### HTMX Response Headers

The server may return these headers:
- `HX-Redirect`: Client-side redirect
- `HX-Trigger`: Trigger client-side events

---

## Examples

### cURL Examples

#### Submit Event
```bash
curl -X POST https://yourdomain.com/dctech/submit \
  -H "Content-Type: application/json" \
  -d '{
    "csrf_token": "1234567890.abcdef...",
    "email": "user@example.com",
    "events": [{
      "title": "Test Event",
      "date": "2024-01-15",
      "time": "18:00",
      "url": "https://example.com"
    }]
  }'
```

#### Subscribe to Newsletter
```bash
curl -X POST https://yourdomain.com/dctech/newsletter/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
```

### JavaScript Examples

#### Event Submission
```javascript
fetch('/dctech/submit', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    csrf_token: document.getElementById('csrf_token').value,
    email: 'user@example.com',
    events: [{
      title: 'Test Event',
      date: '2024-01-15',
      time: '18:00',
      url: 'https://example.com'
    }]
  })
})
.then(response => response.json())
.then(data => console.log(data));
```

---

## Testing

### Run Application Tests
```bash
python -m pytest tests/
```

### Manual Testing Checklist

- [ ] Event form loads
- [ ] Event submission works
- [ ] Email confirmation received
- [ ] GitHub PR created
- [ ] Newsletter signup works
- [ ] Email confirmation works
- [ ] Unsubscribe works
- [ ] HTMX partials render
- [ ] Error pages display
- [ ] CSRF validation works
