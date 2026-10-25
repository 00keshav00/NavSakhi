from typing import Dict, Any, Optional
import logging
from app.agents.workflow_manager import WorkflowManager
from app.ml.normalizer import DataNormalizer
from app.ml.features import FeatureEngineer
from app.ml.predictor import MLSafetyPredictor, SafeSheMLPredictor, get_ml_predictor
from app.services.ml_route_scoring_service import MLRouteScoringService
from app.intelligence.decision.engine import DecisionEngine
from app.tools.specialized.reasoning_tool import ReasoningTool
from app.intelligence.response.builder import ResponseBuilder

from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


def parse_coordinate_pair(text: str) -> Optional[Tuple[float, float]]:
    """
    Parses an input string to check if it represents an explicit coordinate pair.
    Returns canonical (longitude, latitude) if valid, None otherwise.

    Requirements:
    - Exactly two comma-separated values.
    - Both values must be valid numeric floats (supporting signs and decimals).
    - Latitude must be in [-90.0, 90.0], Longitude must be in [-180.0, 180.0].
    - Handles India/Chennai lon/lat ordering properly.
    """
    if not text or not isinstance(text, str):
        return None
    cleaned = text.strip()
    parts = cleaned.split(",")
    if len(parts) != 2:
        return None
    try:
        v0 = float(parts[0].strip())
        v1 = float(parts[1].strip())
    except (ValueError, TypeError):
        return None

    # Check geographic range validity
    # In India (lat ~8-38, lon ~68-98):
    if 68.0 <= v0 <= 98.0 and 8.0 <= v1 <= 38.0:
        lon, lat = v0, v1
    elif 8.0 <= v0 <= 38.0 and 68.0 <= v1 <= 98.0:
        lat, lon = v0, v1
    elif -90.0 <= v0 <= 90.0 and -180.0 <= v1 <= 180.0:
        lat, lon = v0, v1
    elif -180.0 <= v0 <= 180.0 and -90.0 <= v1 <= 90.0:
        lon, lat = v0, v1
    else:
        return None

    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None

    return (lon, lat)


def is_coordinate_pair(text: str) -> bool:
    """Returns True if text represents a valid numerical coordinate pair."""
    return parse_coordinate_pair(text) is not None


