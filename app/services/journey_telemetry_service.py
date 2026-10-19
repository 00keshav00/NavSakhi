import math
import time
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
from app.models.journey import Journey, JourneyStateEnum, JourneyProgress, Location

# Engineering Policy: Off-route threshold in meters.
# Guided by typical urban GPS multipath error (~15-30m) and road corridor widths (~30-50m).
# A reading further than 150m from the planned centerline is classified as deviating.
# This is an operational route-tracking tolerance, not a validated personal-safety boundary.
DEFAULT_OFF_ROUTE_THRESHOLD_METERS = 150.0
EARTH_RADIUS_METERS = 6371000.0

def haversine_distance_meters(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Calculates geodesic distance between two points in meters using Haversine formula."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_METERS * c

def extract_route_coordinates(journey: Journey, selected_route_id: Optional[str] = None) -> List[Tuple[float, float]]:
    """
    Extracts ordered [lon, lat] coordinate list from the planned routes on the journey.
    Prioritizes selected_route_id or first available recommended route.
    """
    if not journey.planned_routes:
        return []

    target_route = None
    if selected_route_id:
        for r in journey.planned_routes:
            if r.get("id") == selected_route_id:
                target_route = r
                break

    if not target_route and journey.planned_routes:
        target_route = journey.planned_routes[0]

    if not target_route:
        return []

    coords: List[Tuple[float, float]] = []
    segments = target_route.get("segments", [])
    for seg in segments:
        polyline = seg.get("polyline")
        if not polyline or not isinstance(polyline, dict):
            continue
        geom = polyline.get("geometry", {})
        if not geom or not isinstance(geom, dict):
            continue
        g_coords = geom.get("coordinates", [])
        if not isinstance(g_coords, list):
            continue

        for pt in g_coords:
            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                try:
                    lon = float(pt[0])
                    lat = float(pt[1])
                    if math.isfinite(lon) and math.isfinite(lat):
                        coords.append((lon, lat))
                except (ValueError, TypeError):
                    continue

    return coords

def project_point_to_route(
    user_lon: float,
    user_lat: float,
    route_coords: List[Tuple[float, float]],
    prior_dist_along: Optional[float] = None
) -> Tuple[float, float, float]:
    """
    Projects a GPS point onto an ordered polyline using local equirectangular metric projection.
    Uses prior_dist_along to maintain route continuity across loops, intersections, and sharp turns.
    Returns:
        (distance_from_route_m, distance_along_route_m, total_route_length_m)
    """
    if not route_coords or len(route_coords) < 2:
        return 0.0, 0.0, 0.0

    # Precalculate segment lengths and planar projections
    lat_avg = math.radians(user_lat)
    cos_lat = math.cos(lat_avg)
    m_per_deg_lat = (math.pi * EARTH_RADIUS_METERS) / 180.0
    m_per_deg_lon = m_per_deg_lat * cos_lat

    def to_planar(lon: float, lat: float) -> Tuple[float, float]:
        return (lon * m_per_deg_lon, lat * m_per_deg_lat)

    px, py = to_planar(user_lon, user_lat)

    segment_lengths: List[float] = []
    cumulative_lengths: List[float] = [0.0]

    for i in range(len(route_coords) - 1):
        p1 = route_coords[i]
        p2 = route_coords[i + 1]
        seg_len = haversine_distance_meters(p1[0], p1[1], p2[0], p2[1])
        segment_lengths.append(seg_len)
        cumulative_lengths.append(cumulative_lengths[-1] + seg_len)

    total_route_length = cumulative_lengths[-1]
    if total_route_length <= 0.0:
        return 0.0, 0.0, 0.0

    candidates = []
    min_dist_from_route = float("inf")

    for i in range(len(route_coords) - 1):
        ax, ay = to_planar(route_coords[i][0], route_coords[i][1])
        bx, by = to_planar(route_coords[i + 1][0], route_coords[i + 1][1])

        vx = bx - ax
        vy = by - ay
        v_len_sq = vx * vx + vy * vy

        if v_len_sq == 0.0:
            continue

        # Projection scalar t
        wx = px - ax
        wy = py - ay
        t = (wx * vx + wy * vy) / v_len_sq
        t_clamped = max(0.0, min(1.0, t))

        # Nearest point on segment
        nx = ax + t_clamped * vx
        ny = ay + t_clamped * vy

        dist = math.hypot(px - nx, py - ny)
        seg_len = segment_lengths[i]
        along = cumulative_lengths[i] + t_clamped * seg_len

        candidates.append((dist, along, i))
        if dist < min_dist_from_route:
            min_dist_from_route = dist

    if not candidates:
        return 0.0, 0.0, total_route_length

    # Route Continuity Resolution:
    # If prior_dist_along is supplied, prefer segments that align with progressive traversal
    # to avoid jumping between loops, cloverleafs, or nearby road segments.
    best_along_route = 0.0
    if prior_dist_along is not None and prior_dist_along > 0:
        # Candidate window: allow slight backward jitter (50m) and progressive forward movement (600m)
        plausible_candidates = [
            c for c in candidates
            if (c[0] <= min_dist_from_route + 35.0) and
               (prior_dist_along - 50.0 <= c[1] <= prior_dist_along + 600.0)
        ]
        if plausible_candidates:
            # Pick the candidate in the forward window with the lowest distance to route
            best_c = min(plausible_candidates, key=lambda c: (c[0], abs(c[1] - prior_dist_along)))
            min_dist_from_route = best_c[0]
            best_along_route = best_c[1]
        else:
            best_c = min(candidates, key=lambda c: c[0])
            min_dist_from_route = best_c[0]
            best_along_route = best_c[1]
    else:
        best_c = min(candidates, key=lambda c: c[0])
        min_dist_from_route = best_c[0]
        best_along_route = best_c[1]

    return min_dist_from_route, best_along_route, total_route_length


class JourneyTelemetryService:
    """
    Core engine for validating GPS telemetry, calculating metric route progress,
    enforcing lifecycle transitions, and rate limiting incoming updates.
    """
    def __init__(self, off_route_threshold_m: float = DEFAULT_OFF_ROUTE_THRESHOLD_METERS):
        self.off_route_threshold_m = off_route_threshold_m
        # Rate-limiting cache: journey_id -> list of unix timestamps (last 1 second)
        self._rate_limit_cache: Dict[str, List[float]] = {}
        # Max updates allowed per second per journey
        self.max_rate_per_sec = 5

    def check_rate_limit(self, journey_id: str) -> bool:
        """Returns True if within rate limit, False if exceeded."""
        now = time.time()
        timestamps = self._rate_limit_cache.get(journey_id, [])
        # Keep only timestamps within the last 1.0 second
        timestamps = [t for t in timestamps if now - t < 1.0]
        if len(timestamps) >= self.max_rate_per_sec:
            self._rate_limit_cache[journey_id] = timestamps
            return False
        timestamps.append(now)
        self._rate_limit_cache[journey_id] = timestamps
        return True

    def calculate_progress(
        self,
        journey: Journey,
        user_lon: float,
        user_lat: float,
        accuracy: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculates metric progress along planned route geometry.
        """
        route_coords = extract_route_coordinates(journey, journey.selected_route_id)
        if not route_coords or len(route_coords) < 2:
            return {
                "distance_from_route_m": None,
                "distance_remaining_m": 0.0,
                "progress_percentage": 0.0,
                "is_on_route": True,
                "status": "unavailable",
                "total_route_length_m": 0.0,
            }

        prior_dist_along = None
        if journey.progress and journey.progress.distance_covered is not None:
            prior_dist_along = journey.progress.distance_covered

        dist_from_route, dist_along, total_length = project_point_to_route(
            user_lon, user_lat, route_coords, prior_dist_along=prior_dist_along
        )

        progress_pct = round((dist_along / total_length) * 100.0, 1) if total_length > 0 else 0.0
        progress_pct = max(0.0, min(100.0, progress_pct))
        distance_remaining = max(0.0, round(total_length - dist_along, 1))

        # Effective threshold accounts for reported GPS accuracy
        effective_threshold = self.off_route_threshold_m
        if accuracy is not None and accuracy > 0:
            effective_threshold = max(self.off_route_threshold_m, min(300.0, accuracy + 50.0))

        is_on_route = dist_from_route <= effective_threshold

        # Progress calculation informs telemetry status but NEVER marks the journey
        # completed automatically. Journey completion is strictly an explicit user action.
        if is_on_route:
            status = "on_route"
        else:
            status = "deviating"

        return {
            "distance_from_route_m": round(dist_from_route, 1),
            "distance_remaining_m": distance_remaining,
            "progress_percentage": progress_pct,
            "is_on_route": is_on_route,
            "status": status,
            "total_route_length_m": round(total_length, 1),
        }

    def process_telemetry_message(
        self,
        journey: Journey,
        message: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validates, rate-limits, and evaluates an incoming telemetry message.
        Returns:
            (is_valid, response_or_error_dict)
        """
        journey_id = str(journey.id)

        # 1. Extract and validate coordinates
        raw_lat = message.get("lat") if "lat" in message else message.get("latitude")
        raw_lng = message.get("lng") if "lng" in message else message.get("longitude")

        if raw_lat is None or raw_lng is None:
            return False, {
                "status": "rejected",
                "error": "Coordinates missing. 'lat' and 'lng' are required."
            }

        try:
            lat = float(raw_lat)
            lng = float(raw_lng)
        except (ValueError, TypeError):
            return False, {
                "status": "rejected",
                "error": "Coordinates must be numeric."
            }

        if not (math.isfinite(lat) and math.isfinite(lng)):
            return False, {
                "status": "rejected",
                "error": "Coordinates must be finite numbers."
            }

        if not (-90.0 <= lat <= 90.0):
            return False, {
                "status": "rejected",
                "error": "Latitude must be between -90 and 90"
            }

        if not (-180.0 <= lng <= 180.0):
            return False, {
                "status": "rejected",
                "error": "Longitude must be between -180 and 180"
            }

        # 2. State check
        current_state = journey.state.current_state
        if current_state in [JourneyStateEnum.COMPLETED, JourneyStateEnum.CANCELLED, JourneyStateEnum.FAILED]:
            return False, {
                "status": "rejected",
                "error": f"Journey is {current_state.value}. Tracking updates are no longer accepted."
            }

        if current_state == JourneyStateEnum.PAUSED:
            return False, {
                "status": "rejected",
                "error": "Journey is paused. Resume the journey before sending location updates."
            }

        if current_state not in [JourneyStateEnum.ACTIVE, JourneyStateEnum.MONITORING]:
            return False, {
                "status": "rejected",
                "error": f"Journey must be ACTIVE or MONITORING to process telemetry. Current state: {current_state.value}"
            }

        # 3. Rate limiting
        if not self.check_rate_limit(journey_id):
            return False, {
                "status": "rejected",
                "error": "Rate limit exceeded. Maximum 5 location updates per second."
            }

        # 4. Accuracy and Timestamp validation
        accuracy = None
        if "accuracy" in message and message["accuracy"] is not None:
            try:
                acc_val = float(message["accuracy"])
                if math.isfinite(acc_val) and acc_val >= 0:
                    accuracy = acc_val
            except (ValueError, TypeError):
                pass

        # Check timestamp monotonically with clock-skew bounds
        msg_time: Optional[float] = None
        if "timestamp" in message and message["timestamp"] is not None:
            try:
                raw_t = message["timestamp"]
                if isinstance(raw_t, (int, float)):
                    # Timestamp in ms or s
                    msg_time = raw_t / 1000.0 if raw_t > 1e11 else float(raw_t)
                elif isinstance(raw_t, str):
                    # ISO string
                    dt = datetime.fromisoformat(raw_t.replace("Z", "+00:00"))
                    msg_time = dt.timestamp()
            except Exception:
                msg_time = None

        server_now = time.time()
        MAX_FUTURE_SKEW_SECONDS = 60.0  # 60s max acceptable client clock forward skew

        if msg_time is not None:
            if msg_time > server_now + MAX_FUTURE_SKEW_SECONDS:
                return False, {
                    "status": "rejected",
                    "error": "Telemetry timestamp is too far in the future."
                }
            if journey.last_telemetry_timestamp is not None:
                # Reject updates older than or identical to latest accepted update
                if msg_time <= journey.last_telemetry_timestamp:
                    return False, {
                        "status": "rejected",
                        "error": "Stale or out-of-order telemetry timestamp rejected."
                    }
        else:
            msg_time = server_now

        # 5. Plausible velocity / location jump check
        if (
            journey.progress
            and journey.progress.current_location
            and journey.progress.current_location.coordinates
            and journey.last_telemetry_timestamp is not None
        ):
            dt = msg_time - journey.last_telemetry_timestamp
            if 0 < dt < 300:  # Only evaluate for short interval transitions
                prev_lon = journey.progress.current_location.coordinates[0]
                prev_lat = journey.progress.current_location.coordinates[1]
                jump_dist = haversine_distance_meters(prev_lon, prev_lat, lng, lat)
                # Maximum plausible speed: 150 m/s (~540 km/h)
                if jump_dist > 500.0 and (jump_dist / dt) > 150.0:
                    return False, {
                        "status": "rejected",
                        "error": "Implausibly large location jump rejected."
                    }

        # Calculate progress
        calc_result = self.calculate_progress(journey, lng, lat, accuracy)

        # Build response payload
        ack_payload = {
            "type": "telemetry_ack",
            "status": "acknowledged",
            "journey_id": journey_id,
            "progress_percentage": calc_result["progress_percentage"],
            "distance_remaining_m": calc_result["distance_remaining_m"],
            "distance_from_route_m": calc_result["distance_from_route_m"],
            "is_on_route": calc_result["is_on_route"],
            "status_label": calc_result["status"],
            "timestamp": datetime.utcnow().isoformat(),
            "location": {"lat": lat, "lng": lng, "accuracy": accuracy}
        }

        # Return success with updated fields for persistence
        persistence_data = {
            "lat": lat,
            "lng": lng,
            "accuracy": accuracy,
            "timestamp": msg_time,
            "calc_result": calc_result
        }

        return True, {"ack": ack_payload, "persistence": persistence_data}

telemetry_service = JourneyTelemetryService()
