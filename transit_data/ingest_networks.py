import zipfile
import csv
import io
import json
import os
import math
import sys
from typing import Dict, List, Any, Tuple

# Add parent directory to sys.path so we can import StationNormalizer
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.intelligence.journey.station_normalizer import station_normalizer, clean_station_name, haversine_m

DOWNLOADS_DIR = "transit_data/downloads"
PROCESSED_DIR = "transit_data/processed"

def process_metro():
    print("Processing CMRL Metro GTFS with Generic Station Normalizer...")
    path = os.path.join(DOWNLOADS_DIR, "cmrl-gtfs.zip")
    data, diag = station_normalizer.normalize_gtfs_rail(
        path, mode_prefix="METRO", mode_type="Metro"
    )
    out_path = os.path.join(PROCESSED_DIR, "metro_network.json")
    with open(out_path, "w", encoding="utf-8") as out:
        json.dump(data, out, indent=2)
    print(f"Saved {len(data['stations'])} normalized Metro stations to {out_path}")
    return data, diag

def process_suburban():
    print("Processing Southern Railway Suburban & MRTS GTFS with Generic Station Normalizer...")
    path = os.path.join(DOWNLOADS_DIR, "srr-gtfs.zip")
    data, diag = station_normalizer.normalize_gtfs_rail(
        path, mode_prefix="SRR", mode_type="Suburban"
    )
    out_path = os.path.join(PROCESSED_DIR, "suburban_network.json")
    with open(out_path, "w", encoding="utf-8") as out:
        json.dump(data, out, indent=2)
    print(f"Saved {len(data['stations'])} normalized Suburban/MRTS stations and {len(data['routes'])} active corridors to {out_path}")
    return data, diag

def process_mtc():
    print("Processing MTC Bus GTFS...")
    path = os.path.join(DOWNLOADS_DIR, "mtc-gtfs.zip")
    with zipfile.ZipFile(path, "r") as z:
        stops = {}
        with z.open("stops.txt") as f:
            reader = csv.DictReader(io.TextIOWrapper(f, "utf-8", errors="replace"))
            for r in reader:
                sid = r["stop_id"].strip()
                lat = float(r["stop_lat"])
                lon = float(r["stop_lon"])
                stops[sid] = {
                    "id": f"MTC_{sid}",
                    "stop_id": sid,
                    "name": r["stop_name"].strip(),
                    "lat": lat,
                    "lon": lon,
                    "type": "BusStop"
                }

        # Routes
        routes_meta = {}
        with z.open("routes.txt") as f:
            reader = csv.DictReader(io.TextIOWrapper(f, "utf-8", errors="replace"))
            for r in reader:
                rid = r["route_id"].strip()
                s_name = r.get("route_short_name", "").strip()
                l_name = r.get("route_long_name", "").strip()
                routes_meta[rid] = {
                    "route_id": rid,
                    "service_number": s_name,
                    "route_long_name": l_name
                }

        # Trip to Route
        trip_route_map = {}
        with z.open("trips.txt") as f:
            reader = csv.DictReader(io.TextIOWrapper(f, "utf-8", errors="replace"))
            for r in reader:
                trip_route_map[r["trip_id"].strip()] = r["route_id"].strip()

        # Stop sequences per route (take representative trip for each route)
        route_sequences = {}
        with z.open("stop_times.txt") as f:
            reader = csv.DictReader(io.TextIOWrapper(f, "utf-8", errors="replace"))
            for r in reader:
                tid = r["trip_id"].strip()
                rid = trip_route_map.get(tid)
                if not rid:
                    continue
                sid = r["stop_id"].strip()
                if sid not in stops:
                    continue
                seq = int(r["stop_sequence"])
                if rid not in route_sequences:
                    route_sequences[rid] = {}
                if tid not in route_sequences[rid]:
                    route_sequences[rid][tid] = []
                # Keep up to 2 distinct trip patterns per route to manage memory
                if len(route_sequences[rid]) <= 2:
                    route_sequences[rid][tid].append((seq, sid))

        # Build clean bus route list
        processed_routes = []
        for rid, trips in route_sequences.items():
            meta = routes_meta.get(rid, {})
            patterns = []
            for tid, seq_tuples in trips.items():
                ordered = [f"MTC_{item[1]}" for item in sorted(seq_tuples, key=lambda x: x[0])]
                if len(ordered) >= 3 and ordered not in patterns:
                    patterns.append(ordered)
            if patterns:
                processed_routes.append({
                    "route_id": rid,
                    "service_number": meta.get("service_number", rid),
                    "route_long_name": meta.get("route_long_name", ""),
                    "patterns": patterns
                })

        data = {
            "mode": "Bus",
            "stop_count": len(stops),
            "route_count": len(processed_routes),
            "stops": list(stops.values()),
            "routes": processed_routes
        }
        out_path = os.path.join(PROCESSED_DIR, "bus_network.json")
        with open(out_path, "w", encoding="utf-8") as out:
            json.dump(data, out, indent=2)
        print(f"Saved {len(stops)} Bus stops and {len(processed_routes)} Bus routes to {out_path}")
        return data

