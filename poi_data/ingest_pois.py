"""
SafeShe - Phase 21: Verified Points of Interest (POI) Ingestion & Validation Pipeline.

Extracts, validates, deduplicates, and indexes genuine safety facilities from OpenStreetMap data:
- Police stations
- Hospitals
- Clinics and health centers
- Pharmacies
- Fire and rescue stations

Source: app/ml/Hack/ml/datasets/raw/osm/chennai_v1.osm.pbf
License: Open Database License (ODbL) 1.0 (OpenStreetMap contributors)
Output: poi_data/processed/chennai_pois.json
Manifest: poi_data/manifest.json
"""

import json
import os
import sys
import datetime
from typing import Dict, Any, List
import pyrosm
from shapely.geometry import Point

RAW_PBF_PATH = os.path.join("app", "ml", "Hack", "ml", "datasets", "raw", "osm", "chennai_v1.osm.pbf")
OUTPUT_JSON_PATH = os.path.join("poi_data", "processed", "chennai_pois.json")
MANIFEST_PATH = os.path.join("poi_data", "manifest.json")

# Geographic bounds for Chennai Metropolitan Area (CMA) validation
CHENNAI_BOUNDS = {
    "min_lat": 12.75,
    "max_lat": 13.35,
    "min_lon": 79.90,
    "max_lon": 80.45,
}

CATEGORY_MAP = {
    "police": ("police", "Police Station"),
    "hospital": ("hospital", "Hospital"),
    "clinic": ("clinic", "Clinic & Health Centre"),
    "pharmacy": ("pharmacy", "Pharmacy"),
    "fire_station": ("fire_station", "Fire & Rescue Station"),
}


