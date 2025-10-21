"""DynamoDB service for submissions."""
from datetime import datetime
from services.aws_clients import AWSClients


class SubmissionsService:
    """Service for managing event submissions in DynamoDB."""
    
    def __init__(self, table_name: str):
        """Initialize with table name."""
        self.table_name = table_name
        self._table = None
    
    @property
    def table(self):
        """Lazy load DynamoDB table."""
        if self._table is None:
            dynamodb = AWSClients.get_dynamodb()
            self._table = dynamodb.Table(self.table_name)
        return self._table
    
    def create_submission(self, submission_id: str, submission_type: str, 
                         site_slug: str, email: str, data: dict) -> None:
        """Create a new submission in DynamoDB."""
        self.table.put_item(
            Item={
                'submission_id': submission_id,
                'status': 'pending',
                'type': submission_type,
                'site_slug': site_slug,
                'email': email,
                'data': data,
                'created_at': datetime.utcnow().isoformat(),
                'confirmation_sent': False
            }
        )
    
    def get_submission(self, submission_id: str) -> dict:
        """Get submission by ID."""
        response = self.table.get_item(Key={'submission_id': submission_id})
        return response.get('Item')
    
    def update_submission_status(self, submission_id: str, status: str, pr_url: str = None) -> None:
        """Update submission status and optionally store PR URL."""
        update_expression = 'SET #status = :status'
        expression_attribute_names = {'#status': 'status'}
        expression_attribute_values = {':status': status}
        
        if pr_url:
            update_expression += ', pr_url = :pr_url'
            expression_attribute_values[':pr_url'] = pr_url
        
        self.table.update_item(
            Key={'submission_id': submission_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )
