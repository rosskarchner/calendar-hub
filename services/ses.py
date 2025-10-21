"""SES service for sending emails."""
from services.aws_clients import AWSClients


class EmailService:
    """Service for sending emails via AWS SES."""
    
    @staticmethod
    def send_confirmation_email(to_email: str, from_email: str, 
                               site_name: str, confirmation_url: str, 
                               item_count: int = 1, item_type: str = 'events') -> None:
        """Send confirmation email to user."""
        ses = AWSClients.get_ses()
        
        subject = f'Complete your {site_name} submission'
        body = f'Please confirm your {item_type} submission ({item_count} {item_type}) by clicking this link: {confirmation_url}'
        
        ses.send_email(
            Source=from_email,
            Destination={'ToAddresses': [to_email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Text': {'Data': body}}
            }
        )
