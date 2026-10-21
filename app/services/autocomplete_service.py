"""
SafeShe Data-Driven Location Autocomplete Service
Combines verified local transit nodes (Metro, Suburban rail, MTC bus stops, POIs, landmarks)
with bounded OSM/Nominatim fallback to provide immediate, progressive place suggestions.
"""

import re
import time
import os
import json
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
    place_type: str = Field(..., description="METRO_STATION, RAILWAY_STATION, BUS_STOP, SAFETY_FACILITY, LANDMARK, LOCALITY, ADDRESS, COORDINATES")
    place_type_label: str = Field(..., description="User-facing badge label")
    latitude: float = Field(..., description="WGS84 Latitude")
    longitude: float = Field(..., description="WGS84 Longitude")
    formatted_coords: str = Field(..., description="Formatted 'lat, lon' string")
    source: str = Field("VERIFIED_DATA", description="Source provider (LOCAL_TRANSIT, LOCAL_POI, LOCAL_LANDMARK, NOMINATIM, COORDINATES)")


class AutocompleteService:
    """
    Provides categorized place suggestions with instant local-first matching
    and non-blocking external Nominatim fallback enrichment.
    """

    def __init__(self):
        self.nominatim_url = settings.nominatim_base_url or "https://nominatim.openstreetmap.org"
        self._cache: Dict[str, Tuple[float, List[LocationSuggestion]]] = {}
        self._cache_ttl = 3600  # 1 hour
        self._local_places_loaded = False
        self._local_places: List[Dict[str, Any]] = []

    def _ensure_local_places(self):
        if self._local_places_loaded:
            return

        try:
            places: List[Dict[str, Any]] = []

            # 1. Metro stations
            metro_path = os.path.join("transit_data", "processed", "metro_network.json")
            if os.path.exists(metro_path):
                try:
                    with open(metro_path, "r", encoding="utf-8") as f:
                        metro = json.load(f)
                        for st in metro.get("stations", []):
                            s_name = st.get("name", "Metro Station")
                            s_raw = st.get("raw_name", "")
                            places.append({
                                "id": f"local_metro_{st.get('id', st.get('code', ''))}",
                                "name": s_name,
                                "secondary_text": "Chennai Metro Line",
                                "place_type": "METRO_STATION",
                                "place_type_label": "Metro Station",
                                "latitude": float(st.get("lat", 0.0)),
                                "longitude": float(st.get("lon", 0.0)),
                                "search_terms": f"{s_name} {s_raw} metro station".lower(),
                                "source": "LOCAL_TRANSIT"
                            })
                except Exception as e:
                    logger.debug(f"Metro loading note: {e}")

            # 2. Suburban / MRTS stations
            sub_path = os.path.join("transit_data", "processed", "suburban_network.json")
            if os.path.exists(sub_path):
                try:
                    with open(sub_path, "r", encoding="utf-8") as f:
                        sub = json.load(f)
                        for st in sub.get("stations", []):
                            s_name = st.get("name", "Railway Station")
                            places.append({
                                "id": f"local_rail_{st.get('id', st.get('code', ''))}",
                                "name": s_name,
                                "secondary_text": "Southern Railway Suburban / MRTS",
                                "place_type": "RAILWAY_STATION",
                                "place_type_label": "Railway Station",
                                "latitude": float(st.get("lat", 0.0)),
                                "longitude": float(st.get("lon", 0.0)),
                                "search_terms": f"{s_name} railway station suburban train".lower(),
                                "source": "LOCAL_TRANSIT"
                            })
                except Exception as e:
                    logger.debug(f"Suburban loading note: {e}")

            # 3. Comprehensive Bus Stops (all verified MTC stops)
            bus_path = os.path.join("transit_data", "processed", "bus_network.json")
            if os.path.exists(bus_path):
                try:
                    with open(bus_path, "r", encoding="utf-8") as f:
                        bn = json.load(f)
                        for st in bn.get("stops", []):
                            s_name = st.get("name", "Bus Stop")
                            places.append({
                                "id": f"local_bus_{st.get('id', '')}",
                                "name": s_name,
                                "secondary_text": "MTC Chennai Bus Stop",
                                "place_type": "BUS_STOP",
                                "place_type_label": "Bus Stop",
                                "latitude": float(st.get("lat", 0.0)),
                                "longitude": float(st.get("lon", 0.0)),
                                "search_terms": f"{s_name} mtc bus stop".lower(),
                                "source": "LOCAL_TRANSIT"
                            })
                except Exception as e:
                    logger.debug(f"Bus stops loading note: {e}")

            # 4. Verified Safety POIs
            poi_path = os.path.join("poi_data", "processed", "chennai_pois.json")
            if os.path.exists(poi_path):
                try:
                    with open(poi_path, "r", encoding="utf-8") as f:
                        pois = json.load(f)
                        for poi in pois:
                            p_name = poi.get("name", "Safety Facility")
                            p_cat = poi.get("category", "facility")
                            p_lbl = poi.get("category_label", "Safety Facility")
                            places.append({
                                "id": f"local_poi_{poi.get('poi_id', '')}",
                                "name": p_name,
                                "secondary_text": f"Verified {p_lbl}",
                                "place_type": "SAFETY_FACILITY",
                                "place_type_label": p_lbl,
                                "latitude": float(poi.get("latitude", 0.0)),
                                "longitude": float(poi.get("longitude", 0.0)),
                                "search_terms": f"{p_name} {p_cat} {p_lbl}".lower(),
                                "source": "LOCAL_POI"
                            })
                except Exception as e:
                    logger.debug(f"POI loading note: {e}")

            # 5. Major Chennai Hubs, Educational Landmarks & Common Aliases
            known_landmarks = [
                ("VIT Chennai", "Vellore Institute of Technology, Vandalur-Kelambakkam Rd", 12.84042, 80.15281, "LANDMARK", "University / Institute", "vit vellore institute technology chennai kelambakkam vandalur"),
                ("T. Nagar", "Thyagaraya Nagar Commercial & Shopping District", 13.0418, 80.2341, "LOCALITY", "Locality", "t nagar thiyagaraya thyagarayanagar panagal park pondy bazaar"),
                ("IIT Madras", "Indian Institute of Technology, Sardar Patel Road, Adyar", 12.9915, 80.2337, "LANDMARK", "University / Institute", "iit madras indian institute technology adyar"),
                ("Anna University", "Guindy Campus, Sardar Patel Road", 13.0125, 80.2355, "LANDMARK", "University / Institute", "anna university guindy cept mit"),
                ("Chennai Central", "Puratchi Thalaivar Dr. M.G.R. Central Railway Station", 13.0827, 80.2755, "RAILWAY_STATION", "Major Terminal", "chennai central railway station mgr central"),
                ("Marina Beach", "Kamarajar Promenade, Triplicane / Mylapore", 13.0500, 80.2824, "LANDMARK", "Beach & Landmark", "marina beach promenade kamarajar salai"),
                ("Chennai Airport", "Meenambakkam International & Domestic Terminal", 12.9941, 80.1709, "LANDMARK", "Airport", "chennai airport meenambakkam terminal"),
            ]
            for name, sec, lat, lon, ptype, plabel, terms in known_landmarks:
                places.append({
                    "id": f"local_hub_{re.sub(r'[^a-z0-9]', '_', name.lower())}",
                    "name": name,
                    "secondary_text": sec,
                    "place_type": ptype,
                    "place_type_label": plabel,
                    "latitude": lat,
                    "longitude": lon,
                    "search_terms": terms.lower(),
                    "source": "LOCAL_LANDMARK"
                })

            self._local_places = places
            self._local_places_loaded = True
            logger.info(f"Loaded {len(self._local_places)} verified local places into Autocomplete index.")
        except Exception as e:
            logger.warning(f"Could not initialize local autocomplete index: {e}")

    def _parse_coordinate_query(self, query: str) -> Optional[LocationSuggestion]:
        """Detects if user typed direct latitude, longitude coordinates."""
        q = query.strip()
        match = re.match(r"^([-+]?\d{1,2}(?:\.\d+)?)[,\s]+([-+]?\d{1,3}(?:\.\d+)?)$", q)
        if match:
            try:
                val1 = float(match.group(1))
                val2 = float(match.group(2))
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

    async def get_suggestions(self, query: str, limit: int = 8) -> List[LocationSuggestion]:
        """
        Returns structured, accessible location suggestions for a query.
        Local verified places return in <50ms; optional Nominatim acts as non-blocking enrichment.
        """
        clean_q = query.strip()
        if not clean_q:
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

        # 3. Fast In-Memory Local Search (always prioritized)
        self._ensure_local_places()
        norm_q = re.sub(r'[^a-z0-9\s]', '', cache_key).strip()
        q_tokens = [t for t in norm_q.split() if t]

        matches: List[Tuple[int, Dict[str, Any]]] = []
        for p in self._local_places:
            nl = p["name"].lower()
            norm_name = re.sub(r'[^a-z0-9\s]', '', nl)
            score = 0

            # Exact match
            if norm_name == norm_q or nl == cache_key:
                score = 150
            # Full prefix match
            elif nl.startswith(cache_key) or norm_name.startswith(norm_q):
                score = 100
            # Word-initial prefix match (e.g. 'VIT' in 'VIT Chennai' or 'Vit University')
            elif any(w.startswith(norm_q) for w in norm_name.split()):
                score = 80
            # Search terms contain token prefix
            elif any(w.startswith(norm_q) for w in p["search_terms"].split()):
                score = 60
            # All query tokens present in name or terms
            elif q_tokens and all(token in norm_name or token in p["search_terms"] for token in q_tokens):
                score = 40
            # Substring match (for queries >= 2 chars)
            elif len(norm_q) >= 2 and norm_q in norm_name:
                score = 30

            if score > 0:
                matches.append((score, p))

        matches.sort(key=lambda x: -x[0])

        suggestions: List[LocationSuggestion] = []
        seen_coords = set()

        for score, p in matches:
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
                if len(suggestions) >= limit:
                    break

        # Fast path: Return immediately whenever at least one verified local place matches
        # or if query is a single character, ensuring zero external network latency delay.
        if len(suggestions) >= 1 or len(clean_q) < 2:
            self._cache[cache_key] = (now, suggestions)
            return suggestions[:limit]

        # 4. Optional External Nominatim Fallback / Enrichment (Strict 1.2s timeout)
        try:
            async with httpx.AsyncClient(timeout=1.2) as client:
                params = {
                    "q": clean_q,
                    "format": "json",
                    "limit": limit,
                    "addressdetails": 1,
                    "countrycodes": "in",
                    "viewbox": "79.90,13.35,80.35,12.70",
                    "bounded": 0
                }
                headers = {"User-Agent": "NavSakhi/1.0 (LocationSearch)"}
                resp = await client.get(f"{self.nominatim_url}/search", params=params, headers=headers)

                if resp.status_code == 200:
                    data = resp.json()
                    for item in data:
                        try:
                            lat = float(item.get("lat"))
                            lon = float(item.get("lon"))
                            coord_key = (round(lat, 4), round(lon, 4))
                            if coord_key in seen_coords:
                                continue
                            seen_coords.add(coord_key)

                            raw_display = item.get("display_name", "")
                            parts = [p.strip() for p in raw_display.split(",") if p.strip()]
                            name = parts[0] if parts else clean_q

                            addr = item.get("address", {})
                            locality_parts = []
                            for k in ["suburb", "neighbourhood", "city_district", "road", "city"]:
                                if k in addr and addr[k] not in locality_parts and addr[k] != name:
                                    locality_parts.append(addr[k])

                            secondary_text = ", ".join(locality_parts[:3]) if locality_parts else (", ".join(parts[1:4]) if len(parts) > 1 else "Chennai Region")
                            pt_type, pt_label = self._classify_osm_type(item)

                            suggestions.append(LocationSuggestion(
                                id=f"nom_{item.get('osm_type', 'node')}_{item.get('osm_id', int(time.time()))}",
                                name=name,
                                secondary_text=secondary_text,
                                place_type=pt_type,
                                place_type_label=pt_label,
                                latitude=lat,
                                longitude=lon,
                                formatted_coords=f"{lat:.5f}, {lon:.5f}",
                                source="NOMINATIM"
                            ))
                            if len(suggestions) >= limit:
                                break
                        except (ValueError, TypeError):
                            continue
        except Exception as net_err:
            logger.debug(f"Optional Nominatim enrichment note: {net_err}")

        # Cache valid results
        self._cache[cache_key] = (now, suggestions)
        return suggestions[:limit]

    search_locations = get_suggestions


# Global singleton instance
global_autocomplete_service = AutocompleteService()
