import pytest
from chalice.test import Client
from app import app
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import base64

@pytest.fixture
def test_client():
    return Client(app)

@pytest.fixture
def mock_ses():
    with patch('app.ses') as mock:
        yield mock

@pytest.fixture
def mock_kms():
    with patch('app.kms') as mock:
        # Mock KMS HMAC generation and verification
        mock.generate_mac.return_value = {'Mac': b'test_mac'}
        mock.verify_mac.return_value = {'MacValid': True}
        yield mock

def test_index_returns_htmx_partial(test_client):
    response = test_client.http.get(
        '/',
        headers={'HX-Request': 'true'}
    )
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/html'
    assert '<form id="signup-form" hx-post="/signup"' in response.body
    assert '<input type="email"' in response.body
    assert '<button type="submit">Subscribe</button>' in response.body
    assert 'DC Tech Events Weekly' not in response.body  # Should not include full page

def test_signup_sends_confirmation_email(test_client, mock_ses, mock_kms):
    response = test_client.http.post(
        '/signup',
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'HX-Request': 'true'
        },
        body='email=test%40example.com'
    )
    
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/html'
    assert 'Please check your email' in response.body
    mock_ses.send_email.assert_called_once()
    # Verify email was sent with confirmation link
    call_args = mock_ses.send_email.call_args[1]
    assert call_args['FromEmailAddress'] == 'outbound@dctech.events'
    assert call_args['Destination']['ToAddresses'] == ['test@example.com']
    assert 'Confirm your subscription' in call_args['Content']['Simple']['Subject']['Data']
    assert '/confirm/' in call_args['Content']['Simple']['Body']['Html']['Data']

def test_confirm_get_shows_confirmation_page(test_client, mock_kms):
    # Generate base64 encoded email and timestamp
    encoded_email = base64.urlsafe_b64encode('test@example.com'.encode()).decode().rstrip('=')
    timestamp = int(datetime.utcnow().timestamp())
    encoded_timestamp = base64.urlsafe_b64encode(str(timestamp).encode()).decode().rstrip('=')
    response = test_client.http.get(
        f'/confirm/{encoded_email}/{encoded_timestamp}/test_signature'
    )
    
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/html'
    assert 'Confirm your subscription' in response.body
    assert 'test@example.com' in response.body
    assert 'type="hidden"' in response.body
    assert 'test_signature' in response.body
def test_confirm_get_rejects_expired_link(test_client, mock_kms):
    # Generate base64 encoded email and timestamp from 7 hours ago
    encoded_email = base64.urlsafe_b64encode('test@example.com'.encode()).decode().rstrip('=')
    timestamp = int((datetime.utcnow() - timedelta(hours=7)).timestamp())
    encoded_timestamp = base64.urlsafe_b64encode(str(timestamp).encode()).decode().rstrip('=')
    response = test_client.http.get(
        f'/confirm/{encoded_email}/{encoded_timestamp}/test_signature'
    )
    
    assert response.status_code == 400
    assert response.headers['Content-Type'] == 'text/html'
    assert 'expired' in response.body

def test_confirm_get_accepts_recent_link(test_client, mock_kms):
    # Generate base64 encoded email and timestamp from 5 hours ago (within 6 hour limit)
    encoded_email = base64.urlsafe_b64encode('test@example.com'.encode()).decode().rstrip('=')
    timestamp = int((datetime.utcnow() - timedelta(hours=5)).timestamp())
    encoded_timestamp = base64.urlsafe_b64encode(str(timestamp).encode()).decode().rstrip('=')
    response = test_client.http.get(
        f'/confirm/{encoded_email}/{encoded_timestamp}/test_signature'
    )
    
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/html'
    assert 'Confirm your subscription' in response.body
    assert str(timestamp) in response.body

def test_confirm_post_adds_to_contact_list(test_client, mock_ses, mock_kms):
    timestamp = int(datetime.utcnow().timestamp())
    response = test_client.http.post(
        '/confirm',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        body=f'email=test%40example.com&timestamp={timestamp}&signature=test_signature'
    )
    
    assert response.status_code == 303
    assert response.headers['Location'] == '/confirm/success'
    mock_ses.create_contact.assert_called_once_with(
        ContactListName='newsletters',
        EmailAddress='test@example.com',
        TopicPreferences=[{
            'TopicName': 'dctech',
            'SubscriptionStatus': 'OPT_IN'
        }]
    )
    mock_ses.update_contact.assert_not_called()

