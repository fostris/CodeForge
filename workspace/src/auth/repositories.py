import uuid
from typing import Optional, Protocol
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.auth.models import User, UserCreate
from src.auth.exceptions import DuplicateEmailError
from src.config import get_logger

logger = get_logger(__name__)


class UserRepository(Protocol):
    """Protocol defining the user repository interface."""
    
    def create(self, user_create: UserCreate, hashed_password: str) -> User:
        """Create a new user."""
        ...
    
    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID."""
        ...
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        ...
    
    def exists_by_email(self, email: str) -> bool:
        """Check if user exists by email."""
        ...


class UserRepositoryImpl:
    """SQLAlchemy implementation of UserRepository."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, user_create: UserCreate, hashed_password: str) -> User:
        """Create a new user."""
        # Check if email already exists
        if self.exists_by_email(user_create.email):
            logger.warning(f"Attempt to create user with duplicate email: {user_create.email}")
            raise DuplicateEmailError(f"Email {user_create.email} already exists")
        
        user = User(
            email=user_create.email,
            hashed_password=hashed_password
        )
        
        self.session.add(user)
        self.session.flush()  # Get the ID without committing
        logger.info(f"Created user with ID: {user.id}")
        return user
    
    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID."""
        stmt = select(User).where(User.id == user_id)
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        stmt = select(User).where(User.email == email)
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    def exists_by_email(self, email: str) -> bool:
        """Check if user exists by email."""
        stmt = select(User.id).where(User.email == email)
        result = self.session.execute(stmt)
        return result.first() is not None