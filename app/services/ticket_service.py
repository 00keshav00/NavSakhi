import time
import secrets
import logging
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class WebSocketTicket:
    ticket: str
    user_id: str
    created_at: float
    expires_at: float
    used: bool = False

class WebSocketTicketService:
    """
    Manages short-lived, single-use tickets for authenticating WebSocket connections.
    Avoids putting long-lived JWTs into WebSocket URLs while ensuring the browser
    WebSocket client can authenticate reliably without custom headers.
    """
    def __init__(self, ticket_ttl_seconds: int = 60):
        self.ticket_ttl = ticket_ttl_seconds
        self._tickets: Dict[str, WebSocketTicket] = {}

    def issue_ticket(self, user_id: str) -> str:
        """Issue a short-lived, single-use ticket bound to a user ID."""
        now = time.time()
        self._cleanup_expired(now)
        
        ticket_id = secrets.token_urlsafe(32)
        ticket = WebSocketTicket(
            ticket=ticket_id,
            user_id=str(user_id),
            created_at=now,
            expires_at=now + self.ticket_ttl,
            used=False
        )
        self._tickets[ticket_id] = ticket
        return ticket_id

    def consume_ticket(self, ticket_id: Optional[str]) -> Optional[str]:
        """
        Atomically validate and consume a ticket.
        Returns the user_id if the ticket is valid, active, and unused.
        Returns None if missing, expired, invalid, or replayed.
        """
        if not ticket_id:
            return None
        
        now = time.time()
        ticket = self._tickets.pop(ticket_id, None)
        if not ticket:
            logger.warning("WebSocket ticket rejected: ticket not found or already consumed.")
            return None
        
        if ticket.used:
            logger.warning("WebSocket ticket rejected: replay attempt detected.")
            return None
        
        if now > ticket.expires_at:
            logger.warning("WebSocket ticket rejected: ticket has expired.")
            return None

        # Mark used and return user_id
        ticket.used = True
        return ticket.user_id

    def _cleanup_expired(self, now: float) -> None:
        """Purge expired tickets from memory to prevent unbounded memory growth."""
        expired_keys = [k for k, v in self._tickets.items() if now > v.expires_at]
        for k in expired_keys:
            self._tickets.pop(k, None)

    def clear(self) -> None:
        """Clear all tickets (useful for isolated unit testing)."""
        self._tickets.clear()

ticket_service = WebSocketTicketService(ticket_ttl_seconds=60)