def test_confirm_post_updates_existing_contact(test_client, mock_ses, mock_kms):
    # Mock create_contact to raise AlreadyExistsException
    mock_ses.create_contact.side_effect = mock_ses.exceptions.AlreadyExistsException({}, 'Operation')
    
    # Mock get_contact to return existing preferences
    mock_ses.get_contact.return_value = {
        'Contact': {
            'EmailAddress': 'test@example.com',
            'TopicPreferences': [
                {
                    'TopicName': 'other_topic',
                    'SubscriptionStatus': 'OPT_IN'
                },
                {
                    'TopicName': 'dctech',
                    'SubscriptionStatus': 'OPT_OUT'
                }
            ]
        }
    }
    
    timestamp = int(datetime.utcnow().timestamp())
    response = test_client.http.post(
        '/confirm',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        body=f'email=test%40example.com&timestamp={timestamp}&signature=test_signature'
    )
    
    assert response.status_code == 303
    assert response.headers['Location'] == '/confirm/success'
    mock_ses.create_contact.assert_called_once()
    mock_ses.get_contact.assert_called_once_with(
        ContactListName='newsletters',
        EmailAddress='test@example.com'
    )
    mock_ses.update_contact.assert_called_once_with(
        ContactListName='newsletters',
        EmailAddress='test@example.com',
        TopicPreferences=[
            {
                'TopicName': 'other_topic',
                'SubscriptionStatus': 'OPT_IN'
            },
            {
                'TopicName': 'dctech',
                'SubscriptionStatus': 'OPT_IN'
            }
        ]
    )

def test_confirm_post_rejects_expired_timestamp(test_client, mock_ses, mock_kms):
    # Generate timestamp from 7 hours ago
    timestamp = int((datetime.utcnow() - timedelta(hours=7)).timestamp())
    response = test_client.http.post(
        '/confirm',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        body=f'email=test%40example.com&timestamp={timestamp}&signature=test_signature'
    )
    
    assert response.status_code == 400
    assert 'expired' in response.body
    mock_ses.create_contact.assert_not_called()

def test_confirm_post_rejects_invalid_signature(test_client, mock_ses, mock_kms):
    mock_kms.verify_mac.return_value = {'MacValid': False}
    timestamp = int(datetime.utcnow().timestamp())
    response = test_client.http.post(
        '/confirm',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        body=f'email=test%40example.com&timestamp={timestamp}&signature=invalid_signature'
    )
    
    assert response.status_code == 400
    assert 'Invalid' in response.body
    mock_ses.create_contact.assert_not_called()

def test_cors_headers_for_allowed_origins(test_client):
    # Test localhost:5000 origin
    response = test_client.http.get(
        '/',
        headers={'origin': 'http://localhost:5000'}
    )
    assert response.headers['Access-Control-Allow-Origin'] == 'http://localhost:5000'
    assert 'Content-Type, HX-Request, HX-Trigger, HX-Target, HX-Prompt, HX-Current-URL, HX-Boosted, HX-History-Restore-Request' in response.headers['Access-Control-Allow-Headers']
    assert 'Content-Type, HX-Location, HX-Push-Url, HX-Redirect, HX-Refresh, HX-Retarget, HX-Reswap, HX-Trigger, HX-Trigger-After-Settle, HX-Trigger-After-Swap' in response.headers['Access-Control-Expose-Headers']
    assert response.headers['Access-Control-Allow-Credentials'] == 'true'
    assert response.headers['Access-Control-Max-Age'] == '86400'
    assert response.headers['Access-Control-Allow-Methods'] == 'GET,POST,OPTIONS'

    # Test newsletter.dctech.events origin
    response = test_client.http.get(
        '/',
        headers={'origin': 'https://newsletter.dctech.events'}
    )
    assert response.headers['Access-Control-Allow-Origin'] == 'https://newsletter.dctech.events'
    assert 'Content-Type, HX-Request, HX-Trigger, HX-Target, HX-Prompt, HX-Current-URL, HX-Boosted, HX-History-Restore-Request' in response.headers['Access-Control-Allow-Headers']
    assert 'Content-Type, HX-Location, HX-Push-Url, HX-Redirect, HX-Refresh, HX-Retarget, HX-Reswap, HX-Trigger, HX-Trigger-After-Settle, HX-Trigger-After-Swap' in response.headers['Access-Control-Expose-Headers']
    assert response.headers['Access-Control-Allow-Credentials'] == 'true'
    assert response.headers['Access-Control-Max-Age'] == '86400'
    assert response.headers['Access-Control-Allow-Methods'] == 'GET,POST,OPTIONS'

def test_cors_headers_not_present_for_other_origins(test_client):
    response = test_client.http.get(
        '/',
        headers={'origin': 'https://example.com'}
    )
    assert 'Access-Control-Allow-Origin' not in response.headers

def test_send_newsletter_basic_functionality(test_client, mock_ses):
    # Mock requests to prevent actual HTTP calls
    with patch('app.requests.get') as mock_get:
        mock_get.return_value.text = 'test content'
        
        # Mock list_contacts response
        mock_ses.list_contacts.return_value = {
            'Contacts': [
                {
                    'EmailAddress': 'test@example.com',
                    'TopicPreferences': [
                        {
                            'TopicName': 'dctech',
                            'SubscriptionStatus': 'OPT_IN'
                        }
                    ]
                }
            ]
        }
        
        # Test newsletter sending
        result = app.send_newsletter_to_subscribers()
        assert result['status'] == 'completed'
        assert result['successful_sends'] == 1
        assert result['failed_sends'] == 0
        assert mock_ses.send_email.call_count == 1
        
        # Verify email call
        mock_ses.send_email.assert_called_with(
            FromEmailAddress='outbound@dctech.events',
            ReplyToAddresses=['ross@karchner.com'],
            Destination={
                'ToAddresses': ['test@example.com']
            },
            Content={
                'Template': {
                    'TemplateName': 'dctech-newsletter',
                    'TemplateData': json.dumps({
                        'content': 'test content'
                    })
                }
            },
            ListManagementOptions={
                'ContactListName': 'newsletters',
                'TopicName': 'dctech'
            }
        )

def test_newsletter_scheduled_for_monday_6am_et():
    """Test that the newsletter is scheduled to run at 6am Eastern Time on Mondays"""
    from chalice.app import Chalice
    
    # Get the scheduled functions from the app
    scheduled_functions = []
    for route in app.routes:
        if route.startswith('schedule:'):
            scheduled_functions.append(app.routes[route])
    
    # Find our newsletter function
    newsletter_schedule = None
    for function in scheduled_functions:
        if function.handler_function.__name__ == 'scheduled_newsletter':
            newsletter_schedule = function
            break
    
    assert newsletter_schedule is not None
    # Check that it's using the correct cron expression for 6am ET Monday (11am UTC)
    assert newsletter_schedule.schedule_expression == 'cron(0 11 ? * MON *)'

def test_handle_bounce_notification(test_client, mock_ses):
    mock_ses.delete_contact = MagicMock()
    
    # Create a bounce notification event
    event = MagicMock()
    event.message = json.dumps({
        'notificationType': 'Bounce',
        'bounce': {
            'bounceType': 'Permanent',
            'bouncedRecipients': [{'emailAddress': 'test@example.com'}]
        }
    })
    
    app.handle_ses_notification(event)
    
    # Verify contact was deleted
    mock_ses.delete_contact.assert_called_once_with(
        ContactListName='newsletters',
        EmailAddress='test@example.com'
    )

def test_handle_complaint_notification(test_client, mock_ses):
    mock_ses.delete_contact = MagicMock()
    
    # Create a complaint notification event
    event = MagicMock()
    event.message = json.dumps({
        'notificationType': 'Complaint',
        'complaint': {
            'complainedRecipients': [{'emailAddress': 'test@example.com'}]
        }
    })
    
    app.handle_ses_notification(event)
    
    # Verify contact was deleted
    mock_ses.delete_contact.assert_called_once_with(
        ContactListName='newsletters',
        EmailAddress='test@example.com'
    )