"""
Test suite for Phase 51.97: Journey WebSocket Transport and Dependency Integrity.
Verifies that:
1. The 'websockets' library is installed and importable in python environment.
2. 'requirements-prod.txt' pins 'websockets==14.2' and 'requirements.txt' includes 'websockets'.
3. WebSocket tickets are single-use, verifiable, and rejected on replay.
4. WebSocket connection rejects query-parameter JWT tokens and missing tickets.
"""

import pytest
import importlib
from unittest.mock import MagicMock, AsyncMock
from app.services.ticket_service import ticket_service
from app.api.websockets.journey_ws import journey_websocket_endpoint
from fastapi import status


def test_websockets_package_importable():
    """Verify that websockets is installed in the active environment."""
    ws_module = importlib.import_module("websockets")
    assert ws_module is not None
    assert hasattr(ws_module, "__version__")


def test_requirements_files_include_websockets():
    """Verify requirements-prod.txt and requirements.txt contain websockets."""
    with open("requirements-prod.txt", "r", encoding="utf-8") as f:
        prod_reqs = f.read()
    assert "websockets" in prod_reqs
    assert "websockets==14.2" in prod_reqs

    with open("requirements.txt", "r", encoding="utf-8") as f:
        dev_reqs = f.read()
    assert "websockets" in dev_reqs


def test_ticket_service_lifecycle():
    """Verify ticket generation, single-use consumption, and replay rejection."""
    user_id = "user_test_99"
    ticket = ticket_service.issue_ticket(user_id)
    assert ticket is not None

    assert len(ticket) > 16

    # 1st consume: must succeed and return user_id
    consumed_user = ticket_service.consume_ticket(ticket)
    assert consumed_user == user_id

    # 2nd consume (replay): must be rejected and return None
    replay_user = ticket_service.consume_ticket(ticket)
    assert replay_user is None


@pytest.mark.asyncio
async def test_journey_websocket_rejects_jwt_query_token():
    """Verify WebSocket endpoint strictly rejects JWT query parameters."""
    mock_ws = AsyncMock()
    mock_repo = MagicMock()

    await journey_websocket_endpoint(
        websocket=mock_ws,
        journey_id="j_123",
        ticket=None,
        token="eyJhbGciOi...",
        journey_repo=mock_repo
    )

    mock_ws.close.assert_called_once_with(
        code=status.WS_1008_POLICY_VIOLATION,
        reason="Query token authentication is disabled. Use single-use tickets."
    )


@pytest.mark.asyncio
async def test_journey_websocket_rejects_missing_ticket():
    """Verify WebSocket endpoint strictly rejects requests without a ticket."""
    mock_ws = AsyncMock()
    mock_repo = MagicMock()

    await journey_websocket_endpoint(
        websocket=mock_ws,
        journey_id="j_123",
        ticket=None,
        token=None,
        journey_repo=mock_repo
    )

    mock_ws.close.assert_called_once_with(
        code=status.WS_1008_POLICY_VIOLATION,
        reason="Missing single-use ticket."
    )
