"""Routes for event submissions."""
from flask import render_template, request, jsonify, current_app, redirect, url_for
from flask_login import login_required, current_user
from . import events_bp
from .forms import EventForm, EventSubmissionForm
from utils.csrf import generate_csrf_token, validate_csrf_token
from services.database import SubmissionsService
from services.github_service import GitHubService
import uuid


def get_csrf_secret():
    """Get CSRF secret key from config."""
    return current_app.config.get('SECRET_KEY', 'dev-secret-key')


@events_bp.route('/<site_slug>')
def site_index(site_slug):
    """Render the landing page for a specific site."""
    site = current_app.config['get_site_by_slug'](site_slug)
    if not site:
        return jsonify({'error': 'Site not found'}), 404

    return render_template('site_index.html', site=site)


@events_bp.route('/<site_slug>/submit')
@login_required
def submit_form(site_slug):
    """Render the event submission form for a specific site."""
    site = current_app.config['get_site_by_slug'](site_slug)
    if not site:
        return jsonify({'error': 'Site not found'}), 404

    csrf_token, _ = generate_csrf_token(get_csrf_secret())
    return render_template('events/form.html', csrf_token=csrf_token, site=site)


@events_bp.route('/<site_slug>/submit', methods=['POST'])
@login_required
def submit_event(site_slug):
    """Handle event submission."""
    site = current_app.config['get_site_by_slug'](site_slug)
    if not site:
        return jsonify({'error': 'Site not found'}), 404

    if not request.is_json:
        return jsonify({'message': 'Content-Type must be application/json'}), 415

    data = request.get_json()

    # Validate CSRF token
    csrf_token = data.get('csrf_token')
    if not csrf_token or not validate_csrf_token(csrf_token, get_csrf_secret()):
        return jsonify({'error': 'Invalid or missing CSRF token'}), 403

    # Validate user information
    form = EventSubmissionForm(data=data)
    if not form.validate():
        return jsonify({'error': 'Validation failed', 'errors': form.errors}), 400

    # Validate events
    events = data.get('events', [])
    if not events:
        return jsonify({'error': 'At least one event is required'}), 400

    if len(events) > 5:
        return jsonify({'error': 'Maximum of 5 events allowed per submission'}), 400

    for event_data in events:
        event_form = EventForm(data=event_data)
        if not event_form.validate():
            return jsonify({'error': 'Event validation failed', 'errors': event_form.errors}), 400

    # Generate submission ID
    submission_id = str(uuid.uuid4())

    # Store in database
    SubmissionsService.create_submission(
        submission_id=submission_id,
        submission_type='event',
        site_slug=site_slug,
        user_id=current_user.id,
        email=current_user.email or data.get('email', ''),
        data={
            'submitted_by': current_user.username,
            'submitter_link': data.get('submitter_link', f'https://github.com/{current_user.username}'),
            'events': events
        }
    )

    # Redirect to confirmation page
    return jsonify({
        'message': 'Submission saved. Please confirm your submission.',
        'redirect': url_for('events.preview_confirmation', site_slug=site_slug, submission_id=submission_id)
    })


@events_bp.route('/<site_slug>/confirm/<submission_id>')
@login_required
def preview_confirmation(site_slug, submission_id):
    """Show confirmation preview page."""
    site = current_app.config['get_site_by_slug'](site_slug)
    if not site:
        return jsonify({'error': 'Site not found'}), 404

    # Get submission from database
    submission = SubmissionsService.get_submission(submission_id)

    if not submission:
        return jsonify({'error': 'Submission not found'}), 404

    # Verify user owns this submission
    if submission['user_id'] != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    if submission['status'] != 'pending':
        return jsonify({'error': 'Submission already processed'}), 400

    if submission.get('site_slug') != site_slug:
        return jsonify({'error': 'Invalid site for this submission'}), 400

    csrf_token, _ = generate_csrf_token(get_csrf_secret())
    return render_template('events/confirm.html', submission=submission,
                         csrf_token=csrf_token, site=site)


@events_bp.route('/<site_slug>/confirm/<submission_id>/submit', methods=['POST'])
@login_required
def confirm_submission(site_slug, submission_id):
    """Handle submission confirmation and create GitHub PR."""
    site = current_app.config['get_site_by_slug'](site_slug)
    if not site:
        return jsonify({'error': 'Site not found'}), 404

    # Get CSRF token from request
    if request.is_json:
        data = request.get_json() or {}
    else:
        data = request.form.to_dict()

    csrf_token = data.get('csrf_token')
    if not csrf_token or not validate_csrf_token(csrf_token, get_csrf_secret()):
        return jsonify({'error': 'Invalid or missing CSRF token'}), 403

    # Get submission from database
    submission = SubmissionsService.get_submission(submission_id)

    if not submission:
        return jsonify({'error': 'Submission not found'}), 404

    # Verify user owns this submission
    if submission['user_id'] != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    if submission['status'] != 'pending':
        return jsonify({'error': 'Submission already processed'}), 400

    if submission.get('site_slug') != site_slug:
        return jsonify({'error': 'Invalid site for this submission'}), 400

    # Check if user has GitHub token
    if not current_user.github_token:
        return jsonify({'error': 'GitHub authentication required'}), 401

    # Use user's GitHub token to create PR
    github_service = GitHubService(current_user.github_token)

    submission_type = submission.get('type', 'event')

    try:
        if submission_type == 'event':
            pr_url = github_service.create_pr_for_events(
                repo_url=site['github_repo'],
                events=submission['data']['events'],
                submitted_by=submission['data']['submitted_by'],
                submission_id=submission_id
            )
        else:
            return jsonify({'error': 'Unknown submission type'}), 400

        # Update submission status
        SubmissionsService.update_submission_status(submission_id, 'confirmed', pr_url)

        # Render success page
        return render_template('events/success.html', pr_url=pr_url, site=site)

    except Exception as e:
        current_app.logger.error(f"Error creating GitHub PR: {str(e)}")
        return jsonify({'error': f'Failed to create pull request: {str(e)}'}), 500
