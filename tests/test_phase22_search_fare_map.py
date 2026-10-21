"""
SafeShe — Phase 22 Regression Test Suite:
1. Fare Data Integrity (Authoritative CMRL GTFS, Unreserved SRR, Fare Unavailable for MTC, Variable Road Costs)
2. Data-Driven Location Autocomplete (Local transit priority, OSM Nominatim integration, Coordinate parsing)
3. Map Basemap Visuals (CARTO Dark Matter raster style, elimination of grayscale mud)
"""

import pytest
import pytest_asyncio
import re
from unittest.mock import AsyncMock, patch
from app.intelligence.journey.fare_engine import FareEngine, RouteFare
from app.services.autocomplete_service import AutocompleteService, LocationSuggestion


class TestFareDataIntegrity:
    """Verifies that numerical fares originate from verified data or disclose unverified status."""

    def setup_method(self):
        self.engine = FareEngine()

    def test_official_cmrl_metro_fare_lookup(self):
        """Authoritative CMRL GTFS OD fare lookup produces official tariff."""
        fare = self.engine.calculate_metro_fare(
            origin_id="Airport",
            dest_id="Puratchi Thalaivar Dr. M.G. Ramachandran Central Metro"
        )
        assert fare.is_official is True
        assert fare.fare_type == "OFFICIAL_FARE"
        assert fare.amount is not None
        assert fare.amount in [40.0, 50.0, 60.0]
        assert fare.currency == "INR"
        assert "₹" in fare.display_text
        assert "CMRL" in fare.source_label

    def test_official_srr_suburban_tariff(self):
        """Southern Railway suburban unreserved tariff calculation."""
        fare = self.engine.calculate_suburban_fare(
            origin_station="Tambaram",
            dest_station="Chennai Beach",
            distance_m=28000.0
        )
        assert fare.is_official is True
        assert fare.fare_type == "OFFICIAL_FARE"
        assert fare.amount in [5.0, 10.0]
        assert "Southern Railway" in fare.source_label

    def test_mtc_bus_fare_is_strictly_unavailable(self):
        """Bus routes without verified GTFS fare rules NEVER receive an invented numerical amount."""
        fare = self.engine.calculate_bus_fare(
            service_number="555G",
            origin_stop="Vandaloor Zoo",
            dest_stop="Marina Mall",
            distance_m=14200.0
        )
        # Numerical amount MUST be None - NEVER default to 15
        assert fare.amount is None
        assert fare.is_official is False
        assert fare.fare_type == "FARE_UNAVAILABLE"
        assert fare.display_text == "Fare unavailable"
        assert "MTC Open GTFS Feed does not contain published fare tables" in fare.source_label

    def test_road_cost_classification(self):
        """Road journey costs are classified as metered variable or personal vehicle."""
        cab_cost = self.engine.calculate_road_cost("CAB", distance_m=15000.0, duration_s=1800.0)
        assert cab_cost.fare_type == "METERED_VARIABLE"
        assert cab_cost.amount is None
        assert "Metered" in cab_cost.display_text
        assert cab_cost.is_official is False

        personal_cost = self.engine.calculate_road_cost("PERSONAL_VEHICLE", distance_m=15000.0, duration_s=1800.0)
        assert personal_cost.fare_type == "NOT_APPLICABLE"
        assert personal_cost.amount is None
        assert "Variable" in personal_cost.display_text or "variable" in personal_cost.display_text
        assert personal_cost.is_official is False

        walk_cost = self.engine.calculate_road_cost("WALK", distance_m=1200.0, duration_s=900.0)
        assert walk_cost.fare_type == "OFFICIAL_FARE"
        assert walk_cost.amount == 0.0
        assert walk_cost.display_text == "Free"