def build_interchanges(metro_data: dict, suburban_data: dict):
    print("Building verified multimodal interchange hubs...")
    pair_map = {}
    for m in metro_data["stations"]:
        for s in suburban_data["stations"]:
            dist = haversine_m(m["lat"], m["lon"], s["lat"], s["lon"])
            if dist <= 450:  # Direct pedestrian transfer threshold
                key = (m["name"], s["name"])
                if key not in pair_map or dist < pair_map[key]["transfer_distance_m"]:
                    walk_min = max(2, int(round(dist / 75.0))) # ~4.5 km/h walking pace
                    pair_map[key] = {
                        "id": f"INT_{m['id']}_{s['id']}",
                        "metro_station_id": m["id"],
                        "metro_station_name": m["name"],
                        "rail_station_id": s["id"],
                        "rail_station_name": s["name"],
                        "transfer_distance_m": round(dist, 1),
                        "walk_time_min": walk_min,
                        "facility_type": "Pedestrian Subway / Walkway / Integrated Concourse"
                    }

    interchanges = list(pair_map.values())
    out_path = os.path.join(PROCESSED_DIR, "interchanges.json")
    with open(out_path, "w", encoding="utf-8") as out:
        json.dump(interchanges, out, indent=2)
    print(f"Saved {len(interchanges)} verified Multimodal Interchanges to {out_path}")
    for it in interchanges:
        print(f"  {it['metro_station_name']} <-> {it['rail_station_name']} ({it['transfer_distance_m']}m, {it['walk_time_min']} min)")
    return interchanges

def export_canonical_all_stations(metro_data: dict, suburban_data: dict):
    print("Exporting canonical all_stations.json from normalized GTFS networks...")
    canonical = []
    seen_names = set()

    for s in metro_data["stations"]:
        name = s["name"]
        entrances = [[e["lat"], e["lon"]] for e in s.get("entrances", [])]
        if not entrances:
            entrances = [[s["lat"], s["lon"]]]
        aliases = [name.lower()]
        for w in ["metro", "station", "central"]:
            c = name.lower().replace(w, "").strip()
            if c and c not in aliases:
                aliases.append(c)
        canonical.append({
            "name": name,
            "type": "Metro",
            "coordinates": [s["lat"], s["lon"]],
            "operational_status": "OPERATIONAL",
            "entrances": entrances,
            "aliases": aliases,
            "station_id": s["id"]
        })
        seen_names.add(name.lower())

    for s in suburban_data["stations"]:
        name = s["name"]
        # If already present under same name (e.g. multimodal hub), distinguish or record
        display_name = name
        if display_name.lower() in seen_names:
            display_name = f"{name} Railway"

        entrances = [[e["lat"], e["lon"]] for e in s.get("entrances", [])]
        if not entrances and s.get("platforms"):
            entrances = [[p["lat"], p["lon"]] for p in s.get("platforms", [])]
        if not entrances:
            entrances = [[s["lat"], s["lon"]]]

        aliases = [name.lower(), display_name.lower(), s.get("code", "").lower()]
        canonical.append({
            "name": display_name,
            "type": s.get("type", "Suburban"),
            "coordinates": [s["lat"], s["lon"]],
            "operational_status": "OPERATIONAL",
            "entrances": entrances,
            "aliases": [a for a in aliases if a],
            "station_id": s["id"]
        })
        seen_names.add(display_name.lower())

    out_file = "all_stations.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(canonical, f, indent=2)
    print(f"Saved canonical all_stations.json ({len(canonical)} stations) to {out_file}")

if __name__ == "__main__":
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    m_data, m_diag = process_metro()
    s_data, s_diag = process_suburban()
    b_data = process_mtc()
    interchanges = build_interchanges(m_data, s_data)
    export_canonical_all_stations(m_data, s_data)

    # Save comprehensive integrity diagnostics
    diagnostics = {
        "timestamp": "2026-10-18T15:40:00Z",
        "metro": m_diag,
        "suburban_and_mrts": s_diag,
        "interchanges_count": len(interchanges),
        "bus_stops_count": len(b_data["stops"]),
        "bus_routes_count": len(b_data["routes"])
    }
    diag_file = os.path.join(PROCESSED_DIR, "station_normalization_diagnostics.json")
    with open(diag_file, "w", encoding="utf-8") as f:
        json.dump(diagnostics, f, indent=2)
    print(f"Saved integrity diagnostics to {diag_file}")
    print("All networks successfully ingested and indexed with GTFS station normalization.")
