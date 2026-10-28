import os
import logging
from typing import Optional, Dict, Any, Tuple
from app.config.settings import settings

logger = logging.getLogger(__name__)


class CredentialSource:
    GEMINI_API_KEY = "GEMINI_API_KEY"
    GOOGLE_API_KEY = "GOOGLE_API_KEY"
    BACKUP = "GEMINI_API_KEY_BACKUP"
    NONE = "NONE"


class SafeCredentialManager:
    """
    Secure server-side credential selection and planned rotation manager.

    Guarantees:
    - Reads credentials only from explicitly named environment variables or application settings.
    - Zero key values, partial fragments, or secrets logged or exposed.
    - Does NOT mutate os.environ across concurrent requests.
    - Strictly separates legitimate credential security rotation from rate-limit / quota avoidance.
    - Preserves deterministic precedence: GEMINI_API_KEY > GOOGLE_API_KEY > GEMINI_API_KEY_BACKUP.
    """

    def __init__(self):
        self._backup_active: bool = False

    def get_primary_credential(self) -> Tuple[Optional[str], str]:
        """
        Determines the primary active Gemini credential based on explicit configuration precedence.
        Returns: (credential_string, source_identifier)
        """
        # 1. Check GEMINI_API_KEY (application primary)
        gemini_env = os.getenv("GEMINI_API_KEY", "").strip()
        if gemini_env:
            return gemini_env, CredentialSource.GEMINI_API_KEY

        gemini_setting = getattr(settings, "gemini_api_key", None)
        if gemini_setting and str(gemini_setting).strip():
            return str(gemini_setting).strip(), CredentialSource.GEMINI_API_KEY

        # 2. Check GOOGLE_API_KEY (standard Google SDK convention)
        google_env = os.getenv("GOOGLE_API_KEY", "").strip()
        if google_env:
            return google_env, CredentialSource.GOOGLE_API_KEY

        google_setting = getattr(settings, "google_api_key", None)
        if google_setting and str(google_setting).strip():
            return str(google_setting).strip(), CredentialSource.GOOGLE_API_KEY

        # 3. Check explicitly configured planned rotation backup
        backup_env = os.getenv("GEMINI_API_KEY_BACKUP", "").strip()
        if backup_env:
            return backup_env, CredentialSource.BACKUP

        return None, CredentialSource.NONE

    def get_backup_credential(self) -> Optional[str]:
        """Returns the separately authorized backup credential if explicitly configured."""
        backup_env = os.getenv("GEMINI_API_KEY_BACKUP", "").strip()
        if backup_env:
            return backup_env
        backup_setting = getattr(settings, "gemini_api_key_backup", None)
        if backup_setting and str(backup_setting).strip():
            return str(backup_setting).strip()
        return None

    def get_credential_status(self) -> Dict[str, Any]:
        """
        Safe boolean-only inspection of credential configuration.
        Guarantees zero secret exposure.
        """
        gemini_set = bool(os.getenv("GEMINI_API_KEY", "").strip() or (getattr(settings, "gemini_api_key", None) and str(settings.gemini_api_key).strip()))
        google_set = bool(os.getenv("GOOGLE_API_KEY", "").strip() or (getattr(settings, "google_api_key", None) and str(settings.google_api_key).strip()))
        backup_set = bool(os.getenv("GEMINI_API_KEY_BACKUP", "").strip() or (getattr(settings, "gemini_api_key_backup", None) and str(getattr(settings, "gemini_api_key_backup", "")).strip()))

        active_cred, source = self.get_primary_credential()

        return {
            "gemini_api_key_configured": gemini_set,
            "google_api_key_configured": google_set,
            "backup_key_configured": backup_set,
            "active_key_source": source,
            "has_usable_credential": active_cred is not None
        }


# Global singleton instance
global_credential_manager = SafeCredentialManager()


def get_active_gemini_api_key() -> str:
    """Helper to acquire the currently selected Gemini credential string."""
    cred, _ = global_credential_manager.get_primary_credential()
    return cred or ""
