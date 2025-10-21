#!/usr/bin/env python3
import boto3
import json
import sys
import logging
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set to True for verbose logging
DEBUG = False

if DEBUG:
    logging.basicConfig(level=logging.DEBUG)
    boto3.set_stream_logger('', logging.DEBUG)

class SESSetup:
    def __init__(self):
        self.ses_client = boto3.client('sesv2')
        self.contact_list_name = "newsletters"
        self.template_name = "dctech-newsletter"
        self.configuration_set_name = "dctech-events"
        self.template_content = {
            "Subject": "DC Tech Events Weekly",
            "Html": "{{content}}<br><br>You received this email because you subscribed to DC Tech Events Weekly. "
            "To unsubscribe, click <a href=\"{{amazonSESUnsubscribeUrl}}\">here</a>.",
            "Text": "{{content}}\n\nYou received this email because you subscribed to DC Tech Events Weekly. To unsubscribe, click here {{amazonSESUnsubscribeUrl}}"
 #            "Html": "{{content}}<br><br>You received this email because you subscribed to DC Tech Events Weekly. To unsubscribe, click",
 #           "Text": "{{content}}\n\nYou received this email because you subscribed to DC Tech Events Weekly. To unsubscribe, click "
        }


    def check_contact_list_exists(self, list_name):
        """Check if a contact list exists"""
        try:
            self.ses_client.get_contact_list(ContactListName=list_name)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'NotFoundException':
                return False
            raise

    def check_template_exists(self, template_name):
        """Check if an email template exists"""
        try:
            self.ses_client.get_email_template(TemplateName=template_name)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'NotFoundException':
                return False
            raise

    def check_contact_exists(self, list_name, email):
        """Check if a contact exists in a list"""
        try:
            self.ses_client.get_contact(ContactListName=list_name, EmailAddress=email)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'NotFoundException':
                return False
            raise

    def check_sending_quota(self):
        """Check SES sending quota"""
        try:
            quota = self.ses_client.get_account()
            send_quota = quota.get('SendQuota', {})
            logger.info(f"SES Sending Quota: {send_quota}")
            
            # Check if you've hit your sending limits
            max_send = send_quota.get('Max24HourSend', 0)
            sent = send_quota.get('SentLast24Hours', 0)
            
            if max_send <= sent:
                logger.error(f"You've reached your sending limit: {sent}/{max_send}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error checking quota: {e}")
            return False

    def check_sending_activity(self):
        """Check recent sending activity"""
        try:
            # Get sending statistics
            stats = self.ses_client.get_account()
            logger.info(f"SES Sending Statistics: {json.dumps(stats.get('SendingStatistics', {}), default=str)}")
            return True
        except Exception as e:
            logger.error(f"Error checking sending activity: {e}")
            return False

    def check_suppression_list(self, email):
        """Check if email is on the suppression list"""
        try:
            response = self.ses_client.get_suppressed_destination(EmailAddress=email)
            logger.error(f"Email {email} is on the suppression list: {response}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'NotFoundException':
                logger.info(f"Email {email} is not on the suppression list")
                return False
            logger.error(f"Error checking suppression list: {e}")
            return False

    def setup_contact_list(self):
        """Create or update SES contact list"""
        topics = [
            {
                "TopicName": "dctech",
                "DisplayName": "DC Tech Events Weekly",
                "Description": "Weekly newsletter about DC tech events",
                "DefaultSubscriptionStatus": "OPT_IN"
            },
        ]

        if self.check_contact_list_exists(self.contact_list_name):
            logger.info(f"Contact list '{self.contact_list_name}' already exists. Updating topics...")
            self.ses_client.update_contact_list(
                ContactListName=self.contact_list_name,
                Description="DCTech Events Newsletter Subscribers",
                Topics=topics
            )
        else:
            logger.info(f"Creating contact list '{self.contact_list_name}'...")
            self.ses_client.create_contact_list(
                ContactListName=self.contact_list_name,
                Description="DCTech Events Newsletter Subscribers",
                Topics=topics
            )

    def setup_email_template(self):
        """Create or update SES email template"""
        if self.check_template_exists(self.template_name):
            logger.info(f"Email template '{self.template_name}' already exists. Updating...")
            self.ses_client.update_email_template(
                TemplateName=self.template_name,
                TemplateContent=self.template_content
            )
        else:
            logger.info(f"Creating email template '{self.template_name}'...")
            self.ses_client.create_email_template(
                TemplateName=self.template_name,
                TemplateContent=self.template_content
            )

    def check_configuration_set_exists(self):
        """Check if a configuration set exists"""
        try:
            self.ses_client.get_configuration_set(ConfigurationSetName=self.configuration_set_name)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'NotFoundException':
                return False
            raise

    def setup_configuration_set(self):
        """Create or update SES configuration set"""
        if self.check_configuration_set_exists():
            logger.info(f"Configuration set '{self.configuration_set_name}' already exists.")
            return

        logger.info(f"Creating configuration set '{self.configuration_set_name}'...")
        try:
            self.ses_client.create_configuration_set(
                ConfigurationSetName=self.configuration_set_name,
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
            logger.info(f"Configuration set '{self.configuration_set_name}' created successfully.")
        except ClientError as e:
            logger.error(f"Failed to create configuration set: {e}")
            raise

    def is_in_sandbox_mode(self):
        """Check if SES is in sandbox mode"""
        account_details = self.ses_client.get_account()
        return account_details.get('ProductionAccessEnabled', True) is False

    def verify_email_identity(self, email):
        """Verify an email identity"""
        try:
            identity = self.ses_client.get_email_identity(EmailIdentity=email)
            logger.info(f"Email {email} verification status: {identity.get('VerificationStatus')}")
            return identity.get('VerificationStatus') == 'SUCCESS'
        except ClientError as e:
            if e.response['Error']['Code'] == 'NotFoundException':
                logger.info(f"Email {email} is not verified. Verifying...")
                self.ses_client.create_email_identity(EmailIdentity=email)
                logger.info(f"Verification email sent to {email}. Please verify before continuing.")
                return False
            logger.error(f"Error verifying email: {e}")
            return False

def main():
    setup = SESSetup()
    
    # Set up the contact list, email template and configuration set
    setup.setup_contact_list()
    setup.setup_email_template()
    setup.setup_configuration_set()

if __name__ == "__main__":
    main()