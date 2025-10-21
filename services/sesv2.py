"""SESv2 service for newsletter management."""
from services.aws_clients import AWSClients
from botocore.exceptions import ClientError


class NewsletterService:
    """Service for managing newsletter subscriptions via SESv2."""
    
    @staticmethod
    def send_confirmation_email(to_email: str, from_email: str, reply_to: str,
                               confirmation_url: str, subject: str, html_content: str) -> None:
        """Send confirmation email to subscriber."""
        sesv2 = AWSClients.get_sesv2()
        
        sesv2.send_email(
            FromEmailAddress=from_email,
            ReplyToAddresses=[reply_to],
            Destination={'ToAddresses': [to_email]},
            Content={
                'Simple': {
                    'Subject': {'Data': subject},
                    'Body': {'Html': {'Data': html_content}}
                }
            }
        )
    
    @staticmethod
    def create_or_update_contact(contact_list_name: str, email: str, 
                                 topic_name: str) -> None:
        """Create or update a contact in SES contact list with topic subscription."""
        sesv2 = AWSClients.get_sesv2()
        
        try:
            sesv2.create_contact(
                ContactListName=contact_list_name,
                EmailAddress=email,
                TopicPreferences=[
                    {
                        'TopicName': topic_name,
                        'SubscriptionStatus': 'OPT_IN'
                    }
                ]
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'AlreadyExistsException':
                # Contact exists, get current preferences
                contact = sesv2.get_contact(
                    ContactListName=contact_list_name,
                    EmailAddress=email
                )
                
                existing_preferences = contact['TopicPreferences']
                
                # Update or add the topic preference
                topic_found = False
                for pref in existing_preferences:
                    if pref['TopicName'] == topic_name:
                        pref['SubscriptionStatus'] = 'OPT_IN'
                        topic_found = True
                        break
                
                if not topic_found:
                    existing_preferences.append({
                        'TopicName': topic_name,
                        'SubscriptionStatus': 'OPT_IN'
                    })
                
                # Update contact
                sesv2.update_contact(
                    ContactListName=contact_list_name,
                    EmailAddress=email,
                    TopicPreferences=existing_preferences
                )
            else:
                raise
    
    @staticmethod
    def unsubscribe_contact(contact_list_name: str, email: str, 
                           topic_name: str) -> None:
        """Unsubscribe a contact from a specific topic."""
        sesv2 = AWSClients.get_sesv2()
        
        try:
            contact = sesv2.get_contact(
                ContactListName=contact_list_name,
                EmailAddress=email
            )
            
            existing_preferences = contact['TopicPreferences']
            
            # Update the topic preference to OPT_OUT
            for pref in existing_preferences:
                if pref['TopicName'] == topic_name:
                    pref['SubscriptionStatus'] = 'OPT_OUT'
                    break
            
            sesv2.update_contact(
                ContactListName=contact_list_name,
                EmailAddress=email,
                TopicPreferences=existing_preferences
            )
        except ClientError as e:
            print(f"Error unsubscribing contact: {str(e)}")
            raise
