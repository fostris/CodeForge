import pytest
from src.auth.services.password_service import PasswordService
import bcrypt


class TestPasswordService:
    """Test suite for PasswordService."""
    
    def test_init_default_cost(self):
        """Test initialization with default cost."""
        service = PasswordService()
        assert service.cost == 12
    
    def test_init_custom_cost(self):
        """Test initialization with custom cost."""
        service = PasswordService(cost=10)
        assert service.cost == 10
    
    def test_hash_password_returns_string(self):
        """Test that hash_password returns a string."""
        service = PasswordService()
        password = "test_password_123"
        
        hashed = service.hash_password(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0
    
    def test_hash_password_empty_password_raises_error(self):
        """Test that hash_password raises ValueError for empty password."""
        service = PasswordService()
        
        with pytest.raises(ValueError):
            service.hash_password("")
        
        with pytest.raises(ValueError):
            service.hash_password(None)  # type: ignore
    
    def test_verify_password_correct_password_returns_true(self):
        """Test that verify_password returns True for correct password."""
        service = PasswordService()
        password = "correct_password"
        
        hashed = service.hash_password(password)
        result = service.verify_password(password, hashed)
        
        assert result is True
    
    def test_verify_password_incorrect_password_returns_false(self):
        """Test that verify_password returns False for incorrect password."""
        service = PasswordService()
        correct_password = "correct_password"
        wrong_password = "wrong_password"
        
        hashed = service.hash_password(correct_password)
        result = service.verify_password(wrong_password, hashed)
        
        assert result is False
    
    def test_verify_password_empty_password_returns_false(self):
        """Test that verify_password returns False for empty password."""
        service = PasswordService()
        password = "some_password"
        
        hashed = service.hash_password(password)
        
        assert service.verify_password("", hashed) is False
        assert service.verify_password(None, hashed) is False  # type: ignore
    
    def test_verify_password_empty_hash_returns_false(self):
        """Test that verify_password returns False for empty hash."""
        service = PasswordService()
        password = "some_password"
        
        assert service.verify_password(password, "") is False
        assert service.verify_password(password, None) is False  # type: ignore
    
    def test_verify_password_invalid_hash_format_returns_false(self):
        """Test that verify_password returns False for invalid hash format."""
        service = PasswordService()
        password = "some_password"
        invalid_hash = "not_a_valid_bcrypt_hash"
        
        result = service.verify_password(password, invalid_hash)
        
        assert result is False
    
    def test_hash_password_uses_bcrypt_correctly(self):
        """Test that hash_password uses bcrypt correctly."""
        service = PasswordService(cost=4)  # Use lower cost for faster tests
        password = "test_password"
        
        hashed = service.hash_password(password)
        
        # Verify the hash is valid bcrypt
        password_bytes = password.encode('utf-8')
        hashed_bytes = hashed.encode('utf-8')
        
        # This should not raise an exception
        assert bcrypt.checkpw(password_bytes, hashed_bytes)
    
    def test_different_passwords_produce_different_hashes(self):
        """Test that different passwords produce different hashes."""
        service = PasswordService()
        password1 = "password1"
        password2 = "password2"
        
        hash1 = service.hash_password(password1)
        hash2 = service.hash_password(password2)
        
        assert hash1 != hash2
    
    def test_same_password_produces_different_hashes_due_to_salt(self):
        """Test that same password produces different hashes due to salt."""
        service = PasswordService()
        password = "same_password"
        
        hash1 = service.hash_password(password)
        hash2 = service.hash_password(password)
        
        # Hashes should be different due to different salts
        assert hash1 != hash2
        
        # But both should verify correctly
        assert service.verify_password(password, hash1) is True
        assert service.verify_password(password, hash2) is True
    
    def test_verify_with_externally_generated_hash(self):
        """Test verification with a hash generated outside the service."""
        password = "external_test"
        password_bytes = password.encode('utf-8')
        
        # Generate hash directly with bcrypt
        salt = bcrypt.gensalt(rounds=12)
        external_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
        
        service = PasswordService()
        
        # Should verify correctly
        assert service.verify_password(password, external_hash) is True
        assert service.verify_password("wrong", external_hash) is False