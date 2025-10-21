from chalice import Chalice, Rate, CORSConfig
from chalice.app import Response, AuthResponse
import boto3
import json
import os
import requests
from datetime import datetime, timedelta
import uuid
from base64 import b64encode, urlsafe_b64decode, urlsafe_b64encode
import hmac
import hashlib
import html
from urllib.parse import urlencode
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Initialize Jinja2 environment
env = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), 'chalicelib/templates')),
    autoescape=select_autoescape(['html', 'xml'])
)

# Configure CORS
# The space-separated list of allowed origins is not supported by every client, may need
# custom implementation https://aws.github.io/chalice/api.html?highlight=cors#CORSConfig.allow_origin
cors_config = CORSConfig(
    allow_origin='https://dctech.events',
    allow_headers=['Content-Type', 'HX-Request', 'HX-Trigger', 'HX-Target', 'HX-Prompt', 
                  'HX-Current-URL', 'HX-Boosted', 'HX-History-Restore-Request'],
    max_age=86400,
    expose_headers=['Content-Type', 'HX-Location', 'HX-Push-Url', 'HX-Redirect', 
                   'HX-Refresh', 'HX-Retarget', 'HX-Reswap', 'HX-Trigger',
                   'HX-Trigger-After-Settle', 'HX-Trigger-After-Swap'],
)

app = Chalice(app_name='dctech-newsletter')
app.debug = False

@app.middleware('http')
def add_no_index_header(event, get_response):
    response = get_response(event)
    if isinstance(response, Response) and 'Content-Type' in response.headers:
        if response.headers['Content-Type'].startswith('text/html'):
            response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    return response

# Initialize AWS clients
ses = boto3.client('sesv2')  # Using SESv2 for contact list features
kms = boto3.client('kms')
secrets = boto3.client('secretsmanager')

# Constants
FROM_EMAIL = 'outbound@dctech.events'
REPLY_TO_EMAIL = 'ross@karchner.com'
CONTACT_LIST_NAME = 'newsletters'
TOPIC_NAME = 'dctech'
CONFIRMATION_KEY_ID = os.environ.get('CONFIRMATION_KEY_ID')  # KMS key ID for HMAC signing
CSRF_SECRET = None  # Will be loaded from Secrets Manager

def get_csrf_secret():
    global CSRF_SECRET
    if CSRF_SECRET is None:
        response = secrets.get_secret_value(SecretId='newsletter/csrf_secret')
        CSRF_SECRET = json.loads(response['SecretString'])['csrf_secret']
    return CSRF_SECRET

def generate_csrf_token(confirmation_id):
    """Generate a CSRF token for form protection"""
    secret = get_csrf_secret()
    timestamp = str(int(datetime.utcnow().timestamp()))
    message = f"{confirmation_id}:{timestamp}".encode()
    signature = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return f"{timestamp}.{signature}"

def verify_csrf_token(confirmation_id, token):
    """Verify a CSRF token for form protection and check it hasn't expired"""
    try:
        timestamp, signature = token.split('.')
        message = f"{confirmation_id}:{timestamp}".encode()
        secret = get_csrf_secret()
        expected_signature = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
        
        # Allow tokens generated in the last hour (3600 seconds)
        if int(datetime.utcnow().timestamp()) - int(timestamp) > 3600:  # 1 hour in seconds
            return False
            
        return signature == expected_signature
    except:
        return False

def generate_confirmation_signature(email, timestamp):
    """Generate a KMS HMAC signature for email confirmation"""
    message = f"{email}:{CONTACT_LIST_NAME}:{TOPIC_NAME}:{timestamp}".encode()
    print(message)
    response = kms.generate_mac(
        Message=message,
        KeyId=CONFIRMATION_KEY_ID,
        MacAlgorithm='HMAC_SHA_512'
    )
    return urlsafe_b64encode(response['Mac']).decode('utf-8').rstrip('=')

def verify_confirmation_signature(email, timestamp, signature):
    """Verify a KMS HMAC signature for email confirmation"""
    try:
        # Check if CONFIRMATION_KEY_ID is set
        if not CONFIRMATION_KEY_ID:
            print("Error: CONFIRMATION_KEY_ID is not set")
            raise ValueError("Missing CONFIRMATION_KEY_ID configuration")
            
        message = f"{email}:{CONTACT_LIST_NAME}:{TOPIC_NAME}:{timestamp}".encode()
        print(message)
        # Pad the signature if needed
        padded_sig = signature + '=' * (-len(signature) % 4)
        
        # Fix: Keep MAC bytes as binary data
        try:
            mac_bytes = urlsafe_b64decode(padded_sig.encode())
            
            response = kms.verify_mac(
                Message=message,
                KeyId=CONFIRMATION_KEY_ID,
                MacAlgorithm='HMAC_SHA_512',
                Mac=mac_bytes
            )
            return response['MacValid']
        except Exception as e:
            print(f"Error in base64 decoding or KMS verification: {str(e)}")
            return False
    except Exception as e:
        print(f"Error verifying signature: {str(e)}")
        return False