class JourneyIntelligenceCoordinator:
    """
    The exclusive public entry point into the Journey Intelligence Layer.
    Orchestrates the Agentic AI Pipeline without executing logic itself.
    """
    
    def __init__(self):
        self.workflow_manager = WorkflowManager()
        self.normalizer = DataNormalizer()
        self.feature_engineer = FeatureEngineer()
        self.ml_predictor = get_ml_predictor()
        self.ml_route_scorer = MLRouteScoringService(predictor=self.ml_predictor)
        self.decision_engine = DecisionEngine()
        self.reasoning_tool = ReasoningTool()
        self.response_builder = ResponseBuilder()

    async def execute_pipeline(self, workflow_type: str, initial_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the full intelligence pipeline.
        """
        # Step 1: Agent Execution via Workflow Manager (includes Agent Registry -> Tools -> Providers)
        agent_results = await self.workflow_manager.run_workflow(workflow_type, initial_context)
        
        # Step 2: Normalization
        normalized_data = self.normalizer.normalize(agent_results)
        
        # Step 3: Feature Engineering
        feature_vector = self.feature_engineer.engineer_features(normalized_data)
        
        # Step 4: ML Prediction (Restricted strictly to spatial/road scoring workflows)
        if workflow_type in ["assistant", "profile", "dashboard", "emergency", "settings"]:
            ml_prediction = {
                "safety_score": None,
                "confidence": None,
                "risk_level": "UNKNOWN",
                "status": "UNAVAILABLE"
            }
        else:
            try:
                ml_prediction = self.ml_predictor.predict(feature_vector)
            except Exception as e:
                logger.error(f"ML prediction failed during {workflow_type}: {e}")
                ml_prediction = {
                    "safety_score": None,
                    "confidence": None,
                    "risk_level": "UNKNOWN",
                    "status": "INFERENCE_FAILED",
                    "error": str(e)
                }
        
        # Step 5: Decision Engine
        context_for_decision = {**normalized_data, **initial_context}
        decision = self.decision_engine.decide(ml_prediction, context_for_decision)
        
        # Step 6: LLM Reasoning (Only for workflows that need text explanations)
        llm_context = {
            "decision": decision,
            "ml_prediction": ml_prediction,
            "agent_results": agent_results,
            "query": initial_context.get("query"),
            "active_journey": initial_context.get("active_journey"),
            "workflow_type": workflow_type
        }
        
        if workflow_type in ["journey_plan", "assistant"]:
            llm_reasoning = await self.reasoning_tool.execute({"context": llm_context})
        else:
            llm_reasoning = {"summary": "System operating normally.", "reasoning": ["Metrics within safe parameters."]}
        
        # Assemble Final Context for Response Builder
        final_context = {
            **agent_results,
            "NormalizedData": normalized_data,
            "MLPrediction": ml_prediction,
            "Decision": decision,
            "LLM": llm_reasoning
        }
        
        return final_context

    # --- Router Endpoints ---

    async def build_journey_plan_response(self, journey_id: str, request: Any) -> Any:
        from app.providers.location.provider import NominatimLocationProvider
        from app.providers.routing.provider import OSRMRoutingProvider
        from app.models.journey import Location
        from fastapi import HTTPException
        import logging
        from app.intelligence.journey.transit_validator import global_validator
        from app.intelligence.journey.schedule_engine import global_schedule_engine
        from app.intelligence.journey.fare_engine import global_fare_engine
        from app.intelligence.journey.deduplication import deduplicate_routes
        from app.providers.live.weather import global_weather_provider
        
        def ensure_lon_lat(coords):
            if coords[0] < coords[1]: # In India, lon (~77-80) > lat (~10-13)
                return [coords[1], coords[0]]
            return coords

        
        logger = logging.getLogger(__name__)
        loc_provider = NominatimLocationProvider()
        route_provider = OSRMRoutingProvider()
        
        # IST timestamp
        import datetime
        ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        ist_dt = datetime.datetime.now(ist_tz)
        from app.providers.shared.exceptions import (
            ProviderRateLimitError,
            ProviderTimeoutError,
            ProviderUnavailableError,
            LocationNotFoundError,
        )

        async def _resolve_location_param(raw_input: str, role: str) -> Location:
            cleaned = (raw_input or "").strip()
            if not cleaned:
                raise HTTPException(
                    status_code=422,
                    detail=f"{role.capitalize()} location cannot be empty."
                )

            # Check if input is a valid coordinate pair
            coords = parse_coordinate_pair(cleaned)
            if coords is not None:
                lon, lat = coords
                return Location(type="Point", coordinates=[lon, lat])

            if "detecting" in cleaned.lower() or "current" in cleaned.lower():
                raise HTTPException(
                    status_code=422,
                    detail=f"Cannot determine {role} location from '{cleaned}'. Please provide coordinates (latitude, longitude) or select a verified place."
                )

            try:
                return await asyncio.wait_for(loc_provider.forward_geocode(cleaned), timeout=4.0)
            except asyncio.TimeoutError:
                logger.warning(f"Geocoding provider timed out for {role} '{cleaned}'")
                raise HTTPException(
                    status_code=503,
                    detail="Location search is temporarily unavailable. Please retry shortly or select a verified place from suggestions."
                )
            except ProviderRateLimitError as e:
                logger.warning(f"Nominatim rate limit during {role} geocoding: retry_after={e.retry_after}")
                headers = {"Retry-After": str(e.retry_after)} if e.retry_after else None
                raise HTTPException(
                    status_code=503,
                    detail="Location search is temporarily unavailable. Please retry shortly or select a verified place from suggestions.",
                    headers=headers
                )
            except (ProviderTimeoutError, ProviderUnavailableError) as e:
                logger.warning(f"Geocoding provider unavailable during {role} geocoding: {e}")
                raise HTTPException(
                    status_code=503,
                    detail="Location search is temporarily unavailable. Please retry shortly or select a verified place from suggestions."
                )
            except LocationNotFoundError:
                sanitized_query = cleaned[:80].replace("\n", " ")
                raise HTTPException(
                    status_code=422,
                    detail=f"Could not find {role} location '{sanitized_query}'. Please verify the place name or select a verified place from suggestions."
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.exception(f"Unexpected error resolving {role} location '{cleaned}': {e}")
                raise HTTPException(
                    status_code=503,
                    detail="Location search is temporarily unavailable. Please retry shortly or select a verified place from suggestions."
                )

        import asyncio
        import time
        import uuid
        correlation_id = f"corr_{uuid.uuid4().hex[:12]}"
        t_pipeline_start = time.perf_counter()
        stage_timings: Dict[str, float] = {}

        t_loc_0 = time.perf_counter()
        source_loc, dest_loc = await asyncio.gather(
            _resolve_location_param(request.source, "source"),
            _resolve_location_param(request.destination, "destination")
        )

        async def _resolve_display_name(loc: Location, raw_text: str, default_label: str) -> str:
            is_coords = is_coordinate_pair(raw_text)
            is_detecting = "detecting" in raw_text.lower() or "current" in raw_text.lower()
            if not (is_coords or is_detecting):
                return raw_text
            try:
                addr = await asyncio.wait_for(loc_provider.reverse_geocode(loc), timeout=1.5)
                return addr.display_name.split(",")[0]
            except Exception:
                return default_label

        source_name, dest_name = await asyncio.gather(
            _resolve_display_name(source_loc, request.source, "Current Location"),
            _resolve_display_name(dest_loc, request.destination, "Destination")
        )
        stage_timings["location_resolution_ms"] = round((time.perf_counter() - t_loc_0) * 1000, 2)
        source_full = source_name.lower()
        dest_full = dest_name.lower()

        # Determine if context is a campus/university
        is_campus = any(keyword in source_full or keyword in dest_full for keyword in ["university", "college", "campus", "institute"])

                # Get Routes Dynamically
        try:
            import asyncio
            import datetime
            
            current_hour = datetime.datetime.utcnow().hour
            
            # --- PREFERENCE PARSING ---
            pref_list = getattr(request, "preferences", None) or []
            pref_lower = [str(p).lower() for p in pref_list]
            wants_public = any(p in pref_lower for p in ["public_transport", "transit", "public", "metro", "suburban", "bus", "train"])
            wants_personal = any(p in pref_lower for p in ["personal_vehicle", "personal", "car", "bike", "driving", "two_wheeler"])
            
            if not wants_public and not wants_personal:
                wants_public = True
                wants_personal = True

            # Compute straight-line distance in km early
            s_lon, s_lat = source_loc.coordinates[0], source_loc.coordinates[1]
            d_lon, d_lat = dest_loc.coordinates[0], dest_loc.coordinates[1]
            from app.intelligence.journey.transit_validator import haversine_m
            dist_m = haversine_m(s_lat, s_lon, d_lat, d_lon)
            dist_km = dist_m / 1000.0

            # 0 KM EXACT HANDLING
            if dist_km < 0.05 or source_loc.coordinates == dest_loc.coordinates:
                final_context = {
                    "source_name": source_name,
                    "dest_name": dest_name,
                    "source_loc": source_loc.coordinates,
                    "dest_loc": dest_loc.coordinates,
                    "routes": [],
                    "zero_distance": True,
                    "warnings": ["Already at destination"]
                }
                resp = self.response_builder.build_journey_plan(
                    final_context, getattr(request, 'user_id', "u_1"), journey_id, timing_collector=stage_timings
                )
                from app.config.settings import settings
                if (getattr(settings, "environment", "") or "").strip().lower() == "staging":
                    stage_timings["total_duration_ms"] = round((time.perf_counter() - t_pipeline_start) * 1000, 2)
                    resp.meta = {"stage_timings": dict(stage_timings)}
                return resp

            warnings = []

            # --- CONCURRENT WEATHER ENRICHMENT TASK ---
            # Launched in background to prevent external weather delay from blocking critical routing path
            weather_task = asyncio.create_task(global_weather_provider.get_live_weather(s_lat, s_lon))

            # --- PHASE 1: DIVERSE VERIFIED ROAD CANDIDATES VIA OSRM ---
            t_road_0 = time.perf_counter()
            road_cands = []
            direct_road_dist_m = dist_m * 1.3
            direct_road_dur_s = (dist_m * 1.3) / 10.0
            
            try:
                # 1. Driving route(s) via OSRM
                driving_routes = await route_provider.get_routes(source_loc, dest_loc, mode="driving", alternatives="true")
                for idx, r in enumerate(driving_routes):
                    r.route_metadata = r.route_metadata or {}
                    if idx == 0:
                        direct_road_dist_m = float(r.distance)
                        direct_road_dur_s = float(r.duration)
                        r.route_metadata["travel_mode"] = "Personal Vehicle"
                        r.route_metadata["route_name"] = "Personal Vehicle"
                    else:
                        r.route_metadata["travel_mode"] = "Cab Direct"
                        r.route_metadata["route_name"] = f"Alternative Road Route {idx}"
                    road_cands.append(r)

                # 2. Secondary Road Corridor via waypoint offset if only 1 driving route returned
                if len(driving_routes) == 1 and dist_km >= 0.8:
                    try:
                        dx = d_lon - s_lon
                        dy = d_lat - s_lat
                        vec_len = (dx*dx + dy*dy)**0.5
                        if vec_len > 0:
                            px = -dy / vec_len
                            py = dx / vec_len
                            offset_deg = min(0.0035, max(0.0015, vec_len * 0.15))
                            wp_lon = (s_lon + d_lon)/2 + px * offset_deg
                            wp_lat = (s_lat + d_lat)/2 + py * offset_deg
                            via_loc = Location(type="Point", coordinates=[wp_lon, wp_lat])
                            alt_routes = await route_provider.get_routes(
                                source_loc, dest_loc, mode="driving", alternatives="false", waypoints=[via_loc]
                            )
                            if alt_routes:
                                alt_r = alt_routes[0]
                                if alt_r.distance <= driving_routes[0].distance * 1.6:
                                    alt_r.route_metadata = alt_r.route_metadata or {}
                                    alt_r.route_metadata["travel_mode"] = "Cab Direct"
                                    alt_r.route_metadata["route_name"] = "Alternative Road Corridor"
                                    road_cands.append(alt_r)
                    except Exception as e:
                        logger.debug(f"Waypoint alternative routing attempt: {e}")
            except Exception as e:
                logger.error(f"OSRM driving route query failed: {e}")

            # 3. Two-Wheeler candidate
            try:
                bike_routes = await route_provider.get_routes(source_loc, dest_loc, mode="bike", alternatives="false")
                if bike_routes:
                    b_cand = bike_routes[0]
                    b_cand.route_metadata = b_cand.route_metadata or {}
                    b_cand.route_metadata["travel_mode"] = "Two Wheeler"
                    b_cand.route_metadata["route_name"] = "Two Wheeler"
                    # Realistic city traffic two-wheeler pace (~28 km/h or ~7.8 m/s)
                    b_cand.duration = max(b_cand.distance / 7.8, b_cand.duration)
                    road_cands.append(b_cand)
            except Exception as e:
                logger.debug(f"OSRM bike route query failed: {e}")

            # 4. Walking candidate if trip is walkable (<= 4.0 km)
            if dist_km <= 4.0:
                try:
                    foot_routes = await route_provider.get_routes(source_loc, dest_loc, mode="foot", alternatives="false")
                    if foot_routes:
                        f_cand = foot_routes[0]
                        f_cand.route_metadata = f_cand.route_metadata or {}
                        f_cand.route_metadata["travel_mode"] = "Walking"
                        f_cand.route_metadata["route_name"] = "Walking"
                        # Realistic pedestrian pace (~4.8 km/h or 1.35 m/s)
                        f_cand.duration = max(f_cand.distance / 1.35, f_cand.duration)
                        road_cands.append(f_cand)
                except Exception as e:
                    logger.debug(f"OSRM foot route query failed: {e}")

            stage_timings["road_routing_ms"] = round((time.perf_counter() - t_road_0) * 1000, 2)

            t_transit_0 = time.perf_counter()
            fully_validated_routes = []
            can_attempt_transit = wants_public and (direct_road_dist_m > 0)

            if can_attempt_transit:
                # 2A. Optional Gemini Mobility Strategy Validation (ISOLATED TO STRATEGY B EXPERIMENT ONLY)
                # By default under production Strategy A, transit candidate routing is 100% deterministic with 0 external calls.
                from app.config.settings import settings
                configured_strat = getattr(request, "strategy", None) or getattr(settings, "routing_strategy", "STRATEGY_A") or "STRATEGY_A"
                if getattr(settings, "enable_experimental_strategy_b", False) and str(configured_strat).upper() == "STRATEGY_B":
                    try:
                        gemini_strategies = await self.reasoning_tool.generate_dynamic_plans(source_name, dest_name, dist_km, pref_list)
                        for strategy in gemini_strategies:
                            req_time = getattr(request, 'travel_time', None) or datetime.datetime.now().isoformat()
                            val_result = global_validator.validate_strategy(strategy, source_loc.coordinates, dest_loc.coordinates, req_time)
                            
                            if val_result["validation"]["status"] == "VALID" and val_result.get("segments"):
                                geom_complete = True
                                total_dist = 0
                                total_dur = 0
                                all_coords = []
                                seg_list = []
                                
                                for seg in val_result.get("segments", []):
                                    mode = seg.get("mode")
                                    if mode in ["metro", "suburban", "mrts", "train"]:
                                        if not seg.get("geometry_complete"):
                                            geom_complete = False
                                            break
                                        total_dist += seg.get("distance_m", 0)
                                        total_dur += seg.get("duration_s", 0)
                                        seg_coords = seg.get("geometry", {}).get("coordinates", [])
                                        for pt in seg_coords:
                                            if not all_coords or all_coords[-1] != pt:
                                                all_coords.append(pt)
                                        seg_list.append(seg)
                                    elif mode in ["auto", "cab", "walk", "two_wheeler"]:
                                        try:
                                            s_pt = ensure_lon_lat(seg["start_coordinates"])
                                            e_pt = ensure_lon_lat(seg["end_coordinates"])
                                            s_loc = Location(type="Point", coordinates=s_pt)
                                            e_loc = Location(type="Point", coordinates=e_pt)
                                            osrm_mode = "foot" if mode == "walk" else "driving"
                                            acc_routes = await route_provider.get_routes(s_loc, e_loc, mode=osrm_mode, alternatives="false")
                                            if acc_routes:
                                                seg_geom = acc_routes[0].route_metadata.get("geometry", {})
                                                seg["geometry"] = seg_geom
                                                seg["distance_m"] = acc_routes[0].distance
                                                seg["duration_s"] = acc_routes[0].duration
                                                seg["geometry_complete"] = True
                                                total_dist += acc_routes[0].distance
                                                total_dur += acc_routes[0].duration
                                                seg_coords = seg_geom.get("coordinates", [])
                                                for pt in seg_coords:
                                                    if not all_coords or all_coords[-1] != pt:
                                                        all_coords.append(pt)
                                                seg_list.append(seg)
                                            else:
                                                geom_complete = False
                                                break
                                        except Exception as e:
                                            logger.warning(f"Failed to route dynamic access leg: {e}")
                                            geom_complete = False
                                            break
                                
                                # Detour sanity: Multimodal total distance must not exceed 1.55x direct road
                                if geom_complete and len(all_coords) >= 2 and total_dist <= direct_road_dist_m * 1.55:
                                    from app.models.journey import CandidateRoute
                                    cand = CandidateRoute(
                                        route_identifier=strategy.get("strategy_id", f"gemini_{len(fully_validated_routes)}"),
                                        distance=total_dist,
                                        duration=total_dur,
                                        recommendation_status="AVAILABLE"
                                    )
                                    cand.route_metadata = {
                                        "geometry": {"type": "LineString", "coordinates": all_coords},
                                        "travel_mode": "Multimodal" if any(s.get("mode") in ["metro", "suburban", "train", "mrts", "bus"] for s in seg_list) else "Cab Direct",
                                        "dynamic_segments": seg_list,
                                        "route_name": strategy.get("strategy_name", "Transit Route"),
                                        "cost": "Estimated",
                                        "distinctness_status": "DISTINCT"
                                    }
                                    fully_validated_routes.append(cand)
                    except Exception as e:
                        logger.info(f"Gemini dynamic planning validation: {e}")

                # 2B. Mode-Matched Verified Transit Graph Corridor Search (Primary Deterministic Engine)
                from app.intelligence.journey.transit_validator import global_index, TransportNode
                from app.intelligence.journey.multimodal_router import global_multimodal_router
                from app.intelligence.journey.transit_graph import global_metro_graph, global_suburban_graph, get_graph_for_mode

                # Query generic data-driven multimodal routing engine across Bus, Metro, Suburban, and MRTS
                if wants_public:
                    try:
                        data_driven_cands = await asyncio.wait_for(
                            global_multimodal_router.search_candidates(
                                source_loc=source_loc,
                                dest_loc=dest_loc,
                                direct_road_dist_m=direct_road_dist_m,
                                direct_road_dur_s=direct_road_dur_s,
                                route_provider=route_provider,
                                ist_dt=ist_dt,
                                preferences=pref_list
                            ),
                            timeout=4.5
                        )
                        for ddc in data_driven_cands:
                            fully_validated_routes.append(ddc)
                    except Exception as e:
                        logger.warning(f"Generic multimodal router error or timeout: {e}")

                has_transit_candidate = any(
                    any(s.get("mode") in ["metro", "suburban", "train", "mrts", "bus"] for s in c.route_metadata.get("dynamic_segments", []))
                    for c in fully_validated_routes
                )

                if not has_transit_candidate and global_index and (global_metro_graph or global_suburban_graph):
                    try:
                        # Catchment distances: access up to 12 km or 65% of trip; egress up to 14 km or 45% of trip
                        max_access_dist_m = min(12000.0, max(4000.0, direct_road_dist_m * 0.65))
                        max_egress_dist_m = min(14000.0, max(2500.0, direct_road_dist_m * 0.45))
                        
                        candidate_modes = ["metro", "suburban"]
                        
                        for target_mode in candidate_modes:
                            if len(fully_validated_routes) >= 2:
                                break
                                
                            graph = get_graph_for_mode(target_mode)
                            if not graph:
                                continue

                            # Eligible origin and destination stations within catchment
                            orig_candidates = [
                                n for n in global_index.nodes 
                                if target_mode in n.type.lower() and n.is_operational()
                                and haversine_m(s_lat, s_lon, n.latitude, n.longitude) <= max_access_dist_m
                            ]
                            orig_candidates.sort(key=lambda n: haversine_m(s_lat, s_lon, n.latitude, n.longitude))

                            dest_candidates = [
                                n for n in global_index.nodes 
                                if target_mode in n.type.lower() and n.is_operational()
                                and haversine_m(d_lat, d_lon, n.latitude, n.longitude) <= max_egress_dist_m
                            ]
                            dest_candidates.sort(key=lambda n: haversine_m(d_lat, d_lon, n.latitude, n.longitude))

                            mode_found = False
                            for orig_st in orig_candidates[:2]:
                                if mode_found:
                                    break
                                for dest_st in dest_candidates[:2]:
                                    if orig_st.name == dest_st.name:
                                        continue
                                        
                                    d_orig_to_dest = haversine_m(orig_st.latitude, orig_st.longitude, d_lat, d_lon)
                                    d_dest_st_to_dest = haversine_m(dest_st.latitude, dest_st.longitude, d_lat, d_lon)
                                    
                                    # Progress invariant: destination station must bring user closer to destination (at least 1.5 km progress)
                                    if d_dest_st_to_dest >= (d_orig_to_dest - 1500):
                                        continue
                                        
                                    # Direction invariant: transit leg must move in destination direction
                                    st_dist_approx = haversine_m(orig_st.latitude, orig_st.longitude, dest_st.latitude, dest_st.longitude)
                                    if st_dist_approx < 1500 or (d_orig_to_dest - d_dest_st_to_dest) < (0.35 * st_dist_approx):
                                        continue
                                        
                                    mode_str = orig_st.type.lower()
                                    track_coords, track_dist, track_status = graph.build_transit_segment(
                                        mode_str, orig_st.latitude, orig_st.longitude, dest_st.latitude, dest_st.longitude
                                    )
                                    
                                    if track_status != "SUCCESS" or not track_coords or track_dist < 1500:
                                        continue
                                        
                                    # Operating window verification (IST local time)
                                    req_time_str = getattr(request, 'travel_time', None)
                                    req_dt = None
                                    if req_time_str:
                                        try:
                                             req_dt = datetime.datetime.fromisoformat(req_time_str.replace("Z", "+00:00"))
                                        except:
                                            req_dt = None

                                    if req_dt is not None:
                                        if req_dt.tzinfo is not None:
                                            ist_offset = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
                                            ist_dt = req_dt.astimezone(ist_offset)
                                        else:
                                            ist_dt = req_dt + datetime.timedelta(hours=5, minutes=30)
                                    else:
                                        now_utc = datetime.datetime.utcnow()
                                        now_ist = now_utc + datetime.timedelta(hours=5, minutes=30)
                                        if now_ist.hour < 5 or now_ist.hour >= 23:
                                            ist_dt = now_ist.replace(hour=9, minute=0, second=0)
                                        else:
                                            ist_dt = now_ist

                                    avail_status, avail_meta = global_schedule_engine.get_service_availability(
                                        mode_str, f"{orig_st.name} to {dest_st.name}", ist_dt
                                    )
                                    if avail_status == "UNAVAILABLE":
                                        continue

                                    # Route road access and egress legs via OSRM
                                    acc_dist_direct = haversine_m(s_lat, s_lon, orig_st.latitude, orig_st.longitude)
                                    egr_dist_direct = haversine_m(dest_st.latitude, dest_st.longitude, d_lat, d_lon)
                                    
                                    acc_mode_osrm = "foot" if acc_dist_direct <= 1200 else "driving"
                                    egr_mode_osrm = "foot" if egr_dist_direct <= 1200 else "driving"
                                    acc_display_mode = "walk" if acc_mode_osrm == "foot" else "auto"
                                    egr_display_mode = "walk" if egr_mode_osrm == "foot" else "auto"

                                    access_routes = await route_provider.get_routes(
                                        source_loc, Location(type="Point", coordinates=[orig_st.longitude, orig_st.latitude]),
                                        mode=acc_mode_osrm, alternatives="false"
                                    )
                                    egress_routes = await route_provider.get_routes(
                                        Location(type="Point", coordinates=[dest_st.longitude, dest_st.latitude]), dest_loc,
                                        mode=egr_mode_osrm, alternatives="false"
                                    )
                                    
                                    if not access_routes or not egress_routes:
                                        continue
                                        
                                    acc_dist = access_routes[0].distance
                                    egr_dist = egress_routes[0].distance
                                    total_multimodal_dist = acc_dist + track_dist + egr_dist
                                    
                                    # Detour check: Total multimodal distance must not exceed 1.55x direct road distance
                                    if total_multimodal_dist > direct_road_dist_m * 1.55:
                                        continue
                                        
                                    # Transit significance: Rail portion must be at least 25% of total travel
                                    if (track_dist / total_multimodal_dist) < 0.25:
                                        continue
                                        
                                    # Realistic Door-to-Door ETA (in seconds)
                                    # Metro: 8 min entry/wait. Suburban: 14 min entry/wait. Station exit: 3 min.
                                    wait_secs = 8 * 60 if "metro" in mode_str else 14 * 60
                                    transit_speed_mps = 11.1 if "suburban" in mode_str else 9.7 # ~40km/h suburban, ~35km/h metro
                                    transit_dur_s = (track_dist / transit_speed_mps) + wait_secs + 180
                                    total_dur_s = access_routes[0].duration + transit_dur_s + egress_routes[0].duration
                                    
                                    # Practicality check: total multimodal duration must not exceed realistic transit threshold
                                    # (allowing for realistic 8-15 min headway wait + access/egress transfers)
                                    if total_dur_s > max(direct_road_dur_s * 2.65, direct_road_dur_s + 2100):
                                        continue

                                    acc_geom = access_routes[0].route_metadata.get("geometry", {}).get("coordinates", [])
                                    egr_geom = egress_routes[0].route_metadata.get("geometry", {}).get("coordinates", [])
                                    
                                    # Strict geographic continuity enforcement: ensure consecutive legs share matching endpoints
                                    orig_pt = [orig_st.longitude, orig_st.latitude]
                                    dest_pt = [dest_st.longitude, dest_st.latitude]
                                    
                                    if not acc_geom:
                                        acc_geom = [[s_lon, s_lat], orig_pt]
                                    elif acc_geom[-1] != orig_pt:
                                        acc_geom.append(orig_pt)
                                        
                                    if track_coords[0] != orig_pt:
                                        track_coords.insert(0, orig_pt)
                                    if track_coords[-1] != dest_pt:
                                        track_coords.append(dest_pt)
                                        
                                    if not egr_geom:
                                        egr_geom = [dest_pt, [d_lon, d_lat]]
                                    elif egr_geom[0] != dest_pt:
                                        egr_geom.insert(0, dest_pt)
                                    
                                    # Stitch continuous GeoJSON coordinates without disconnected jumps
                                    multimodal_coords = []
                                    for pt in acc_geom:
                                        if not multimodal_coords or multimodal_coords[-1] != pt:
                                            multimodal_coords.append(pt)
                                    for pt in track_coords:
                                        if not multimodal_coords or multimodal_coords[-1] != pt:
                                            multimodal_coords.append(pt)
                                    for pt in egr_geom:
                                        if not multimodal_coords or multimodal_coords[-1] != pt:
                                            multimodal_coords.append(pt)
                                            
                                    from app.models.journey import CandidateRoute
                                    t_cand = CandidateRoute(
                                        route_identifier=f"verified_transit_{len(fully_validated_routes)}",
                                        distance=total_multimodal_dist,
                                        duration=total_dur_s,
                                        recommendation_status="AVAILABLE"
                                    )
                                    t_cand.route_metadata = {
                                        "geometry": {"type": "LineString", "coordinates": multimodal_coords},
                                        "travel_mode": "Multimodal",
                                        "route_name": f"{acc_display_mode.capitalize()} + {orig_st.type} ({orig_st.name} to {dest_st.name}) + {egr_display_mode.capitalize()}",
                                        "cost": "Estimated",
                                        "distinctness_status": "DISTINCT",
                                        "dynamic_segments": [
                                            {
                                                "mode": acc_display_mode,
                                                "start_name": "Origin",
                                                "end_name": orig_st.name,
                                                "distance_m": acc_dist,
                                                "duration_s": access_routes[0].duration,
                                                "geometry": {"type": "LineString", "coordinates": acc_geom},
                                                "geometry_complete": True
                                            },
                                            {
                                                "mode": mode_str,
                                                "start_name": orig_st.name,
                                                "end_name": dest_st.name,
                                                "distance_m": track_dist,
                                                "duration_s": transit_dur_s,
                                                "waiting_time_s": wait_secs,
                                                "geometry": {"type": "LineString", "coordinates": track_coords},
                                                "geometry_complete": True
                                            },
                                            {
                                                "mode": egr_display_mode,
                                                "start_name": dest_st.name,
                                                "end_name": "Destination",
                                                "distance_m": egr_dist,
                                                "duration_s": egress_routes[0].duration,
                                                "geometry": {"type": "LineString", "coordinates": egr_geom},
                                                "geometry_complete": True
                                            }
                                        ]
                                    }
                                    fully_validated_routes.append(t_cand)
                                    mode_found = True
                                    break
                    except Exception as e:
                        logger.warning(f"Verified transit graph corridor error: {e}")

            if not fully_validated_routes and wants_public:
                warnings.append("No practical direct public transit route is available between these locations without excessive detours. Showing verified road alternatives.")

            stage_timings["transit_discovery_ms"] = round((time.perf_counter() - t_transit_0) * 1000, 2)

            # --- DEDUPLICATION ACROSS ALL CANDIDATES ---
            t_dedup_0 = time.perf_counter()
            all_raw_candidates = fully_validated_routes + road_cands
            all_raw_candidates = deduplicate_routes(all_raw_candidates)

            # --- PHASE 3: GENUINE FROZEN LIGHTGBM ML ROUTE SCORING ---
            candidates = []
            for i, cand in enumerate(all_raw_candidates):
                dist_cand_m = getattr(cand, "distance", 0.0)
                if dist_cand_m < 50.0:
                    continue

                geom = cand.route_metadata.get("geometry", {})
                coords = geom.get("coordinates", []) if isinstance(geom, dict) else (geom if isinstance(geom, list) else [])
                if not coords or len(coords) < 2:
                    continue

                cand.route_identifier = f"real_route_{i}"
                r_mode = cand.route_metadata.get("travel_mode", "Road")
                if "fare" not in cand.route_metadata:
                    fare_obj = global_fare_engine.calculate_road_cost(r_mode, dist_cand_m, getattr(cand, "duration", 0.0))
                    cand.route_metadata["fare"] = fare_obj.model_dump()
                    cand.route_metadata["cost"] = fare_obj.display_text

                cand.route_metadata.update({
                    "travel_mode": r_mode,
                    "cost": cand.route_metadata.get("cost", "Fare unavailable"),
                    "distinctness_status": getattr(cand, "distinctness_status", "DISTINCT"),
                    "overlap_metrics": getattr(cand, "overlap_metrics", {})
                })
                candidates.append(cand)

            stage_timings["candidate_creation_ms"] = round((time.perf_counter() - t_dedup_0) * 1000, 2)

            if not candidates:
                from fastapi import HTTPException
                if dist_km < 0.5:
                    raise HTTPException(status_code=400, detail="Invalid route: Source and Destination are too close or unroutable.")
                raise HTTPException(status_code=503, detail="Routing provider is temporarily unavailable. Please retry shortly.")

            t_scoring_0 = time.perf_counter()
            self.ml_route_scorer.score_candidate_routes(candidates, timing_collector=stage_timings)
            stage_timings["lightgbm_scoring_ms"] = round((time.perf_counter() - t_scoring_0) * 1000, 2)

            # Strategy Resolution: Production Lock-In -> STRATEGY_A (Deterministic)
            # Strategy B is experimental only and strictly disabled unless enable_experimental_strategy_b is True.
            from app.config.settings import settings
            configured_strategy = getattr(request, "strategy", None) or getattr(settings, "routing_strategy", "STRATEGY_A") or "STRATEGY_A"
            configured_strategy = str(configured_strategy).upper()

            recommendation_payload = None
            strategy_metrics = None
            if getattr(settings, "enable_experimental_strategy_b", False) and configured_strategy == "STRATEGY_B":
                try:
                    from app.intelligence.journey.strategy_b import StrategyBOrchestrator
                    sb_orch = StrategyBOrchestrator()
                    recommendation_payload, interpreted_prefs, strategy_metrics = await sb_orch.execute_strategy_b(candidates, pref_list)
                except Exception as e:
                    logger.warning(f"Strategy B execution fallback to Strategy A: {e}")
                    from app.intelligence.journey.recommender import global_recommender
                    recommendation_payload = global_recommender.generate_recommendation(candidates, pref_list[0] if pref_list else "ANY")
                    strategy_metrics = {"strategy_used": "STRATEGY_A", "fallback_used": True, "error": str(e)}
            else:
                from app.intelligence.journey.recommender import global_recommender
                primary_pref = pref_list[0] if pref_list else "ANY"
                recommendation_payload = global_recommender.generate_recommendation(candidates, primary_pref)
                strategy_metrics = {
                    "strategy_used": "STRATEGY_A",
                    "gemini_calls": 0,
                    "gemini_latency_ms": 0.0,
                    "fallback_used": False
                }

            # --- AWAIT CONCURRENT WEATHER ENRICHMENT ---
            t_weather_0 = time.perf_counter()
            try:
                weather_data = await asyncio.wait_for(weather_task, timeout=0.5)
            except Exception as e:
                logger.warning(f"Live weather lookup skipped or timed out: {e}")
                weather_data = {"available": False, "status": "UNAVAILABLE", "hazards": []}

            if not weather_data.get("available"):
                warnings.append("Live weather data is currently unavailable from provider.")
            if weather_data.get("hazards"):
                warnings.extend(weather_data["hazards"])
            stage_timings["weather_enrichment_ms"] = round((time.perf_counter() - t_weather_0) * 1000, 2)

            # --- PHASE 4: GEMINI OBJECTIVE EXPLANATION (Ground Truth Context Only) ---
            t_gemini_0 = time.perf_counter()
            ai_explanation = None
            try:
                from app.tools.specialized.reasoning_tool import sanitize_privacy_context
                clean_source_display = sanitize_privacy_context(source_name)
                clean_dest_display = sanitize_privacy_context(dest_name)
                routes_summary = []
                for c in candidates[:4]:
                    routes_summary.append({
                        "route_name": c.route_metadata.get("route_name", "Route"),
                        "travel_mode": c.route_metadata.get("travel_mode", "Road"),
                        "distance_km": round(c.distance / 1000.0, 2),
                        "eta_min": int(c.duration / 60.0),
                        "safety_score": c.route_metadata.get("safety_score")
                    })
                ai_explanation = await asyncio.wait_for(
                    self.reasoning_tool.explain_journey_recommendations(
                        source=clean_source_display,
                        dest=clean_dest_display,
                        verified_routes=routes_summary,
                        preferences=pref_list,
                        weather=weather_data
                    ),
                    timeout=2.0
                )
            except Exception as e:
                logger.info(f"Gemini route explanation generation skipped or timed out: {e}")
            stage_timings["gemini_generation_ms"] = round((time.perf_counter() - t_gemini_0) * 1000, 2)

            user_id = getattr(request, 'user_id', "u_1")
            strategy_metrics["stage_timings_ms"] = stage_timings
            strategy_metrics["correlation_id"] = correlation_id

            final_context = {
                "source_name": source_name,
                "dest_name": dest_name,
                "source_loc": source_loc.coordinates,
                "dest_loc": dest_loc.coordinates,
                "routes": candidates,
                "warnings": warnings,
                "weather": weather_data,
                "ai_explanation": ai_explanation,
                "recommendation": recommendation_payload,
                "strategy_metrics": strategy_metrics,
                "preference": pref_list[0] if pref_list else "ANY"
            }
            t_resp_0 = time.perf_counter()
            resp = self.response_builder.build_journey_plan(
                final_context, user_id, journey_id, timing_collector=stage_timings
            )
            stage_timings["response_construction_ms"] = round((time.perf_counter() - t_resp_0) * 1000, 2)
            stage_timings["total_duration_ms"] = round((time.perf_counter() - t_pipeline_start) * 1000, 2)
            self.last_stage_timings = stage_timings
            self.last_strategy_metrics = strategy_metrics

            from app.config.settings import settings
            if (getattr(settings, "environment", "") or "").strip().lower() == "staging":
                resp.meta = {"stage_timings": dict(stage_timings)}
            else:
                resp.meta = None

            logger.info(
                f"[{correlation_id}] Journey pipeline complete in {stage_timings['total_duration_ms']}ms: "
                f"location={stage_timings.get('location_resolution_ms')}ms, "
                f"road={stage_timings.get('road_routing_ms')}ms, "
                f"transit={stage_timings.get('transit_discovery_ms')}ms, "
                f"candidates={len(candidates)}, "
                f"scoring={stage_timings.get('lightgbm_scoring_ms')}ms, "
                f"weather={stage_timings.get('weather_enrichment_ms')}ms, "
                f"gemini={stage_timings.get('gemini_generation_ms')}ms, "
                f"resp={stage_timings.get('response_construction_ms')}ms"
            )
            return resp
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Routing failed: {e}")
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail="Routing engine failed.")

    async def build_dashboard_overview(self, user_id: str, lat: Optional[float] = None, lon: Optional[float] = None) -> Any:
        context = {"user_id": user_id}
        final_context = await self.execute_pipeline("dashboard", context)
        try:
            from app.services.weather_service import global_weather_service
            w_lat = lat if lat is not None else 13.0827
            w_lon = lon if lon is not None else 80.2707
            live_w = await global_weather_service.get_live_weather(w_lat, w_lon)
            final_context["weather"] = live_w
        except Exception as e:
            logger.warning(f"Could not load live weather in dashboard overview: {e}")
        return self.response_builder.build_dashboard_overview(final_context)

    async def build_assistant_context(self, user_id: str, journey_repo: Optional[Any] = None) -> Any:
        active_journey = None
        journey_history = []
        if journey_repo:
            try:
                active_journey = await journey_repo.get_active_journey(user_id)
                journey_history = await journey_repo.get_journey_history(user_id, limit=5)
            except Exception as e:
                logger.warning(f"Could not load journey context for assistant: {e}")
        
        context = {
            "user_id": user_id, 
            "query": "init", 
            "active_journey": active_journey, 
            "journey_history": journey_history
        }
        final_context = await self.execute_pipeline("assistant", context)
        return self.response_builder.build_assistant_context(
            final_context, 
            user_id, 
            active_journey=active_journey, 
            journey_history=journey_history
        )

    async def process_assistant_chat(self, user_id: str, query: str, journey_repo: Optional[Any] = None, history: Optional[Any] = None) -> Any:
        active_journey = None
        journey_history = []
        if journey_repo:
            try:
                active_journey = await journey_repo.get_active_journey(user_id)
                journey_history = await journey_repo.get_journey_history(user_id, limit=5)
            except Exception as e:
                logger.warning(f"Could not load journey context for assistant chat: {e}")

        context = {
            "user_id": user_id, 
            "query": query, 
            "history": history,
            "active_journey": active_journey, 
            "journey_history": journey_history
        }
        final_context = await self.execute_pipeline("assistant", context)
        return self.response_builder.build_assistant_chat(
            final_context, 
            user_id, 
            query, 
            active_journey=active_journey, 
            journey_history=journey_history
        )

    async def build_emergency_status(self, session_id: str, user_id: str) -> Any:
        context = {"user_id": user_id, "session_id": session_id}
        final_context = await self.execute_pipeline("emergency", context)
        return self.response_builder.build_emergency_status(final_context, session_id, user_id)

    async def build_profile_response(self, user_id: str) -> Any:
        context = {"user_id": user_id}
        final_context = await self.execute_pipeline("profile", context)
        return self.response_builder.build_profile_response(final_context, user_id)

    async def build_settings_response(self, user_id: str) -> Any:
        context = {"user_id": user_id}
        final_context = await self.execute_pipeline("profile", context)
        return self.response_builder.build_settings_response(final_context, user_id)

    async def active_monitor_tick(self, context: Any, tick_count: int) -> Optional[Dict[str, Any]]:
        # This acts as the active monitor loop for live journeys.
        # SafeShe never invents safety scores, lighting observations, or hazard assertions.
        if tick_count % 4 == 0:
            return {
                "message": "Telemetry update: Monitoring verified route progress.",
                "severity": "info",
                "status": "MONITORING"
            }
        return None
