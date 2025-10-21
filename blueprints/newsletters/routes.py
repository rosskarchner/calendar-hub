"""Routes for newsletter subscriptions."""
from flask import render_template, request, jsonify, redirect, url_for, current_app
from . import newsletters_bp
from .forms import NewsletterSignupForm
from utils.csrf import generate_csrf_token, validate_csrf_token
from services.sesv2 import NewsletterService
from services.kms import KMSService
from services.aws_clients import get_secret
from base64 import urlsafe_b64encode, urlsafe_b64decode
from datetime import datetime
import uuid


def get_csrf_secret():
    """Get CSRF secret key from config or Secrets Manager."""
    if current_app.config.get('DEBUG'):
        return current_app.config.get('SECRET_KEY', 'dev-secret-key')
    return get_secret(current_app.config['NEWSLETTER_CSRF_SECRET_NAME'])


def generate_confirmation_url(email: str, site: dict, kms_service: KMSService) -> str:
    """Generate a signed confirmation URL."""
    timestamp = int(datetime.utcnow().timestamp())
    signature = kms_service.generate_confirmation_signature(
        email=email,
        contact_list_name=site['contact_list_name'],
        topic_name=site['topic_name'],
        timestamp=timestamp
    )
    encoded_email = urlsafe_b64encode(email.encode()).decode('utf-8').rstrip('=')
    encoded_timestamp = urlsafe_b64encode(str(timestamp).encode()).decode('utf-8').rstrip('=')
    return f"/{site['slug']}/newsletter/confirm/{encoded_email}/{encoded_timestamp}/{signature}"


@newsletters_bp.route('/<site_slug>/newsletter')
def newsletter_signup(site_slug):
    """Render the newsletter signup form."""
    site = current_app.config['get_site_by_slug'](site_slug)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    is_htmx = request.headers.get('HX-Request') == 'true'
    temp_id = str(uuid.uuid4())
    csrf_token = generate_csrf_token(get_csrf_secret())
    
    if is_htmx:
        return render_template('newsletters/partials/signup_form.html', 
                             csrf_token=csrf_token, temp_id=temp_id)
    
    return render_template('newsletters/index.html', 
                         csrf_token=csrf_token, temp_id=temp_id, site=site)


@newsletters_bp.route('/<site_slug>/newsletter/signup', methods=['POST'])
def signup(site_slug):
    """Handle newsletter signup submission."""
    site = current_app.config['get_site_by_slug'](site_slug)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    is_htmx = request.headers.get('HX-Request') == 'true'
    
    # Handle both form-encoded and JSON data
    if request.is_json:
        email = request.json.get('email', '')
    else:
        email = request.form.get('email', '')
    
    if not email:
        error_msg = 'Email is required'
        if is_htmx:
            return render_template('newsletters/partials/error.html', error=error_msg), 400
        return jsonify({'error': error_msg}), 400
    
    # Validate email
    form = NewsletterSignupForm(data={'email': email})
    if not form.validate():
        error_msg = 'Invalid email address'
        if is_htmx:
            return render_template('newsletters/partials/error.html', error=error_msg), 400
        return jsonify({'error': error_msg}), 400
    
    try:
        # Initialize KMS service
        confirmation_key_id = current_app.config.get('CONFIRMATION_KEY_ID')
        if not confirmation_key_id:
            raise ValueError("CONFIRMATION_KEY_ID not configured")
        
        kms_service = KMSService(confirmation_key_id)
        
        # Generate confirmation URL
        confirmation_path = generate_confirmation_url(email, site, kms_service)
        domain_name = current_app.config.get('DOMAIN_NAME', request.host)
        protocol = 'https' if 'localhost' not in domain_name else 'http'
        full_confirmation_url = f"{protocol}://{domain_name}{confirmation_path}"
        
        # Render confirmation email template
        html_content = render_template('newsletters/confirmation_email.html',
                                      confirmation_url=full_confirmation_url)
        
        # Send confirmation email
        NewsletterService.send_confirmation_email(
            to_email=email,
            from_email=site.get('from_email', current_app.config['SENDER_EMAIL']),
            reply_to=site.get('reply_to_email', site.get('from_email')),
            confirmation_url=full_confirmation_url,
            subject=f'Confirm your subscription to {site["name"]}',
            html_content=html_content
        )
        
        success_msg = 'Please check your email (and maybe your junk folder!) to confirm your subscription.'
        if is_htmx:
            return render_template('newsletters/partials/success.html', message=success_msg)
        
        return jsonify({'message': success_msg})
        
    except Exception as e:
        current_app.logger.error(f"Subscription error: {str(e)}")
        error_msg = 'Failed to process subscription'
        if is_htmx:
            return render_template('newsletters/partials/error.html', error=error_msg), 500
        return jsonify({'error': error_msg}), 500