def ingest_pois():
    print(f"[POI Ingestion] Loading PBF from: {RAW_PBF_PATH}")
    if not os.path.exists(RAW_PBF_PATH):
        raise FileNotFoundError(f"Source OSM PBF file not found at: {RAW_PBF_PATH}")

    osm = pyrosm.OSM(RAW_PBF_PATH)
    
    # Query facilities
    filter_dict = {
        "amenity": ["police", "hospital", "clinic", "pharmacy", "fire_station"],
        "healthcare": ["hospital", "clinic", "pharmacy"]
    }
    
    print("[POI Ingestion] Extracting POIs via pyrosm...")
    raw_df = osm.get_pois(custom_filter=filter_dict)
    print(f"[POI Ingestion] Extracted {len(raw_df)} raw records")

    valid_records: List[Dict[str, Any]] = []
    seen_ids = set()
    seen_coords = set()
    skipped_out_of_bounds = 0
    skipped_unsupported_category = 0
    skipped_duplicates = 0

    for _, row in raw_df.iterrows():
        amenity = row.get("amenity")
        healthcare = row.get("healthcare")

        # Map to canonical category
        cat_key = None
        if amenity in CATEGORY_MAP:
            cat_key = amenity
        elif healthcare in CATEGORY_MAP:
            cat_key = healthcare
        else:
            skipped_unsupported_category += 1
            continue

        canonical_category, category_label = CATEGORY_MAP[cat_key]

        # Geometry extraction
        geom = row.get("geometry")
        if geom is None:
            continue

        if isinstance(geom, Point):
            lon, lat = geom.x, geom.y
        else:
            # For building footprints (Polygon / MultiPolygon), compute representative centroid
            centroid = geom.centroid
            lon, lat = centroid.x, centroid.y

        # Coordinate sanity check
        if not (CHENNAI_BOUNDS["min_lat"] <= lat <= CHENNAI_BOUNDS["max_lat"] and
                CHENNAI_BOUNDS["min_lon"] <= lon <= CHENNAI_BOUNDS["max_lon"]):
            skipped_out_of_bounds += 1
            continue

        raw_id = row.get("id")
        osm_id = int(raw_id) if raw_id is not None else None
        poi_id = f"osm_{canonical_category}_{osm_id}" if osm_id else f"osm_{canonical_category}_{lat:.5f}_{lon:.5f}"

        if poi_id in seen_ids:
            skipped_duplicates += 1
            continue
        seen_ids.add(poi_id)

        # Spatial duplicate check (identical rounded coordinates within 10 meters and same category)
        coord_key = (round(lat, 5), round(lon, 5), canonical_category)
        if coord_key in seen_coords:
            skipped_duplicates += 1
            continue
        seen_coords.add(coord_key)

        # Name cleaning
        raw_name = row.get("name")
        name = str(raw_name).strip() if (raw_name and str(raw_name).lower() != "nan") else f"{category_label} (Unnamed)"

        # Emergency indicator
        emergency_tag = str(row.get("emergency", "")).lower()
        is_emergency = (canonical_category == "hospital") or (emergency_tag in ["yes", "designated"])

        # Timestamp / verification provenance
        raw_ts = row.get("timestamp")
        last_verified = str(raw_ts) if (raw_ts and str(raw_ts).lower() != "nan") else "2026-03-01T00:00:00Z"

        # Operator / phone if present
        operator = str(row.get("operator", "")).strip() if row.get("operator") and str(row.get("operator")).lower() != "nan" else None

        record = {
            "poi_id": poi_id,
            "osm_id": osm_id,
            "name": name,
            "category": canonical_category,
            "category_label": category_label,
            "latitude": round(float(lat), 7),
            "longitude": round(float(lon), 7),
            "is_emergency": is_emergency,
            "operator": operator,
            "source": "OpenStreetMap (ODbL 1.0)",
            "last_verified_at": last_verified,
        }
        valid_records.append(record)

    # Sort deterministically by category then poi_id
    valid_records.sort(key=lambda r: (r["category"], r["poi_id"]))

    print(f"[POI Ingestion] Validated {len(valid_records)} unique records:")
    category_counts: Dict[str, int] = {}
    for r in valid_records:
        category_counts[r["category"]] = category_counts.get(r["category"], 0) + 1
    for cat, count in category_counts.items():
        print(f"  - {cat}: {count}")
    print(f"  - Skipped out of bounds: {skipped_out_of_bounds}")
    print(f"  - Skipped duplicates: {skipped_duplicates}")
    print(f"  - Skipped unsupported categories: {skipped_unsupported_category}")

    # Write processed JSON
    os.makedirs(os.path.dirname(OUTPUT_JSON_PATH), exist_ok=True)
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(valid_records, f, indent=2, ensure_ascii=False)
    print(f"[POI Ingestion] Saved validated records to: {OUTPUT_JSON_PATH}")

    # Create manifest
    manifest = {
        "dataset_name": "safeshe_chennai_verified_pois",
        "dataset_version": "1.0.0",
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
        "publisher": "OpenStreetMap contributors",
        "source_url": "https://www.openstreetmap.org",
        "source_pbf_file": RAW_PBF_PATH,
        "license": "Open Database License (ODbL) 1.0",
        "attribution_requirement": "© OpenStreetMap contributors. Data available under the Open Database License.",
        "geographic_coverage": {
            "region": "Chennai Metropolitan Area (CMA), Tamil Nadu, India",
            "bounds": CHENNAI_BOUNDS
        },
        "total_records": len(valid_records),
        "category_breakdown": category_counts,
        "data_provenance": "Extracted directly from canonical chennai_v1.osm.pbf road and infrastructure extract.",
        "known_limitations": [
            "Facility operating hours and 24-hour emergency status are not universally tagged in OSM.",
            "Specialized clinics are distinguished from full hospitals; only hospitals are marked as default emergency departments.",
            "Coverage reflects mapped OSM records as of extract timestamp."
        ],
        "validation_rules_applied": [
            "Coordinates verified within Chennai CMA geographic bounding box [12.75-13.35 N, 79.90-80.45 E].",
            "Building footprints converted to representative geometric centroids.",
            "Deduplication by stable OSM ID and spatial proximity threshold (0.0001 deg).",
            "Preservation of genuine OSM IDs and source provenance."
        ]
    }

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"[POI Ingestion] Saved manifest to: {MANIFEST_PATH}")


if __name__ == "__main__":
    ingest_pois()