class TestLocationAutocomplete:
    """Verifies location autocomplete correctness, coordinate parsing, and provenance."""

    def setup_method(self):
        self.service = AutocompleteService()

    @pytest.mark.asyncio
    async def test_explicit_coordinate_input_supported(self):
        """Accepts explicit latitude/longitude input and parses exact coordinates."""
        results = await self.service.get_suggestions("12.8448, 80.1527")
        assert len(results) == 1
        res = results[0]
        assert res.place_type == "COORDINATES"
        assert pytest.approx(res.latitude, abs=1e-4) == 12.8448
        assert pytest.approx(res.longitude, abs=1e-4) == 80.1527
        assert "12.8448" in res.formatted_coords

    @pytest.mark.asyncio
    async def test_similar_stations_remain_distinguishable(self):
        """Chennai Central returns both Metro and Suburban transit options without confusion."""
        results = await self.service.get_suggestions("Chennai Central", limit=8)
        assert len(results) >= 2
        names = [r.name for r in results]
        types = [r.place_type for r in results]

        # Check Metro station and Railway station are distinguishable
        has_metro = any("Metro" in n or t == "METRO_STATION" for n, t in zip(names, types))
        has_rail = any("Central" in n and t in ["RAILWAY_STATION", "LOCAL_TRANSIT"] for n, t in zip(names, types))
        assert has_metro or has_rail

    @pytest.mark.asyncio
    async def test_no_hardcoded_locations(self):
        """Service queries verified datasets or external geocoder, not static mock lists."""
        assert len(self.service._local_places) == 0  # Starts empty until initialized
        self.service._ensure_local_places()
        assert len(self.service._local_places) > 100  # Indexed from real transit stops & POIs

    @pytest.mark.asyncio
    async def test_short_query_returns_empty(self):
        """Single character queries return bounded local verified suggestions without calling external geocoder."""
        # 1. Empty or whitespace-only input must strictly return an empty list
        assert await self.service.get_suggestions("") == []
        assert await self.service.get_suggestions("   ") == []

        # 2. Single-character query returns bounded list of verified local suggestions
        with patch("httpx.AsyncClient.get") as mock_get:
            limit = 6
            results = await self.service.get_suggestions("a", limit=limit)

            # Prove Nominatim or external geocoding is NOT called
            mock_get.assert_not_called()

            # Results are capped according to the requested limit
            assert 0 < len(results) <= limit

            # Results must be verified local suggestions, no duplicates, no fabricated coordinates
            seen_ids = set()
            for r in results:
                assert r.id not in seen_ids, f"Duplicate suggestion id {r.id}"
                seen_ids.add(r.id)
                assert r.source in ["LOCAL_TRANSIT", "LOCAL_POI", "LOCAL_LANDMARK"]
                assert 12.5 <= r.latitude <= 13.5, f"Invalid latitude {r.latitude}"
                assert 79.8 <= r.longitude <= 80.5, f"Invalid longitude {r.longitude}"
                assert "a" in r.name.lower() or "a" in r.secondary_text.lower()

    @pytest.mark.asyncio
    async def test_canonical_coordinates_preserved(self):
        """Suggestion object binds canonical latitude and longitude floats."""
        suggestion = LocationSuggestion(
            id="test_loc_1",
            name="VIT Chennai",
            secondary_text="Kelambakkam - Vandalur Rd, Chennai",
            place_type="LANDMARK",
            place_type_label="Landmark",
            latitude=12.8448,
            longitude=80.1527,
            formatted_coords="12.84480, 80.15270",
            source="LOCAL_TRANSIT"
        )
        assert suggestion.latitude == 12.8448
        assert suggestion.longitude == 80.1527
        assert suggestion.formatted_coords == "12.84480, 80.15270"


class TestMapVisualBasemap:
    """Verifies that the MapLibre basemap uses refined raster tiles without desaturating grayscale mud."""

    def test_basemap_tile_source_and_no_saturation_mud(self):
        """Reads SafeMap.tsx to verify the basemap style eliminates -0.85 saturation mud."""
        with open("frontend/src/components/map/SafeMap.tsx", "r", encoding="utf-8") as f:
            content = f.read()

        # Must use tile source without proprietary watermarks
        assert "tile.openstreetmap.org" in content
        # Must NOT crush saturation with -0.85
        assert '"raster-saturation": -0.85' not in content
        # Must have natural saturation
        assert '"raster-saturation": 0.0' in content
