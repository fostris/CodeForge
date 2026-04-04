import bcrypt


def hash_password(password: bytes) -> bytes:
    """Hash a password using bcrypt with cost factor 12."""
    salt = bcrypt.gensalt(12)
    hashed = bcrypt.hashpw(password, salt)
    return hashed


def verify_password(password: bytes, hashed_password: bytes) -> bool:
    """Verify a password against a hashed password using bcrypt."""
    return bcrypt.checkpw(password, hashed_password)