def generate_confirmation_url(email):
    """Generate a signed confirmation URL using path parameters and base64 encoded email"""
    timestamp = int(datetime.utcnow().timestamp())
    signature = generate_confirmation_signature(email, timestamp)
    encoded_email = urlsafe_b64encode(email.encode()).decode('utf-8').rstrip('=')
    encoded_timestamp = urlsafe_b64encode(str(timestamp).encode()).decode('utf-8').rstrip('=')
    return f"/confirm/{encoded_email}/{encoded_timestamp}/{signature}"

@app.route('/', cors=cors_config)
def index():
    template = env.get_template('index.html')
    is_htmx = app.current_request.headers.get('HX-Request') == 'true'
    
    if is_htmx:
        template = env.get_template('partials/signup_form.html')
    else:
        template = env.get_template('index.html')
    
    # Generate a temporary ID for CSRF token generation
    temp_id = str(uuid.uuid4())
    csrf_token = generate_csrf_token(temp_id)
    
    return Response(
        body=template.render(csrf_token=csrf_token, temp_id=temp_id),
        headers={'Content-Type': 'text/html'}
    )

@app.route('/signup', methods=['POST'], cors=cors_config, content_types=['application/x-www-form-urlencoded', 'application/json'])
def signup():
    is_htmx = app.current_request.headers.get('HX-Request') == 'true'
    request = app.current_request
    
    # Handle both form-encoded and JSON data
    try:
        if request.headers.get('Content-Type', '').startswith('application/x-www-form-urlencoded'):
            # Parse form data
            form_data = request.raw_body.decode('utf-8')
            from urllib.parse import parse_qs
            data = parse_qs(form_data)
            email = data.get('email', [''])[0]
        else:
            # Handle JSON data
            body = request.json_body
            email = body.get('email', '')
    except:
        email = ''
    
    if not email:
        error_msg = 'Email is required'
        if is_htmx:
            template = env.get_template('partials/error.html')
            return Response(
                body=template.render(error=error_msg),
                status_code=400,
                headers={'Content-Type': 'text/html'}
            )
        return Response(
            body={'error': error_msg},
            status_code=400,
            headers={'Content-Type': 'application/json'}
        )
    
    try:
        # Check if CONFIRMATION_KEY_ID is set
        if not CONFIRMATION_KEY_ID:
            print("Error: CONFIRMATION_KEY_ID is not set")
            raise ValueError("Missing CONFIRMATION_KEY_ID configuration")
            
        # Generate confirmation URL
        confirmation_url = generate_confirmation_url(email)
        base_url = os.environ.get('BASE_URL', 'https://newsletter.dctech.events')
        full_confirmation_url = f"{base_url}{confirmation_url}"
        
        # Send confirmation email
        template = env.get_template('confirmation_email.html')
        html_content = template.render(confirmation_url=full_confirmation_url)
        
        ses.send_email(
            FromEmailAddress=FROM_EMAIL,
            ReplyToAddresses=[REPLY_TO_EMAIL],
            Destination={
                'ToAddresses': [email]
            },
            Content={
                'Simple': {
                    'Subject': {
                        'Data': 'Confirm your subscription to DCTech Events Newsletter'
                    },
                    'Body': {
                        'Html': {
                            'Data': html_content
                        }
                    }
                }
            }
        )
        
        success_msg = 'Please check your email (and maybe your junk folder!) to confirm your subscription.'
        if is_htmx:
            template = env.get_template('partials/success.html')
            return Response(
                body=template.render(message=success_msg),
                headers={'Content-Type': 'text/html'}
            )
        
        return Response(
            body={'message': success_msg},
            headers={'Content-Type': 'application/json'}
        )
        
    except Exception as e:
        print(f"Subscription error: {str(e)}")
        error_msg = 'Failed to process subscription'
        if is_htmx:
            template = env.get_template('partials/error.html')
            return Response(
                body=template.render(error=error_msg),
                status_code=500,
                headers={'Content-Type': 'text/html'}
            )
        return Response(
            body={'error': error_msg},
            status_code=500,
            headers={'Content-Type': 'application/json'}
        )

