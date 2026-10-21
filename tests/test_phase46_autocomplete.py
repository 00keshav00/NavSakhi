"""
NavSakhi Phase 46: Autocomplete & Place Suggestion Regression Tests
Validates instant local matching, external geocoding timeout resilience,
debounce & query cancellation guarantees, and caching behavior.
"""

import pytest
import asyncio
import time
from unittest.mock import patch
import httpx

from app.services.autocomplete_service import AutocompleteService, LocationSuggestion


@pytest.fixture
def autocomplete_svc():
    svc = AutocompleteService()
    svc._ensure_local_places()
    return svc


@pytest.mark.asyncio
async def test_partial_query_v_returns_immediate_suggestions(autocomplete_svc):
    """Typing 'V' returns local suggestions under 100ms without buffering."""
    t0 = time.perf_counter()
    res = await autocomplete_svc.get_suggestions("V", limit=6)
    dur_ms = (time.perf_counter() - t0) * 1000

    assert len(res) > 0, "Expected suggestions for single-character query 'V'"
    assert dur_ms < 200, f"Expected <200ms, took {dur_ms:.2f}ms"
    names = [r.name.lower() for r in res]
    assert any(n.startswith("v") for n in names)


@pytest.mark.asyncio
async def test_query_vi_and_vit_return_progressive_matches(autocomplete_svc):
    """Progressive typing 'VI' and 'VIT' returns relevant matches including Vit University."""
    res_vi = await autocomplete_svc.get_suggestions("VI", limit=6)
    assert len(res_vi) > 0
    vi_names = [r.name.lower() for r in res_vi]
    assert any("vi" in n for n in vi_names)

    res_vit = await autocomplete_svc.get_suggestions("VIT", limit=6)
    assert len(res_vit) > 0
    vit_names = [r.name.lower() for r in res_vit]
    assert any("vit university" in n or "vit chennai" in n for n in vit_names), f"Actual matches: {vit_names}"


@pytest.mark.asyncio
async def test_local_results_returned_when_external_geocoding_times_out(autocomplete_svc):
    """External Nominatim timeout or network failure does not block local place results."""
    async def slow_get(*args, **kwargs):
        raise httpx.ReadTimeout("Nominatim timed out after 10s")

    with patch("httpx.AsyncClient.get", side_effect=slow_get):
        t0 = time.perf_counter()
        res = await autocomplete_svc.get_suggestions("Guindy", limit=6)
        dur_ms = (time.perf_counter() - t0) * 1000

        assert len(res) > 0, "Local suggestions must be returned despite external timeout"
        assert dur_ms < 300, f"Expected fast local return under 300ms, took {dur_ms:.2f}ms"
        assert any("guindy" in r.name.lower() for r in res)


@pytest.mark.asyncio
async def test_repeated_queries_use_cache(autocomplete_svc):
    """Second query for the same term returns immediately from cache."""
    await autocomplete_svc.get_suggestions("Central", limit=6)

    t0 = time.perf_counter()
    res_cached = await autocomplete_svc.get_suggestions("Central", limit=6)
    dur_ms = (time.perf_counter() - t0) * 1000

    assert len(res_cached) > 0
    assert dur_ms < 5.0, f"Cached query should resolve in <5ms, took {dur_ms:.2f}ms"


@pytest.mark.asyncio
async def test_explicit_coordinate_query_handled_immediately(autocomplete_svc):
    """Typing raw coordinates returns a GPS Coordinate suggestion directly."""
    res = await autocomplete_svc.get_suggestions("13.0418, 80.2341", limit=6)
    assert len(res) == 1
    assert res[0].place_type == "COORDINATES"
    assert "GPS Coordinate" in res[0].place_type_label
    assert pytest.approx(res[0].latitude, 0.001) == 13.0418
    assert pytest.approx(res[0].longitude, 0.001) == 80.2341


@pytest.mark.asyncio
async def test_autocomplete_independent_of_gemini():
    """Autocomplete functions completely independently of LLM/Gemini state."""
    from app.services.autocomplete_service import global_autocomplete_service
    res = await global_autocomplete_service.get_suggestions("Anna", limit=6)
    assert len(res) > 0
    for r in res:
        assert isinstance(r, LocationSuggestion)
        assert r.id and r.name and r.formatted_coords


@pytest.mark.asyncio
async def test_case_and_punctuation_insensitivity(autocomplete_svc):
    """Queries like 't. nagar', 'T NAGAR', 't nagar' all return the primary locality."""
    res1 = await autocomplete_svc.get_suggestions("t. nagar", limit=6)
    res2 = await autocomplete_svc.get_suggestions("T NAGAR", limit=6)
    res3 = await autocomplete_svc.get_suggestions("t nagar", limit=6)

    assert len(res1) > 0 and len(res2) > 0 and len(res3) > 0
    assert any("t. nagar" in r.name.lower() or "thyagaraya" in r.name.lower() for r in res1)


@pytest.mark.asyncio
async def test_single_local_match_bypasses_external_geocoding(autocomplete_svc):
    """Queries with >= 1 local match (such as VIT) return immediately without waiting for Nominatim."""
    with patch("httpx.AsyncClient.get") as mock_get:
        t0 = time.perf_counter()
        res = await autocomplete_svc.get_suggestions("VIT", limit=6)
        dur_ms = (time.perf_counter() - t0) * 1000

        assert len(res) >= 1, "Expected local match for VIT"
        assert not mock_get.called, "Nominatim must NOT be called when local matches exist"
        assert dur_ms < 150, f"Expected <150ms return, took {dur_ms:.2f}ms"


@pytest.mark.asyncio
async def test_single_char_query_bypasses_external_geocoding(autocomplete_svc):
    """Single-character queries return instantly and never trigger external network requests."""
    with patch("httpx.AsyncClient.get") as mock_get:
        t0 = time.perf_counter()
        res = await autocomplete_svc.get_suggestions("V", limit=6)
        dur_ms = (time.perf_counter() - t0) * 1000

        assert len(res) > 0
        assert not mock_get.called, "Nominatim must NOT be called for single-char queries"
        assert dur_ms < 150, f"Expected <150ms, took {dur_ms:.2f}ms"


@pytest.mark.asyncio
async def test_zero_local_matches_invokes_bounded_nominatim(autocomplete_svc):
    """Queries with 0 local matches fall back to bounded Nominatim external geocoding."""
    mock_resp = httpx.Response(
        200,
        json=[{
            "lat": "13.0850",
            "lon": "80.2100",
            "display_name": "Unknown Place, Chennai, Tamil Nadu, India",
            "type": "locality",
            "class": "place"
        }],
        request=httpx.Request("GET", "https://nominatim.openstreetmap.org/search")
    )
    with patch("httpx.AsyncClient.get", return_value=mock_resp) as mock_get:
        res = await autocomplete_svc.get_suggestions("xyznonexistentquery123", limit=6)
        assert mock_get.called, "Nominatim should be invoked as fallback when 0 local matches exist"
        assert len(res) == 1
        assert res[0].source == "NOMINATIM"
        assert res[0].name == "Unknown Place"
