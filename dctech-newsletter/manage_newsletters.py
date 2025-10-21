#!/usr/bin/env python3
"""
CLI script to manage newsletters in AWS SES
"""
import boto3
import argparse
import sys
import logging
from newsletter_config import get_all_newsletters, get_newsletter_by_slug
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NewsletterManager:
    def __init__(self):
        self.ses = boto3.client('sesv2')

    def create_contact_list(self, newsletter_config):
        """Create or update a contact list for a newsletter"""
        contact_list_name = newsletter_config['contact_list_name']
        
        try:
            # Check if contact list exists
            self.ses.get_contact_list(ContactListName=contact_list_name)
            logger.info(f"Contact list '{contact_list_name}' already exists")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'NotFoundException':
                # Create the contact list
                try:
                    self.ses.create_contact_list(
                        ContactListName=contact_list_name,
                        Description=f"Subscribers for {newsletter_config['name']}",
                        Topics=[
                            {
                                'TopicName': newsletter_config['topic_name'],
                                'DisplayName': newsletter_config['name'],
                                'Description': newsletter_config['description'],
                                'DefaultSubscriptionStatus': 'OPT_IN'
                            }
                        ]
                    )
                    logger.info(f"Created contact list '{contact_list_name}'")
                    return True
                except ClientError as e:
                    logger.error(f"Failed to create contact list '{contact_list_name}': {e}")
                    return False
            else:
                logger.error(f"Error checking contact list '{contact_list_name}': {e}")
                return False

    def create_email_template(self, newsletter_config):
        """Create or update an email template for a newsletter"""
        template_name = newsletter_config['template_name']
        
        template_content = {
            "Subject": newsletter_config['subject'],
            "Html": "{{content}}<br><br>You received this email because you subscribed to " + newsletter_config['name'] + ". To unsubscribe, click {{amazonSESUnsubscribeUrl}}",
            "Text": "{{content}}\n\nYou received this email because you subscribed to " + newsletter_config['name'] + ". To unsubscribe, visit: {{amazonSESUnsubscribeUrl}}"
        }
        
        try:
            # Check if template exists
            self.ses.get_email_template(TemplateName=template_name)
            # Update existing template
            self.ses.update_email_template(
                TemplateName=template_name,
                TemplateContent=template_content
            )
            logger.info(f"Updated email template '{template_name}'")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'NotFoundException':
                # Create new template
                try:
                    self.ses.create_email_template(
                        TemplateName=template_name,
                        TemplateContent=template_content
                    )
                    logger.info(f"Created email template '{template_name}'")
                    return True
                except ClientError as e:
                    logger.error(f"Failed to create email template '{template_name}': {e}")
                    return False
            else:
                logger.error(f"Error checking email template '{template_name}': {e}")
                return False

    def setup_newsletter(self, slug):
        """Set up a newsletter in AWS SES"""
        newsletter_config = get_newsletter_by_slug(slug)
        if not newsletter_config:
            logger.error(f"Newsletter '{slug}' not found in configuration")
            return False

        logger.info(f"Setting up newsletter '{slug}' ({newsletter_config['name']})")
        
        # Create contact list
        if not self.create_contact_list(newsletter_config):
            return False
        
        # Create email template
        if not self.create_email_template(newsletter_config):
            return False
        
        logger.info(f"Successfully set up newsletter '{slug}'")
        return True

    def setup_all_newsletters(self):
        """Set up all newsletters in AWS SES"""
        newsletters = get_all_newsletters()
        success_count = 0
        
        for slug, config in newsletters.items():
            if self.setup_newsletter(slug):
                success_count += 1
        
        logger.info(f"Successfully set up {success_count}/{len(newsletters)} newsletters")
        return success_count == len(newsletters)

    def list_newsletters(self):
        """List all configured newsletters"""
        newsletters = get_all_newsletters()
        
        print("\nConfigured Newsletters:")
        print("-" * 50)
        for slug, config in newsletters.items():
            print(f"Slug: {slug}")
            print(f"Name: {config['name']}")
            print(f"Description: {config['description']}")
            print(f"Contact List: {config['contact_list_name']}")
            print(f"Topic: {config['topic_name']}")
            print(f"Template: {config['template_name']}")
            print("-" * 50)

def main():
    parser = argparse.ArgumentParser(description='Manage newsletters in AWS SES')
    parser.add_argument('action', choices=['setup', 'setup-all', 'list'], 
                       help='Action to perform')
    parser.add_argument('--slug', help='Newsletter slug (required for setup action)')
    
    args = parser.parse_args()
    
    manager = NewsletterManager()
    
    if args.action == 'setup':
        if not args.slug:
            logger.error("--slug is required for setup action")
            sys.exit(1)
        success = manager.setup_newsletter(args.slug)
        sys.exit(0 if success else 1)
    
    elif args.action == 'setup-all':
        success = manager.setup_all_newsletters()
        sys.exit(0 if success else 1)
    
    elif args.action == 'list':
        manager.list_newsletters()
        sys.exit(0)

if __name__ == "__main__":
    main()