@newsletters_bp.route('/<site_slug>/newsletter/confirm/<encoded_email>/<encoded_timestamp>/<signature>')
def confirm_preview(site_slug, encoded_email, encoded_timestamp, signature):
    """Show confirmation preview page."""
    site = current_app.config['get_site_by_slug'](site_slug)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    try:
        # Decode email and timestamp
        padded_email = encoded_email + '=' * (-len(encoded_email) % 4)
        padded_timestamp = encoded_timestamp + '=' * (-len(encoded_timestamp) % 4)
        email = urlsafe_b64decode(padded_email.encode()).decode('utf-8')
        timestamp = int(urlsafe_b64decode(padded_timestamp.encode()).decode('utf-8'))
        
        # Check if link is less than 6 hours old
        if datetime.utcnow().timestamp() - timestamp > 21600:  # 6 hours
            return render_template('newsletters/error.html', 
                                 error='Confirmation link has expired'), 400
        
        # Verify signature
        confirmation_key_id = current_app.config.get('CONFIRMATION_KEY_ID')
        kms_service = KMSService(confirmation_key_id)
        
        if not kms_service.verify_confirmation_signature(
            email=email,
            contact_list_name=site['contact_list_name'],
            topic_name=site['topic_name'],
            timestamp=timestamp,
            signature=signature
        ):
            return render_template('newsletters/error.html',
                                 error='Invalid confirmation link'), 400
        
        # Show confirmation button
        return render_template('newsletters/confirm.html',
                             email=email,
                             timestamp=timestamp,
                             signature=signature,
                             site=site)
    
    except Exception as e:
        current_app.logger.error(f"Error in confirmation preview: {str(e)}")
        return render_template('newsletters/error.html',
                             error='Invalid confirmation link'), 400


@newsletters_bp.route('/<site_slug>/newsletter/confirm', methods=['POST'])
def confirm_subscription(site_slug):
    """Handle final subscription confirmation."""
    site = current_app.config['get_site_by_slug'](site_slug)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    try:
        # Get form data
        email = request.form.get('email')
        timestamp = request.form.get('timestamp')
        signature = request.form.get('signature')
        
        if not all([email, timestamp, signature]):
            return render_template('newsletters/error.html',
                                 error='Invalid confirmation data'), 400
        
        timestamp = int(timestamp)
        
        # Check if link is less than 6 hours old
        if datetime.utcnow().timestamp() - timestamp > 21600:
            return render_template('newsletters/error.html',
                                 error='Confirmation link has expired'), 400
        
        # Verify signature
        confirmation_key_id = current_app.config.get('CONFIRMATION_KEY_ID')
        kms_service = KMSService(confirmation_key_id)
        
        if not kms_service.verify_confirmation_signature(
            email=email,
            contact_list_name=site['contact_list_name'],
            topic_name=site['topic_name'],
            timestamp=timestamp,
            signature=signature
        ):
            return render_template('newsletters/error.html',
                                 error='Invalid confirmation data'), 400
        
        # Add contact to SES contact list
        NewsletterService.create_or_update_contact(
            contact_list_name=site['contact_list_name'],
            email=email,
            topic_name=site['topic_name']
        )
        
        # Redirect to success page
        return redirect(url_for('newsletters.confirm_success', site_slug=site_slug))
    
    except Exception as e:
        current_app.logger.error(f"Error confirming subscription: {str(e)}")
        return render_template('newsletters/error.html',
                             error='Failed to confirm subscription'), 500


