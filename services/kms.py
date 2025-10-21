"""KMS service for signature generation and verification."""
from base64 import urlsafe_b64encode, urlsafe_b64decode
from services.aws_clients import AWSClients


class KMSService:
    """Service for KMS-based signatures."""
    
    def __init__(self, key_id: str):
        """Initialize with KMS key ID."""
        self.key_id = key_id
        self.kms = AWSClients.get_kms()
    
    def generate_confirmation_signature(self, email: str, contact_list_name: str, 
                                       topic_name: str, timestamp: int) -> str:
        """Generate a KMS HMAC signature for email confirmation."""
        message = f"{email}:{contact_list_name}:{topic_name}:{timestamp}".encode()
        
        response = self.kms.generate_mac(
            Message=message,
            KeyId=self.key_id,
            MacAlgorithm='HMAC_SHA_512'
        )
        return urlsafe_b64encode(response['Mac']).decode('utf-8').rstrip('=')
    
    def verify_confirmation_signature(self, email: str, contact_list_name: str,
                                     topic_name: str, timestamp: int, 
                                     signature: str) -> bool:
        """Verify a KMS HMAC signature for email confirmation."""
        try:
            message = f"{email}:{contact_list_name}:{topic_name}:{timestamp}".encode()
            
            # Pad the signature if needed
            padded_sig = signature + '=' * (-len(signature) % 4)
            mac_bytes = urlsafe_b64decode(padded_sig.encode())
            
            response = self.kms.verify_mac(
                Message=message,
                KeyId=self.key_id,
                MacAlgorithm='HMAC_SHA_512',
                Mac=mac_bytes
            )
            return response['MacValid']
        except Exception as e:
            print(f"Error verifying signature: {str(e)}")
            return False