@app.route('/confirm/{encoded_email}/{encoded_timestamp}/{signature}', methods=['GET'], cors=cors_config)
def confirm(encoded_email, encoded_timestamp, signature):
    try:
        # Add padding back to base64
        padded_email = encoded_email + '=' * (-len(encoded_email) % 4)
        padded_timestamp = encoded_timestamp + '=' * (-len(encoded_timestamp) % 4)
        email = urlsafe_b64decode(padded_email.encode()).decode('utf-8')
        timestamp = int(urlsafe_b64decode(padded_timestamp.encode()).decode('utf-8'))
        
        # Check if link is less than 6 hours old
        if datetime.utcnow().timestamp() - timestamp > 21600:  # 6 hours in seconds
            template = env.get_template('error.html')
            return Response(
                body=template.render(error='Confirmation link has expired'),
                status_code=400,
                headers={'Content-Type': 'text/html'}
            )
        
        # Verify signature
        if not verify_confirmation_signature(email, timestamp, signature):
            template = env.get_template('error.html')
            return Response(
                body=template.render(error='Invalid confirmation link'),
                status_code=400,
                headers={'Content-Type': 'text/html'}
            )
            
        # Show confirmation button
        template = env.get_template('confirm.html')
        return Response(
            body=template.render(
                email=email,
                timestamp=timestamp,
                signature=signature
            ),
            headers={'Content-Type': 'text/html'}
        )
        
    except Exception as e:
        print(f"Error in confirmation: {str(e)}")
        template = env.get_template('error.html')
        return Response(
            body=template.render(error='Invalid confirmation link'),
            status_code=400,
            headers={'Content-Type': 'text/html'}
        )

@app.route('/confirm', methods=['POST'], content_types=['application/x-www-form-urlencoded'])
def confirm_subscription():
    request = app.current_request
    
    try:
        # Parse form data
        form_data = request.raw_body.decode('utf-8')
        from urllib.parse import parse_qs
        data = parse_qs(form_data)
        email = data.get('email', [''])[0]
        timestamp = data.get('timestamp', [''])[0]
        signature = data.get('signature', [''])[0]
        
        if not all([email, timestamp, signature]):
            template = env.get_template('error.html')
            return Response(
                body=template.render(error='Invalid confirmation data'),
                status_code=400,
                headers={'Content-Type': 'text/html'}
            )
            
        timestamp = int(timestamp)
        # Check if link is less than 6 hours old
        if datetime.utcnow().timestamp() - timestamp > 21600:  # 6 hours in seconds
            template = env.get_template('error.html')
            return Response(
                body=template.render(error='Confirmation link has expired'),
                status_code=400,
                headers={'Content-Type': 'text/html'}
            )
            
        # Verify signature
        if not verify_confirmation_signature(email, timestamp, signature):
            template = env.get_template('error.html')
            return Response(
                body=template.render(error='Invalid confirmation data'),
                status_code=400,
                headers={'Content-Type': 'text/html'}
            )
            
        # Add contact to SES contact list with topic subscription
        try:
            ses.create_contact(
                ContactListName=CONTACT_LIST_NAME,
                EmailAddress=email,
                TopicPreferences=[
                    {
                        'TopicName': TOPIC_NAME,
                        'SubscriptionStatus': 'OPT_IN'
                    }
                ]
            )
        except ses.exceptions.AlreadyExistsException:
            # Contact exists, get their current topic preferences
            try:
                contact = ses.get_contact(
                    ContactListName=CONTACT_LIST_NAME,
                    EmailAddress=email
                )
                
                # Get existing topic preferences
                existing_preferences = contact['TopicPreferences']
                
                # Update or add the TOPIC_NAME preference while preserving others
                topic_found = False
                for pref in existing_preferences:
                    if pref['TopicName'] == TOPIC_NAME:
                        pref['SubscriptionStatus'] = 'OPT_IN'
                        topic_found = True
                        break
                
                if not topic_found:
                    existing_preferences.append({
                        'TopicName': TOPIC_NAME,
                        'SubscriptionStatus': 'OPT_IN'
                    })
                
                # Update contact with all topic preferences
                ses.update_contact(
                    ContactListName=CONTACT_LIST_NAME,
                    EmailAddress=email,
                    TopicPreferences=existing_preferences
                )
            except Exception as e:
                print(f"Error updating contact preferences: {str(e)}")
                raise
        
        # Redirect to success page
        return Response(
            status_code=303,
            body='',
            headers={
                'Location': '/confirm/success',
                'Content-Type': 'text/html'
            }
        )
        
    except Exception as e:
        print(e)
        template = env.get_template('error.html')
        return Response(
            body=template.render(error='Failed to confirm subscription'),
            status_code=500,
            headers={'Content-Type': 'text/html'}
        )