@newsletters_bp.route('/<site_slug>/newsletter/confirm/success')
def confirm_success(site_slug):
    """Show subscription success page."""
    site = current_app.config['get_site_by_slug'](site_slug)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    return render_template('newsletters/success.html', site=site)


@newsletters_bp.route('/<site_slug>/newsletter/unsubscribe/<encoded_email>/<encoded_timestamp>/<signature>')
def unsubscribe_preview(site_slug, encoded_email, encoded_timestamp, signature):
    """Show unsubscribe preview page."""
    site = current_app.config['get_site_by_slug'](site_slug)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    try:
        # Decode email and timestamp
        padded_email = encoded_email + '=' * (-len(encoded_email) % 4)
        padded_timestamp = encoded_timestamp + '=' * (-len(encoded_timestamp) % 4)
        email = urlsafe_b64decode(padded_email.encode()).decode('utf-8')
        timestamp = int(urlsafe_b64decode(padded_timestamp.encode()).decode('utf-8'))
        
        # Verify signature (no time limit for unsubscribe)
        confirmation_key_id = current_app.config.get('CONFIRMATION_KEY_ID')
        kms_service = KMSService(confirmation_key_id)
        
        if not kms_service.verify_confirmation_signature(
            email=email,
            contact_list_name=site['contact_list_name'],
            topic_name=site['topic_name'],
            timestamp=timestamp,
            signature=signature
        ):
            return render_template('newsletters/error.html',
                                 error='Invalid unsubscribe link'), 400
        
        # Show unsubscribe confirmation
        return render_template('newsletters/unsubscribe.html',
                             email=email,
                             timestamp=timestamp,
                             signature=signature,
                             site=site)
    
    except Exception as e:
        current_app.logger.error(f"Error in unsubscribe preview: {str(e)}")
        return render_template('newsletters/error.html',
                             error='Invalid unsubscribe link'), 400


@newsletters_bp.route('/<site_slug>/newsletter/unsubscribe', methods=['POST'])
def unsubscribe(site_slug):
    """Handle unsubscribe confirmation."""
    site = current_app.config['get_site_by_slug'](site_slug)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    
    try:
        # Get form data
        email = request.form.get('email')
        timestamp = request.form.get('timestamp')
        signature = request.form.get('signature')
        
        if not all([email, timestamp, signature]):
            return render_template('newsletters/error.html',
                                 error='Invalid unsubscribe data'), 400
        
        timestamp = int(timestamp)
        
        # Verify signature
        confirmation_key_id = current_app.config.get('CONFIRMATION_KEY_ID')
        kms_service = KMSService(confirmation_key_id)
        
        if not kms_service.verify_confirmation_signature(
            email=email,
            contact_list_name=site['contact_list_name'],
            topic_name=site['topic_name'],
            timestamp=timestamp,
            signature=signature
        ):
            return render_template('newsletters/error.html',
                                 error='Invalid unsubscribe data'), 400
        
        # Unsubscribe contact
        NewsletterService.unsubscribe_contact(
            contact_list_name=site['contact_list_name'],
            email=email,
            topic_name=site['topic_name']
        )
        
        # Show unsubscribed confirmation
        return render_template('newsletters/unsubscribed.html', site=site)
    
    except Exception as e:
        current_app.logger.error(f"Error unsubscribing: {str(e)}")
        return render_template('newsletters/error.html',
                             error='Failed to unsubscribe'), 500
