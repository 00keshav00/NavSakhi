"""
SafeShe Data-Driven Location Autocomplete Service
Combines verified local transit nodes (Metro, Suburban rail, MTC bus stops, POIs)
with OSM/Nominatim geocoding to provide rich, responsive, and categorized place suggestions.
"""

import re
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
import httpx
from pydantic import BaseModel, Field

from app.config.settings import settings

logger = logging.getLogger(__name__)


class LocationSuggestion(BaseModel):
    id: str = Field(..., description="Unique suggestion identifier")
    name: str = Field(..., description="Place or station name")
    secondary_text: str = Field(..., description="Locality, address or zone")
    place_type: str = Field(..., description="METRO_STATION, RAILWAY_STATION, BUS_STOP, SAFETY_FACILITY, LANDMARK, ADDRESS, COORDINATES")
    place_type_label: str = Field(..., description="User-facing badge label")
    latitude: float = Field(..., description="WGS84 Latitude")
    longitude: float = Field(..., description="WGS84 Longitude")
    formatted_coords: str = Field(..., description="Formatted 'lat, lon' string")
    source: str = Field("VERIFIED_DATA", description="Source provider (LOCAL_TRANSIT, LOCAL_POI, NOMINATIM, COORDINATES)")


class AutocompleteService:
    """Provides categorized place suggestions with local transit boosting and Nominatim geocoding."""

    def __init__(self):
        self.nominatim_url = settings.nominatim_base_url or "https://nominatim.openstreetmap.org"
        self._cache: Dict[str, Tuple[float, List[LocationSuggestion]]] = {}
        self._cache_ttl = 3600 # 1 hour
        self._local_stations_loaded = False
        self._local_places: List[Dict[str, Any]] = []

    def _ensure_local_places(self):
        if self._local_stations_loaded:
            return

        try:
            from app.intelligence.journey.multimodal_router import global_multimodal_router
            from app.services.local_location_resolver import CANONICAL_CHENNAI_LANDMARKS

            # 0. Canonical Curated Chennai Landmarks (Campuses, Transport Hubs, Key Junctions)
            for alias, (lon, lat, desc) in CANONICAL_CHENNAI_LANDMARKS.items():
                p_name = desc.split(",")[0].strip() if "," in desc else alias.title()
                p_type = "LANDMARK"
                p_label = "Campus / Landmark"
                if "metro" in alias or "metro" in desc.lower():
                    p_type = "METRO_STATION"
                    p_label = "Metro Station"
                elif "railway" in alias or "rail" in desc.lower() or "central" in alias or "egmore" in alias:
                    p_type = "RAILWAY_STATION"
                    p_label = "Railway Station"
                elif "bus" in alias or "bus" in desc.lower():
                    p_type = "BUS_STOP"
                    p_label = "Bus Station"

                self._local_places.append({
                    "id": f"local_landmark_{alias.replace(' ', '_')}",
                    "name": p_name,
                    "secondary_text": desc,
                    "place_type": p_type,
                    "place_type_label": p_label,
                    "latitude": float(lat),
                    "longitude": float(lon),
                    "search_terms": f"{alias} {desc} {p_name}".lower(),
                    "source": "VERIFIED_DATA"
                })

            # 1. Metro stations
            for st in getattr(global_multimodal_router, "metro_stations", []):
                self._local_places.append({
                    "id": f"local_metro_{st.get('id', st.get('code', ''))}",
                    "name": st.get("name", "Metro Station"),
                    "secondary_text": "Chennai Metro Line",
                    "place_type": "METRO_STATION",
                    "place_type_label": "Metro Station",
                    "latitude": float(st.get("lat", 0.0)),
                    "longitude": float(st.get("lon", 0.0)),
                    "search_terms": f"{st.get('name', '')} {st.get('raw_name', '')} metro".lower(),
                    "source": "LOCAL_TRANSIT"
                })

            # 2. Suburban / MRTS stations
            for st in getattr(global_multimodal_router, "suburban_stations", []):
                self._local_places.append({
                    "id": f"local_rail_{st.get('id', st.get('code', ''))}",
                    "name": st.get("name", "Railway Station"),
                    "secondary_text": "Southern Railway Suburban / MRTS",
                    "place_type": "RAILWAY_STATION",
                    "place_type_label": "Railway Station",
                    "latitude": float(st.get("lat", 0.0)),
                    "longitude": float(st.get("lon", 0.0)),
                    "search_terms": f"{st.get('name', '')} railway station suburban train".lower(),
                    "source": "LOCAL_TRANSIT"
                })

            # 3. Key Bus stops (stations with highest frequency or major junctions)
            bus_stops = getattr(global_multimodal_router, "bus_stops", [])
            for st in bus_stops[:400]: # top major bus stops
                self._local_places.append({
                    "id": f"local_bus_{st.get('id', '')}",
                    "name": st.get("name", "Bus Stop"),
                    "secondary_text": "MTC Chennai Bus Stop",
                    "place_type": "BUS_STOP",
                    "place_type_label": "Bus Stop",
                    "latitude": float(st.get("lat", 0.0)),
                    "longitude": float(st.get("lon", 0.0)),
                    "search_terms": f"{st.get('name', '')} mtc bus stop".lower(),
                    "source": "LOCAL_TRANSIT"
                })

            # 4. Safety facilities
            from app.services.poi_service import get_poi_service
            poi_service = get_poi_service()
            for poi in poi_service.pois[:200]:
                p_name = poi.get("name", "Safety Facility")
                p_cat = poi.get("category", "facility")
                p_lbl = poi.get("category_label", "Safety Facility")
                p_lat = float(poi.get("latitude", 0.0))
                p_lon = float(poi.get("longitude", 0.0))
                p_id = poi.get("poi_id", str(time.time()))
                self._local_places.append({
                    "id": f"local_poi_{p_id}",
                    "name": p_name,
                    "secondary_text": f"Verified {p_lbl}",
                    "place_type": "SAFETY_FACILITY",
                    "place_type_label": p_lbl,
                    "latitude": p_lat,
                    "longitude": p_lon,
                    "search_terms": f"{p_name} {p_cat} {p_lbl}".lower(),
                    "source": "LOCAL_POI"
                })

            self._local_stations_loaded = True
            logger.info(f"Loaded {len(self._local_places)} verified local places into Autocomplete index.")
        except Exception as e:
            logger.warning(f"Could not initialize local autocomplete index: {e}")

    def _parse_coordinate_query(self, query: str) -> Optional[LocationSuggestion]:
        """Detects if user typed direct latitude, longitude coordinates."""
        q = query.strip()
        # Pattern matching: 12.8448, 80.1527 or 12.8448 80.1527
        match = re.match(r"^([-+]?\d{1,2}(?:\.\d+)?)[,\s]+([-+]?\d{1,3}(?:\.\d+)?)$", q)
        if match:
            try:
                val1 = float(match.group(1))
                val2 = float(match.group(2))
                # Distinguish lat from lon: In Chennai/India, Lat is ~10-14, Lon is ~79-81
                if 8.0 <= val1 <= 38.0 and 68.0 <= val2 <= 98.0:
                    lat, lon = val1, val2
                elif 8.0 <= val2 <= 38.0 and 68.0 <= val1 <= 98.0:
                    lat, lon = val2, val1
                else:
                    lat, lon = val1, val2

                return LocationSuggestion(
                    id=f"coords_{lat:.5f}_{lon:.5f}",
                    name=f"Coordinate Location ({lat:.4f}, {lon:.4f})",
                    secondary_text="Explicit WGS84 Geographic Coordinate",
                    place_type="COORDINATES",
                    place_type_label="GPS Coordinate",
                    latitude=lat,
                    longitude=lon,
                    formatted_coords=f"{lat:.5f}, {lon:.5f}",
                    source="COORDINATES"
                )
            except ValueError:
                return None
        return None

    def _classify_osm_type(self, item: Dict[str, Any]) -> Tuple[str, str]:
        """Maps OpenStreetMap element types to clean UI place types and labels."""
        osm_type = str(item.get("type", "")).lower()
        osm_class = str(item.get("class", "")).lower()
        full_display = str(item.get("display_name", "")).lower()
        primary_name = full_display.split(",")[0].strip()

        if "metro" in primary_name or (osm_class == "railway" and osm_type in ["station", "stop"] and "metro" in primary_name):
            return "METRO_STATION", "Metro Station"
        if osm_class == "railway" and osm_type in ["station", "halt", "stop"]:
            return "RAILWAY_STATION", "Railway Station"
        if (osm_class == "highway" and osm_type == "bus_stop") or "bus stop" in primary_name or "bus stand" in primary_name:
            return "BUS_STOP", "Bus Stop"
        if osm_class == "amenity" and osm_type in ["hospital", "clinic", "police", "pharmacy", "fire_station"]:
            return "SAFETY_FACILITY", osm_type.replace("_", " ").title()
        if osm_type in ["mall", "supermarket", "university", "college", "school", "stadium", "cinema"]:
            return "LANDMARK", osm_type.title()
        if osm_class in ["tourism", "historic", "leisure"]:
            return "LANDMARK", "Landmark"
        if osm_class in ["place", "boundary"]:
            return "LOCALITY", "Locality"
        return "ADDRESS", "Address"

    async def get_suggestions(self, query: str, limit: int = 6) -> List[LocationSuggestion]:
        """
        Returns structured, accessible location suggestions for a query.
        """
        clean_q = query.strip()
        if not clean_q or len(clean_q) < 2:
            return []

        # 1. Check for explicit coordinates
        coord_suggestion = self._parse_coordinate_query(clean_q)
        if coord_suggestion:
            return [coord_suggestion]

        # 2. Check cache
        cache_key = clean_q.lower()
        now = time.time()
        if cache_key in self._cache:
            ts, cached_res = self._cache[cache_key]
            if (now - ts) < self._cache_ttl:
                return cached_res[:limit]

        suggestions: List[LocationSuggestion] = []
        seen_coords = set()

        # 3. Match against local verified transport nodes
        self._ensure_local_places()
        q_tokens = [t for t in cache_key.split() if len(t) >= 2]
        
        local_matches = []
        for p in self._local_places:
            score = 0
            name_lower = p["name"].lower()
            terms_lower = p["search_terms"].lower()
            name_words = re.findall(r"\b\w+\b", name_lower)
            terms_words = re.findall(r"\b\w+\b", terms_lower)

            if cache_key == name_lower:
                score += 100
            elif cache_key in terms_words:
                score += 85
            elif name_lower.startswith(cache_key):
                score += 65
            elif terms_lower.startswith(cache_key):
                score += 50
            elif any(w.startswith(cache_key) for w in name_words):
                score += 40
            elif len(cache_key) >= 4 and cache_key in name_lower:
                score += 25
            elif len(cache_key) >= 4 and all(token in terms_lower for token in q_tokens):
                score += 15

            if score > 0:
                local_matches.append((score, p))

        # Sort local matches by score
        local_matches.sort(key=lambda x: -x[0])
        for _, p in local_matches[:limit]:
            coord_key = (round(p["latitude"], 4), round(p["longitude"], 4))
            if coord_key not in seen_coords:
                seen_coords.add(coord_key)
                suggestions.append(LocationSuggestion(
                    id=p["id"],
                    name=p["name"],
                    secondary_text=p["secondary_text"],
                    place_type=p["place_type"],
                    place_type_label=p["place_type_label"],
                    latitude=p["latitude"],
                    longitude=p["longitude"],
                    formatted_coords=f"{p['latitude']:.5f}, {p['longitude']:.5f}",
                    source=p["source"]
                ))

        # Cache valid local results
        self._cache[cache_key] = (now, suggestions)
        return suggestions[:limit]

    search_locations = get_suggestions


# Global singleton instance
global_autocomplete_service = AutocompleteService()
