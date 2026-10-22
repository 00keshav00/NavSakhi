"""
NavSakhi Phase 46K.1 Pre-Warming & Autocomplete Verification Suite
Verifies:
1. Autocomplete accessor and singleton resolution.
2. Full pre-warming lifecycle reaching "completed".
3. Graceful handling and transparent recording of initialization failures.
4. Thread-safe locking preventing duplicate singleton/place loading.
5. Independence of /health/ready from pre-warming status.
6. Full preservation of verified local places (7,786+ places) and autocomplete query API.
7. Companion-store validation integrity.
"""

import asyncio
import threading
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app, _async_startup_db_init, _prewarm_status
from app.services.autocomplete_service import (
    global_autocomplete_service,
    get_global_autocomplete_service,
    AutocompleteService,
    LocationSuggestion,
)
from app.intelligence.journey.spatial_matcher import validate_companion_stores


# --- 1. Autocomplete accessor resolution and singleton identity ---

def test_autocomplete_accessor_resolution():
    """Verify that both global_autocomplete_service and get_global_autocomplete_service resolve to the same instance."""
    svc = get_global_autocomplete_service()
    assert svc is global_autocomplete_service
    assert isinstance(svc, AutocompleteService)
    assert hasattr(svc, "_ensure_local_places")
    assert callable(svc._ensure_local_places)
    assert hasattr(svc, "warm_cache")
    assert callable(svc.warm_cache)


# --- 2. Full pre-warming sequence reaches "completed" ---

@pytest.mark.asyncio
async def test_full_prewarm_sequence_completes():
    """Verify that _async_startup_db_init sequentially warms all singletons and sets status to 'completed'."""
    with patch("app.main.initialize_database", new=AsyncMock(return_value=None)):
        await _async_startup_db_init()
        assert _prewarm_status["status"] == "completed"
        assert _prewarm_status["completed_at"] is not None
        assert _prewarm_status["error"] is None


# --- 3. Initializer failure records 'failed' without masking error ---

@pytest.mark.asyncio
async def test_prewarm_failure_records_failed_status():
    """Verify that if any component fails during pre-warming, status is set to 'failed' with error captured."""
    with patch("app.main.initialize_database", new=AsyncMock(return_value=None)), \
         patch("app.ml.predictor.get_ml_safety_predictor", side_effect=RuntimeError("Simulated predictor failure")):
        await _async_startup_db_init()
        assert _prewarm_status["status"] == "failed"
        assert "Simulated predictor failure" in _prewarm_status["error"]


# --- 4. Thread-safe lock prevents duplicate place loading ---

def test_autocomplete_thread_safe_locking():
    """Verify AutocompleteService uses double-checked locking so concurrent calls do not re-load local places."""
    svc = AutocompleteService()
    assert hasattr(svc, "_lock")
    assert isinstance(svc._lock, type(threading.Lock()))

    load_count = 0
    orig_impl = svc._load_local_places_impl

    def tracked_impl():
        nonlocal load_count
        load_count += 1
        orig_impl()

    svc._load_local_places_impl = tracked_impl

    # Call concurrently from 5 threads
    threads = []
    for _ in range(5):
        t = threading.Thread(target=svc._ensure_local_places)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert load_count == 1, f"Expected _load_local_places_impl to be called exactly once, called {load_count} times"
    assert svc._local_places_loaded is True
    assert len(svc._local_places) > 1000


# --- 5. /health/ready remains lightweight and independent of pre-warm ---

def test_health_ready_independent_of_prewarm():
    """Verify that /health/ready passes regardless of prewarm state and does not trigger heavy prewarm."""
    client = TestClient(app)

    # Set prewarm to failed
    _prewarm_status["status"] = "failed"
    _prewarm_status["error"] = "Test error"

    res = client.get("/health/ready")
    assert res.status_code == 200
    assert res.json()["status"] == "ready"

    # Set prewarm to in_progress
    _prewarm_status["status"] = "in_progress"
    res_in_prog = client.get("/health/ready")
    assert res_in_prog.status_code == 200
    assert res_in_prog.json()["status"] == "ready"

    # Verify /health endpoint exposes prewarm accurately
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["prewarm"] == "in_progress"


# --- 6. Existing autocomplete behavior and verified local places preserved ---

@pytest.mark.asyncio
async def test_autocomplete_behavior_and_index_preserved():
    """Verify that autocomplete queries correctly match verified local places."""
    svc = get_global_autocomplete_service()
    suggestions = await svc.get_suggestions("VIT", limit=6)
    assert len(suggestions) > 0
    names = [s.name.lower() for s in suggestions]
    assert any("vit university" in n or "vit chennai" in n for n in names)
    assert any(s.source.startswith("LOCAL_") for s in suggestions)


# --- 7. Phase 46I companion-store validation intact ---

def test_companion_store_validation_intact():
    """Verify companion store validation succeeds without regression."""
    valid, reason = validate_companion_stores()
    assert valid is True
    assert reason is None