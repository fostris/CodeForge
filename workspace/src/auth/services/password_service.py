import bcrypt
from typing import Optional


class PasswordService:
    """Service for password hashing and verification using bcrypt."""
    
    def __init__(self, cost: int = 12):
        """Initialize password service with bcrypt cost factor.
        
        Args:
            cost: The bcrypt cost factor (default: 12)
        """
        self.cost = cost
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt.
        
        Args:
            password: The plain text password to hash
            
        Returns:
            The hashed password as a string
        """
        if not password:
            raise ValueError("Password cannot be empty")
        
        # Encode password to bytes
        password_bytes = password.encode('utf-8')
        
        # Generate salt and hash password
        salt = bcrypt.gensalt(rounds=self.cost)
        hashed_bytes = bcrypt.hashpw(password_bytes, salt)
        
        # Return as string
        return hashed_bytes.decode('utf-8')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against a hashed password.
        
        Args:
            plain_password: The plain text password to verify
            hashed_password: The hashed password to compare against
            
        Returns:
            True if password matches, False otherwise
        """
        if not plain_password or not hashed_password:
            return False
        
        try:
            # Encode both to bytes
            plain_bytes = plain_password.encode('utf-8')
            hashed_bytes = hashed_password.encode('utf-8')
            
            # Verify password
            return bcrypt.checkpw(plain_bytes, hashed_bytes)
        except (ValueError, UnicodeEncodeError):
            # Handle invalid inputs
            return False