@app.route('/confirm/success', methods=['GET'], cors=cors_config)
def confirm_success():
    template = env.get_template('success.html')
    return Response(
        body=template.render(),
        headers={'Content-Type': 'text/html'}
    )

def send_newsletter_to_subscribers():
    """
    Send newsletter to all confirmed subscribers using SES with the dctech-newsletter template.
    Returns:
        dict: Summary of the operation
    """
    # Fetch newsletter content
    try:
        html_content = requests.get('https://dctech.events/newsletter.html').text
        text_content = requests.get('https://dctech.events/newsletter.txt').text
    except:
        error_msg = "Failed to fetch newsletter content"
        print(error_msg)
        return {'status': 'error', 'reason': error_msg}
    
    try:
        # Get all contacts from the list
        response = ses.list_contacts(ContactListName=CONTACT_LIST_NAME)
        contacts = response['Contacts']
        
        success_count = 0
        error_count = 0
        
        for contact in contacts:
            # Only send to contacts subscribed to the newsletter topic
            topic_preferences = contact.get('TopicPreferences', [])
            is_subscribed = any(
                pref['TopicName'] == TOPIC_NAME and pref['SubscriptionStatus'] == 'OPT_IN'
                for pref in topic_preferences
            )
            
            if not is_subscribed:
                continue
                
            try:
                # Send individual email using the SESv2 template
                ses.send_email(
                    FromEmailAddress=FROM_EMAIL,
                    ReplyToAddresses=[REPLY_TO_EMAIL],
                    Destination={
                        'ToAddresses': [contact['EmailAddress']]
                    },
                    Content={
                        'Template': {
                            'TemplateName': 'dctech-newsletter',
                            'TemplateData': json.dumps({
                                'content': html_content
                            })
                        }
                    },
                    ListManagementOptions={
                        'ContactListName': CONTACT_LIST_NAME,
                        'TopicName': TOPIC_NAME
                    }
                )
                success_count += 1
            except Exception as e:
                print(f"Error sending to {contact['EmailAddress']}: {str(e)}")
                error_count += 1
        
        return {
            'status': 'completed',
            'successful_sends': success_count,
            'failed_sends': error_count,
            'message': f'Newsletter sent successfully to {success_count} subscribers ({error_count} failures)'
        }
        
    except Exception as e:
        print(f"Error sending newsletter: {str(e)}")
        return {
            'status': 'error',
            'reason': str(e)
        }

@app.schedule('cron(0 11 ? * MON *)')  # Run at 6am Monday Eastern (11:00 UTC)
def scheduled_newsletter(event):
    """
    Scheduled function that runs at 6am Eastern Time every Monday to send the newsletter to all confirmed subscribers.
    Note: AWS cron expressions are in UTC, so 6am ET = 11am UTC
    """
    return send_newsletter_to_subscribers()

@app.on_sns_message(topic='newsletter-feedback')
def handle_ses_notification(event):
    """
    Handle SES feedback notifications (bounces, complaints).
    SES will automatically handle unsubscribe requests through the List-Unsubscribe header.
    """
    message = json.loads(event.message)
    
    # Check if this is an SES notification
    if message.get('notificationType') in ['Bounce', 'Complaint']:
        notification_type = message.get('notificationType')
        
        if notification_type == 'Bounce':
            bounce_type = message['bounce']['bounceType']  # 'Permanent' or 'Transient'
            recipients = [recipient['emailAddress'] for recipient in message['bounce']['bouncedRecipients']]
            
            # Only handle permanent bounces
            if bounce_type == 'Permanent':
                for email in recipients:
                    try:
                        # Delete contact from list
                        ses.delete_contact(
                            ContactListName=CONTACT_LIST_NAME,
                            EmailAddress=email
                        )
                    except Exception as e:
                        print(f"Error removing bounced contact {email}: {str(e)}")
                    
        elif notification_type == 'Complaint':
            recipients = [recipient['emailAddress'] for recipient in message['complaint']['complainedRecipients']]
            for email in recipients:
                try:
                    # Delete contact from list
                    ses.delete_contact(
                        ContactListName=CONTACT_LIST_NAME,
                        EmailAddress=email
                    )
                except Exception as e:
                    print(f"Error removing complained contact {email}: {str(e)}")
                
    return {'status': 'processed'}
