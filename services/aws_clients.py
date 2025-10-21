"""AWS client initialization and configuration."""
import boto3
from botocore.exceptions import ClientError


class AWSClients:
    """Singleton for AWS service clients."""
    
    _dynamodb = None
    _ses = None
    _sesv2 = None
    _kms = None
    _secrets = None
    
    @classmethod
    def get_dynamodb(cls):
        """Get DynamoDB resource."""
        if cls._dynamodb is None:
            cls._dynamodb = boto3.resource('dynamodb')
        return cls._dynamodb
    
    @classmethod
    def get_ses(cls):
        """Get SES client."""
        if cls._ses is None:
            cls._ses = boto3.client('ses')
        return cls._ses
    
    @classmethod
    def get_sesv2(cls):
        """Get SESv2 client."""
        if cls._sesv2 is None:
            cls._sesv2 = boto3.client('sesv2')
        return cls._sesv2
    
    @classmethod
    def get_kms(cls):
        """Get KMS client."""
        if cls._kms is None:
            cls._kms = boto3.client('kms')
        return cls._kms
    
    @classmethod
    def get_secrets_manager(cls):
        """Get Secrets Manager client."""
        if cls._secrets is None:
            cls._secrets = boto3.client('secretsmanager')
        return cls._secrets


def get_secret(secret_name):
    """Fetch a secret from AWS Secrets Manager."""
    client = AWSClients.get_secrets_manager()
    try:
        response = client.get_secret_value(SecretId=secret_name)
        if 'SecretString' in response:
            return response['SecretString']
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == 'AccessDeniedException':
            print(f"Access denied to secret {secret_name}. Please check IAM permissions.")
        else:
            print(f"Error fetching secret {secret_name}: {str(e)}")
        raise
    except Exception as e:
        print(f"Error fetching secret {secret_name}: {str(e)}")
        raise
