import pytest
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, patch
import sys
import json
sys.path.append('.')
from setup_ses import SESSetup

@pytest.fixture
def ses_setup():
    return SESSetup()

@pytest.fixture
def mock_ses_client():
    with patch('boto3.client') as mock_client:
        mock_ses = MagicMock()
        mock_client.return_value = mock_ses
        yield mock_ses

def test_check_contact_list_exists_true(ses_setup, mock_ses_client):
    mock_ses_client.get_contact_list.return_value = {}
    assert ses_setup.check_contact_list_exists("test-list") is True

def test_check_contact_list_exists_false(ses_setup, mock_ses_client):
    mock_ses_client.get_contact_list.side_effect = ClientError(
        {'Error': {'Code': 'NotFoundException', 'Message': 'Not found'}},
        'GetContactList'
    )
    assert ses_setup.check_contact_list_exists("test-list") is False

def test_check_template_exists_true(ses_setup, mock_ses_client):
    mock_ses_client.get_email_template.return_value = {}
    assert ses_setup.check_template_exists("test-template") is True

def test_check_template_exists_false(ses_setup, mock_ses_client):
    mock_ses_client.get_email_template.side_effect = ClientError(
        {'Error': {'Code': 'NotFoundException', 'Message': 'Not found'}},
        'GetEmailTemplate'
    )
    assert ses_setup.check_template_exists("test-template") is False

def test_check_contact_exists_true(ses_setup, mock_ses_client):
    mock_ses_client.get_contact.return_value = {}
    assert ses_setup.check_contact_exists("test-list", "test@example.com") is True

def test_check_contact_exists_false(ses_setup, mock_ses_client):
    mock_ses_client.get_contact.side_effect = ClientError(
        {'Error': {'Code': 'NotFoundException', 'Message': 'Not found'}},
        'GetContact'
    )
    assert ses_setup.check_contact_exists("test-list", "test@example.com") is False

def test_setup_contact_list_new(ses_setup, mock_ses_client):
    mock_ses_client.get_contact_list.side_effect = ClientError(
        {'Error': {'Code': 'NotFoundException', 'Message': 'Not found'}},
        'GetContactList'
    )
    ses_setup.setup_contact_list()
    mock_ses_client.create_contact_list.assert_called_once_with(
        ContactListName=ses_setup.contact_list_name,
        Description="DCTech Events Newsletter Subscribers",
        Topics=[
            {
                "TopicName": "dctech",
                "DisplayName": "DC Tech Events Weekly",
                "Description": "Weekly newsletter about DC tech events",
                "DefaultSubscriptionStatus": "OPT_IN"
            },
            {
                "TopicName": "test",
                "DisplayName": "DC Tech Events Test",
                "Description": "Test messages for DC tech events",
                "DefaultSubscriptionStatus": "OPT_IN"
            }
        ]
    )

def test_setup_contact_list_existing(ses_setup, mock_ses_client):
    mock_ses_client.get_contact_list.return_value = {}
    ses_setup.setup_contact_list()
    mock_ses_client.update_contact_list.assert_called_once_with(
        ContactListName=ses_setup.contact_list_name,
        Description="DCTech Events Newsletter Subscribers",
        Topics=[
            {
                "TopicName": "dctech",
                "DisplayName": "DC Tech Events Weekly",
                "Description": "Weekly newsletter about DC tech events",
                "DefaultSubscriptionStatus": "OPT_IN"
            },
            {
                "TopicName": "test",
                "DisplayName": "DC Tech Events Test",
                "Description": "Test messages for DC tech events",
                "DefaultSubscriptionStatus": "OPT_IN"
            }
        ]
    )

def test_setup_email_template_new(ses_setup, mock_ses_client):
    mock_ses_client.get_email_template.side_effect = ClientError(
        {'Error': {'Code': 'NotFoundException', 'Message': 'Not found'}},
        'GetEmailTemplate'
    )
    ses_setup.setup_email_template()
    mock_ses_client.create_email_template.assert_called_once()

def test_setup_email_template_existing(ses_setup, mock_ses_client):
    mock_ses_client.get_email_template.return_value = {}
    ses_setup.setup_email_template()
    mock_ses_client.update_email_template.assert_called_once()

def test_is_in_sandbox_mode_true(ses_setup, mock_ses_client):
    mock_ses_client.get_account.return_value = {'ProductionAccessEnabled': False}
    assert ses_setup.is_in_sandbox_mode() is True

def test_is_in_sandbox_mode_false(ses_setup, mock_ses_client):
    mock_ses_client.get_account.return_value = {'ProductionAccessEnabled': True}
    assert ses_setup.is_in_sandbox_mode() is False

def test_verify_email_identity_already_verified(ses_setup, mock_ses_client):
    mock_ses_client.get_email_identity.return_value = {}
    assert ses_setup.verify_email_identity("test@example.com") is True
    mock_ses_client.create_email_identity.assert_not_called()

def test_verify_email_identity_new(ses_setup, mock_ses_client):
    mock_ses_client.get_email_identity.side_effect = ClientError(
        {'Error': {'Code': 'NotFoundException', 'Message': 'Not found'}},
        'GetEmailIdentity'
    )
    assert ses_setup.verify_email_identity("test@example.com") is False
    mock_ses_client.create_email_identity.assert_called_once_with(EmailIdentity="test@example.com")

def test_check_configuration_set_exists_true(ses_setup, mock_ses_client):
    mock_ses_client.get_configuration_set.return_value = {}
    assert ses_setup.check_configuration_set_exists() is True

def test_check_configuration_set_exists_false(ses_setup, mock_ses_client):
    mock_ses_client.get_configuration_set.side_effect = ClientError(
        {'Error': {'Code': 'NotFoundException', 'Message': 'Not found'}},
        'GetConfigurationSet'
    )
    assert ses_setup.check_configuration_set_exists() is False

def test_setup_configuration_set_new(ses_setup, mock_ses_client):
    # Mock that configuration set doesn't exist
    mock_ses_client.get_configuration_set.side_effect = ClientError(
        {'Error': {'Code': 'NotFoundException', 'Message': 'Not found'}},
        'GetConfigurationSet'
    )
    
    # Call the method
    ses_setup.setup_configuration_set()
    
    # Verify create_configuration_set was called with correct parameters
    mock_ses_client.create_configuration_set.assert_called_once_with(
        ConfigurationSetName=ses_setup.configuration_set_name,
        SendingOptions={
            'SendingEnabled': True
        },
        ReputationOptions={
            'ReputationMetricsEnabled': True
        },
        TrackingOptions={
            'CustomRedirectDomain': 'dctech.events'
        }
    )

def test_setup_configuration_set_existing(ses_setup, mock_ses_client):
    # Mock that configuration set exists
    mock_ses_client.get_configuration_set.return_value = {}
    
    # Call the method
    ses_setup.setup_configuration_set()
    
    # Verify create_configuration_set was not called
    mock_ses_client.create_configuration_set.assert_not_called()

