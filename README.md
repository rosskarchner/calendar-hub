# Calendar Hub

A multi-site event submission system that allows users to submit events via a web form and automatically creates GitHub pull requests for approval.

## Features

- **GitHub OAuth Authentication**: Users authenticate with their GitHub accounts
- **Multi-Site Support**: Single application can serve multiple communities
- **Event Submission**: Users submit events that are stored in PostgreSQL
- **Automatic PR Creation**: Creates GitHub PRs using the submitter's account
- **Newsletter Management**: AWS SES-based newsletter subscriptions with KMS-signed confirmation links
- **Docker Support**: Fully containerized with Docker Compose

## Requirements

- Docker and Docker Compose
- GitHub OAuth App credentials
- A GitHub repository for storing event data
- AWS account with SES and KMS configured (for newsletter functionality)

## Quick Start

### 1. Register a GitHub OAuth App

1. Go to https://github.com/settings/developers
2. Click "New OAuth App"
3. Fill in the details:
   - **Application name**: Calendar Hub (or your preferred name)
   - **Homepage URL**: `http://localhost:5000`
   - **Authorization callback URL**: `http://localhost:5000/auth/callback`
4. Click "Register application"
5. Note your **Client ID** and generate a **Client Secret**

### 2. Configure Environment Variables

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` and set:
- `GITHUB_CLIENT_ID`: Your GitHub OAuth App Client ID
- `GITHUB_CLIENT_SECRET`: Your GitHub OAuth App Client Secret
- `SECRET_KEY`: A random secret key for Flask session security

```bash
# Generate a random secret key
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

### 3. Start the Application

```bash
docker-compose up --build
```

The application will be available at http://localhost:5000

### 4. Configure Sites

Edit `sites.json` to configure the communities/calendars you want to serve:

```json
{
  "sites": [
    {
      "name": "DC Tech Events",
      "slug": "dctech",
      "github_repo": "https://github.com/your-org/your-calendar-repo",
      "from_email": "events@example.com"
    }
  ]
}
```

## Architecture Changes

This version has been refactored from the original AWS-based architecture:

### What Changed

| Before (AWS) | After (Docker + AWS) |
|-------------|----------------|
| DynamoDB | PostgreSQL |
| AWS Secrets Manager | Environment variables |
| Magic link authentication (email) | GitHub OAuth |
| Service account creates PRs | User's GitHub account creates PRs |
| AWS SES for event confirmations | Not needed (GitHub OAuth) |
| AWS SES/KMS for newsletters | Still used for newsletters |

### Key Improvements

1. **User-Created PRs**: Pull requests are now created using the authenticated user's GitHub token, so PRs appear to come from the actual submitter
2. **Reduced AWS Dependencies**: Only SES and KMS needed for newsletter functionality
3. **Simplified Event Auth**: GitHub OAuth eliminates email verification flow for event submissions
4. **PostgreSQL**: Standard relational database instead of DynamoDB
5. **Docker-First**: Easy local development with docker-compose

## Development

### Local Development Without Docker

1. Install PostgreSQL locally
2. Create a database:
   ```bash
   createdb calendar_hub
   ```

3. Set up a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. Set environment variables (use `.env` file or export directly):
   ```bash
   export DATABASE_URL="postgresql://localhost/calendar_hub"
   export GITHUB_CLIENT_ID="your_client_id"
   export GITHUB_CLIENT_SECRET="your_client_secret"
   export SECRET_KEY="your_secret_key"
   ```

5. Run the application:
   ```bash
   python app.py
   ```

### Database Migrations

The application automatically creates database tables on startup. To reset the database:

```bash
docker-compose down -v  # Remove volumes
docker-compose up       # Recreate with fresh database
```

## API Endpoints

### Authentication
- `GET /auth/login` - Redirect to GitHub OAuth login
- `GET /auth/callback` - GitHub OAuth callback handler
- `GET /auth/logout` - Logout current user
- `GET /auth/user` - Get current user info (JSON)

### Events
- `GET /<site_slug>` - Site landing page
- `GET /<site_slug>/submit` - Event submission form (requires login)
- `POST /<site_slug>/submit` - Submit events (requires login)
- `GET /<site_slug>/confirm/<submission_id>` - Preview submission
- `POST /<site_slug>/confirm/<submission_id>/submit` - Create GitHub PR

### Health Check
- `GET /health` - Application health status

## Troubleshooting

### "GitHub authentication required" error
- Make sure you're logged in with GitHub
- Check that your GitHub OAuth credentials are correct
- Verify the callback URL matches exactly

### Database connection errors
- Ensure PostgreSQL container is running: `docker-compose ps`
- Check database logs: `docker-compose logs db`

### PR creation fails
- Verify the GitHub repository URL in `sites.json`
- Ensure the authenticated user has write access to the repository
- Check that the repository structure matches expected format

## Security Notes

1. **GitHub Token Storage**: User GitHub tokens are stored in the database. In production, consider encrypting these tokens.
2. **Secret Key**: Always use a strong, random secret key in production.
3. **HTTPS**: Use HTTPS in production to protect tokens in transit.
4. **OAuth Scopes**: The app requests `user:email` scope. Add repository scopes if needed.

## Newsletter Functionality

Newsletter subscriptions use AWS SES and KMS for secure, stateless confirmation links.

### AWS Setup for Newsletters

1. **Configure AWS Credentials**:
   - Install AWS CLI: `pip install awscli`
   - Run `aws configure` to set up credentials
   - Or use IAM roles if running in AWS (EC2, ECS, etc.)

2. **Set up AWS SES**:
   - Verify your sender email address in SES console
   - If in sandbox mode, also verify recipient emails for testing
   - Request production access for unlimited recipients

3. **Create KMS Key**:
   - Go to AWS KMS console
   - Create a symmetric encryption key
   - Note the Key ID and add to `.env` as `CONFIRMATION_KEY_ID`

4. **Configure IAM Permissions**:
   Your AWS credentials need these permissions:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "ses:SendEmail",
           "sesv2:SendEmail",
           "sesv2:CreateContact",
           "sesv2:UpdateContact",
           "sesv2:DeleteContact",
           "kms:GenerateMac",
           "kms:VerifyMac"
         ],
         "Resource": "*"
       }
     ]
   }
   ```

5. **Update sites.json**:
   Add newsletter configuration for each site:
   ```json
   {
     "name": "DC Tech Events",
     "slug": "dctech",
     "github_repo": "https://github.com/your-org/your-repo",
     "from_email": "events@example.com",
     "contact_list_name": "dctech-newsletter",
     "topic_name": "dctech-events"
   }
   ```

## License

[Your License Here]

## Contributing

[Contributing Guidelines Here]
