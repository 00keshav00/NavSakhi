"""
NavSakhi Phase 51.86 — Dashboard Weather Negative-Cache Remediation Test Suite
Verifies:
1. Positive cache reuse for 900s TTL.
2. 429 response generates honest RATE_LIMITED state with stable provider 'Open-Meteo'.
3. Negative-cache cooldown (30s) prevents repeated outbound provider requests for same coordinates.
4. Provider-wide rate-limit cooldown prevents calls for different coordinates during active 429 cooldown.
5. Cooldown expiration permits new attempts and successfully recovers to AVAILABLE state.
6. Transient network timeouts/exceptions use 30s negative cooldown instead of 15-minute lock-in.
7. Provider identity remains 'Open-Meteo' across available and unavailable responses.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from app.services.weather_service import WeatherService
from app.schemas.weather_schemas import LiveWeatherResponse


def create_mock_open_meteo_payload(temp=28.5, condition_code=0):
    return {
        "current": {
            "time": "2026-10-25T16:00",
            "temperature_2m": temp,
            "apparent_temperature": temp + 2.0,
            "relative_humidity_2m": 65,
            "wind_speed_10m": 12.0,
            "wind_direction_10m": 180,
            "precipitation": 0.0,
            "rain": 0.0,
            "cloud_cover": 20,
            "weather_code": condition_code,
            "uv_index": 0.0,
        },
        "daily": {
            "time": ["2026-10-25"],
            "weather_code": [condition_code],
            "temperature_2m_max": [temp + 4.0],
            "temperature_2m_min": [temp - 3.0],
            "sunrise": ["2026-10-25T06:05"],
            "sunset": ["2026-10-25T17:50"],
            "uv_index_max": [7.5],
        },
        "hourly": {
            "time": ["2026-10-25T16:00", "2026-10-25T17:00"],
            "temperature_2m": [temp, temp - 0.5],
            "precipitation_probability": [0, 5],
            "weather_code": [condition_code, condition_code],
        },
        "timezone": "Asia/Kolkata",
    }


class ControllableClock:
    def __init__(self, start_time: float = 1000.0):
        self.current_time = start_time

    def __call__(self) -> float:
        return self.current_time

    def advance(self, seconds: float):
        self.current_time += seconds


@pytest.mark.asyncio
async def test_successful_weather_response_cached_for_positive_ttl():
    """Verify successful weather observations are cached for the 900s positive TTL."""
    clock = ControllableClock(start_time=1000.0)
    service = WeatherService(time_func=clock)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = create_mock_open_meteo_payload(temp=27.0)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        # 1st call at t=1000.0: should call provider
        res1 = await service.get_live_weather(13.0827, 80.2707, "Chennai Central")
        assert res1.available is True
        assert res1.status == "AVAILABLE"
        assert res1.provider == "Open-Meteo"
        assert res1.cached is False
        assert res1.cache_expires_in_seconds == 900
        assert mock_get.call_count == 1

        # Advance 100s to t=1100.0 (within 900s positive TTL)
        clock.advance(100.0)
        res2 = await service.get_live_weather(13.0827, 80.2707, "Chennai Central")
        assert res2.available is True
        assert res2.cached is True
        assert res2.cache_expires_in_seconds == 800
        assert mock_get.call_count == 1  # No additional provider request


@pytest.mark.asyncio
async def test_429_rate_limit_and_negative_cache_cooldown():
    """Verify 429 sets RATE_LIMITED state and suppresses provider requests during 30s cooldown."""
    clock = ControllableClock(start_time=2000.0)
    service = WeatherService(time_func=clock)

    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp_429

        # 1st call at t=2000.0: hits 429
        res1 = await service.get_live_weather(13.0067, 80.2024, "Guindy")
        assert res1.available is False
        assert res1.status == "RATE_LIMITED"
        assert res1.provider == "Open-Meteo"  # Normalized provider identity
        assert res1.cached is False
        assert res1.cache_expires_in_seconds == 30
        assert mock_get.call_count == 1

        # 2nd call at t=2010.0 (10s later, within 30s cooldown): same coordinates
        clock.advance(10.0)
        res2 = await service.get_live_weather(13.0067, 80.2024, "Guindy")
        assert res2.available is False
        assert res2.status == "RATE_LIMITED"
        assert res2.provider == "Open-Meteo"
        assert res2.cached is True
        assert res2.cache_expires_in_seconds == 20
        assert mock_get.call_count == 1  # Suppressed! No second outbound HTTP call

        # 3rd call at t=2015.0: different coordinates (Tambaram) during provider-wide cooldown
        clock.advance(5.0)
        res3 = await service.get_live_weather(12.9249, 80.1000, "Tambaram")
        assert res3.available is False
        assert res3.status == "RATE_LIMITED"
        assert res3.provider == "Open-Meteo"
        assert res3.cached is True
        assert res3.cache_expires_in_seconds == 15
        assert mock_get.call_count == 1  # Suppressed by provider-wide cooldown!


@pytest.mark.asyncio
async def test_negative_cache_expiration_and_recovery():
    """Verify negative cache expires after 30s and a successful retry recovers to AVAILABLE."""
    clock = ControllableClock(start_time=3000.0)
    service = WeatherService(time_func=clock)

    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = create_mock_open_meteo_payload(temp=31.0)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp_429

        # Trigger 429 at t=3000.0
        res1 = await service.get_live_weather(13.0827, 80.2707, "Chennai Central")
        assert res1.status == "RATE_LIMITED"
        assert mock_get.call_count == 1

        # Advance beyond 30s cooldown to t=3035.0
        clock.advance(35.0)
        # Provider recovers!
        mock_get.return_value = mock_resp_200

        # Next request after cooldown: must attempt provider call and recover
        res2 = await service.get_live_weather(13.0827, 80.2707, "Chennai Central")
        assert res2.available is True
        assert res2.status == "AVAILABLE"
        assert res2.provider == "Open-Meteo"
        assert res2.cached is False
        assert res2.temperature == 31.0
        assert res2.cache_expires_in_seconds == 900
        assert mock_get.call_count == 2  # Outbound attempt permitted!


@pytest.mark.asyncio
async def test_transient_network_timeout_uses_short_cooldown():
    """Verify network exceptions use 30s cooldown instead of locking in for 15 minutes."""
    clock = ControllableClock(start_time=4000.0)
    service = WeatherService(time_func=clock)

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = create_mock_open_meteo_payload(temp=29.0)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        # Simulate network timeout
        mock_get.side_effect = httpx.ConnectTimeout("Connection to Open-Meteo timed out")

        # 1st call at t=4000.0: fails with network error
        res1 = await service.get_live_weather(13.0300, 80.2100, "Saidapet")
        assert res1.available is False
        assert res1.status == "UNAVAILABLE"
        assert res1.provider == "Open-Meteo"
        assert res1.cached is False
        assert res1.cache_expires_in_seconds == 30
        assert "temporarily unreachable" in res1.warnings[0]
        assert mock_get.call_count == 1

        # 2nd call at t=4010.0: within 30s negative cache
        clock.advance(10.0)
        res2 = await service.get_live_weather(13.0300, 80.2100, "Saidapet")
        assert res2.available is False
        assert res2.cached is True
        assert res2.cache_expires_in_seconds == 20
        assert mock_get.call_count == 1

        # Advance 25s to t=4035.0 (total 35s, past negative cache TTL)
        clock.advance(25.0)
        mock_get.side_effect = None
        mock_get.return_value = mock_resp_200

        # 3rd call: must retry and succeed rather than waiting 900s
        res3 = await service.get_live_weather(13.0300, 80.2100, "Saidapet")
        assert res3.available is True
        assert res3.status == "AVAILABLE"
        assert res3.provider == "Open-Meteo"
        assert res3.cached is False
        assert res3.temperature == 29.0
        assert mock_get.call_count == 2
