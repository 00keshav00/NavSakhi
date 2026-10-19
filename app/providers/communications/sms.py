import logging
from typing import List

logger = logging.getLogger(__name__)

class SMSProvider:
    """Stub for SMS integration (e.g., Twilio)"""
    def __init__(self):
        pass

    async def send_emergency_sms(self, contacts: List[str], message: str) -> bool:
        """
        Simulates sending an SMS to the provided contacts.
        """
        for contact in contacts:
            logger.info(f"[SMS Provider] Sending to {contact}: {message}")
            print(f"🚨 [SMS DISPATCHED to {contact}]: {message}")
        return True
