import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from app.config.settings import settings
from app.config.logging_config import logger
from app.api.exceptions import UnauthorizedException
from app.models.user import User
from app.repositories.user_repository import UserRepository

# Pre-computed dummy hash to mitigate timing attacks when a user is not found
_DUMMY_BCRYPT_HASH = "$2b$12$e8rXpB6iC4q1.FzFk9m7xOd28L5LzP7U0qXJpZ12yZ1eZ2iZ3aZ4a"

class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plaintext password using bcrypt."""
        if not password:
            raise ValueError("Password cannot be empty.")
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, stored_hash: str) -> bool:
        """Verify a plaintext password against a stored bcrypt hash."""
        if not plain_password or not stored_hash:
            return False
        
        # Verify valid bcrypt prefix
        if not (stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$") or stored_hash.startswith("$2y$")):
            logger.warning("Authentication failed: Stored hash is not in bcrypt format.")
            return False

        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), stored_hash.encode("utf-8"))
        except (ValueError, TypeError) as exc:
            logger.warning("Authentication failed during bcrypt check: invalid hash structure.")
            return False

    @staticmethod
    def create_access_token(user_id: str, email: str, expires_delta: Optional[timedelta] = None) -> str:
        """Generate a signed, expiring JWT access token."""
        now = datetime.now(timezone.utc)
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=settings.jwt_expiration_minutes)

        payload: Dict[str, Any] = {
            "sub": str(user_id),
            "email": email,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp())
        }

        secret = settings.effective_jwt_secret
        token = jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)
        return token

    @staticmethod
    def decode_access_token(token: str) -> Dict[str, Any]:
        """Decode and validate a JWT access token signature and expiration."""
        secret = settings.effective_jwt_secret
        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=[settings.jwt_algorithm],
                options={"require": ["sub", "exp", "iat"]}
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise UnauthorizedException("Authentication token has expired.")
        except jwt.InvalidTokenError:
            raise UnauthorizedException("Invalid authentication token.")

    @classmethod
    async def authenticate_user(cls, user_repo: UserRepository, email: str, password: str) -> User:
        """Authenticate user by email and password without disclosing account existence."""
        user = await user_repo.get_by_email(email)
        if not user:
            # Timing attack mitigation: perform dummy checkpw calculation
            try:
                bcrypt.checkpw(password.encode("utf-8"), _DUMMY_BCRYPT_HASH.encode("utf-8"))
            except Exception:
                pass
            raise UnauthorizedException("Invalid email or password.")

        if not cls.verify_password(password, user.password_hash):
            raise UnauthorizedException("Invalid email or password.")

        if not getattr(user, "is_active", True):
            raise UnauthorizedException("Account has been deactivated.")

        return user
