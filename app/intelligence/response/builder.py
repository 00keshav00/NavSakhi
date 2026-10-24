from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def get_mode_color(mode: str) -> str:
    m = mode.lower().strip()
    if "auto" in m: return "#F97316" # Orange for Auto
    if "metro" in m: return "#8B5CF6" # Violet for Metro
    if "suburban" in m or "train" in m or "rail" in m: return "#3B82F6" # Blue for Suburban / local train
    if "mrts" in m: return "#06B6D4" # Cyan / Teal for MRTS
    if "bus" in m: return "#10B981" # Green for Government bus
    if "walk" in m: return "#EAB308" # Yellow / Gold for Walking
    if "two_wheeler" in m or "bike" in m: return "#A855F7" # Two Wheeler
    return "#0284C7" # Bright Blue for Personal vehicle / direct cab

class ResponseBuilder:

    """
    Constructs the exact Pydantic DTOs required by the frontend APIs based on the evaluated context.
    """
    def build_dashboard_overview(self, final_context: Dict[str, Any]) -> Any:
        from app.schemas.dashboard_schemas import DashboardOverviewResponse, AIStatus, SafetyScoreStatus, WeatherStatus, CommunityStatus, SystemHealthStatus, RecentJourneyItem, AlertItem, AITimelineEventItem
        import datetime
        
        dashboard_data = final_context.get("DashboardAgent", {})
        
        return DashboardOverviewResponse(
            ai_status=AIStatus(
                mode="Active Monitoring",
                health="Optimal",
                last_analysis=datetime.datetime.utcnow().isoformat(),
                recommendation="No action needed."
            ),
            safety_score=SafetyScoreStatus(
                overall=final_context.get("overall_safety", 85),
                risk_level="Low",
                confidence=final_context.get("confidence", 85.0),
                trend="Stable"
            ),
            weather=WeatherStatus(
                condition=getattr(final_context.get("weather"), "condition", "Clear"),
                temperature=int(round(getattr(final_context.get("weather"), "temperature", 25.0))),
                visibility=10,
                humidity=int(getattr(final_context.get("weather"), "humidity", 60)),
                rain_probability=int(round(getattr(final_context.get("weather"), "precipitation", 0.0) * 10)),
                apparent_temperature=getattr(final_context.get("weather"), "apparent_temperature", None),
                wind_speed=getattr(final_context.get("weather"), "wind_speed", None),
                precipitation_mm=getattr(final_context.get("weather"), "precipitation", None),
                uv_index=getattr(final_context.get("weather"), "uv_index", None),
                location_name=getattr(final_context.get("weather"), "location_name", "Chennai, Tamil Nadu"),
                provider=getattr(final_context.get("weather"), "provider", "Open-Meteo"),
                observation_timestamp=getattr(final_context.get("weather"), "observation_timestamp", None),
                status=getattr(final_context.get("weather"), "status", "AVAILABLE"),
                available=getattr(final_context.get("weather"), "available", True)
            ),
            community=CommunityStatus(
                nearby_reports=dashboard_data.get("active_journeys", 1),
                safe_zones=4,
                danger_zones=0,
                recent_activity="Normal"
            ),
            recent_alerts=[],
            ai_timeline=[],
            recent_journeys=[],
            system_health=SystemHealthStatus(
                backend="Online",
                ai_agent=dashboard_data.get("system_health", "Online"),
                latency=42,
                connected_providers=["Weather", "Routing", "MongoDB"],
                last_sync=datetime.datetime.utcnow().isoformat()
            )
        )

    def build_journey_plan(self, final_context: Dict[str, Any], user_id: str, journey_id: str) -> Any:
        from app.schemas.journey_schemas import (
            JourneyPlanResponse, SessionInfo, JourneyInformation,
            MultimodalRoute, RouteSegment, WeatherSummary, CommunitySummary, AIRecommendation,
            RoutePOI, RouteModelAttribution
        )
        import datetime
        import copy
        
        candidates = final_context.get("routes", [])
        source_name = final_context.get("source_name", "Current Location")
        dest_name = final_context.get("dest_name", "Destination")
        
        if final_context.get("zero_distance"):
            return JourneyPlanResponse(
                journey_id=journey_id,
                session_info=SessionInfo(created_at=datetime.datetime.utcnow().isoformat(), status="ACTIVE"),
                journey_information=JourneyInformation(
                    source=source_name, destination=dest_name, distance=0.0, estimated_duration=0.0
                ),
                recommended_routes=[],
                weather_summary=WeatherSummary(condition="Clear", temperature=24, hazards=[]),
                community_summary=CommunitySummary(reports_along_route=0, severity_level="Low"),
                alerts=[],
                ai_recommendation=AIRecommendation(
                    title="Already at destination",
                    summary="No travel required",
                    confidence=100,
                    reasoning="The source and destination are effectively identical.",
                    warnings=[],
                    suggested_actions=[]
                )
            )
        
        def get_color(score: int, index: int) -> str:
            if score is None: return "#9CA3AF" # Gray
            if score >= 80: return "#16A34A" # Green
            if score >= 50: return "#EAB308" # Yellow
            return "#DC2626" # Red
            
        # The user requested 3 specific scenarios: Route A (Walk->Metro->Auto), Route B (Walk->Bus->Walk), Route C (Cab Direct)
        from app.ml.predictor import get_ml_predictor
        predictor = get_ml_predictor()
        
        from app.intelligence.journey.recommender import global_recommender
        # Recommender handles objective ranking and missing data without mutating arrays
        pref = final_context.get("preference", "ANY") if isinstance(final_context, dict) else "ANY"
        rec_payload = (final_context.get("recommendation") if isinstance(final_context, dict) else None) or global_recommender.generate_recommendation(candidates, pref)
        
        # Determine actual roles
        recommended_routes = []
        if candidates:
            pass # ranking logic removed from here, driven by rec_payload
            
        for i, c in enumerate(candidates):
            if not c: continue
                
            is_rec = (c.route_identifier == rec_payload.primary_route_id) if rec_payload.primary_route_id else (i == 0)
            
            # Map labels
            labels = []
            if c.route_identifier == rec_payload.safest_route_id: labels.append("SAFEST")
            if c.route_identifier == rec_payload.fastest_route_id: labels.append("FASTEST")
            if c.route_identifier == rec_payload.balanced_route_id: labels.append("BALANCED")
            if c.route_identifier == rec_payload.lowest_cost_route_id: labels.append("LOWEST_COST")
            if is_rec: labels.append("RECOMMENDED")
            
            geo = c.route_metadata.get("geometry", {})
            if isinstance(geo, dict):
                coords = geo.get("coordinates", [])
            elif isinstance(geo, list):
                coords = geo
            else:
                coords = []
            
            # Hard validity check: candidate must have verified, continuous geometry
            if not coords or len(coords) < 2:
                logger.warning(f"Candidate {c.route_identifier} has invalid or empty geometry coordinates. Discarding unverified candidate.")
                continue
                    
            segments = []
            mode_name = c.route_metadata.get("travel_mode", "Cab Direct")
            cost_str = c.route_metadata.get("cost", "Fare unavailable")
            
            dist_km = c.distance / 1000
            eta_mins = c.duration / 60
            
            s_score = c.route_metadata.get("safety_score") # Used for sorting fallback
            env_risk = c.route_metadata.get("env_risk", 50.0)
            contrib = c.route_metadata.get("contributions", {})
            dynamic_segs = c.route_metadata.get("dynamic_segments", [])
            
            if dynamic_segs:
                # Map individually identifiable legs with verified geometries and per-leg scoring
                for idx, seg in enumerate(dynamic_segs):
                    mode = seg.get("mode", "Unknown")
                    seg_color = get_mode_color(mode)
                    
                    # Convert raw dict from coordinator to GeoJSON Feature
                    raw_geom = seg.get("geometry", {})
                    if "type" not in raw_geom or raw_geom["type"] != "Feature":
                        geojson_feature = {
                            "type": "Feature",
                            "properties": {"color": seg_color, "mode": mode, "legIndex": idx},
                            "geometry": raw_geom if raw_geom else {"type": "LineString", "coordinates": []}
                        }
                    else:
                        geojson_feature = raw_geom
                        if "properties" not in geojson_feature or not geojson_feature["properties"]:
                            geojson_feature["properties"] = {}
                        geojson_feature["properties"]["color"] = seg_color
                        geojson_feature["properties"]["mode"] = mode
                        geojson_feature["properties"]["legIndex"] = idx
                        
                    dist_km_seg = float(seg.get("distance_m", 0)) / 1000.0
                    eta_mins_seg = float(seg.get("duration_s", 0)) / 60.0
                    
                    # Leg-specific scoring - DO NOT copy overall route score to transit!
                    leg_score = seg.get("safety_score")
                    leg_score_status = seg.get("score_status")
                    if leg_score is not None:
                        leg_score = float(round(leg_score, 2))
                    
                    is_transit_leg = any(tm in mode.lower() for tm in ["metro", "suburban", "train", "mrts", "bus"])
                    if is_transit_leg:
                        leg_score = None
                        leg_score_status = "NOT_SCORED"
                        leg_reason = "Transit safety data unavailable"
                        leg_source = seg.get("score_source") or "None (Transit infrastructure unrated)"
                        leg_disclosure = seg.get("score_disclosure") or "Transit track safety assessment is not modeled by the road-segment LightGBM pipeline."
                    elif leg_score_status == "INSUFFICIENT_COVERAGE":
                        leg_score = None
                        leg_reason = "Insufficient scoreable road coverage"
                        leg_source = seg.get("score_source") or "SafeShe LightGBM Road Risk Model v2.0"
                        leg_disclosure = seg.get("score_disclosure") or "Road leg has insufficient spatial feature coverage (< 70%)."
                    else:
                        leg_reason = seg.get("validation_status", "VALID")
                        leg_source = seg.get("score_source") or "SafeShe LightGBM Road Risk Model v2.0"
                        leg_disclosure = seg.get("score_disclosure") or "Synthetic environmental safety proxy based on road infrastructure features."
                    
                    s_name = seg.get("start_name", "Start")
                    e_name = seg.get("end_name", "End")
                    
                    segments.append(RouteSegment(
                        leg_id=f"{c.route_identifier}_leg_{idx+1}",
                        sequence=idx + 1,
                        segment_name=f"{s_name} -> {e_name}",
                        transport_mode=mode.capitalize(),
                        polyline=geojson_feature,
                        color=seg_color,
                        distance=f"{dist_km_seg:.1f} km",
                        eta=f"{max(1, int(round(eta_mins_seg)))} min",
                        environmental_risk=int(env_risk),
                        adjusted_safety_score=leg_score,
                        safety_score=leg_score,
                        score_status=leg_score_status,
                        scoreable_coverage_ratio=seg.get("scoreable_coverage_ratio"),
                        score_source=leg_source,
                        score_disclosure=leg_disclosure,
                        distance_m=float(seg.get("distance_m", 0)),
                        duration_s=float(seg.get("duration_s", 0)),
                        origin=s_name,
                        destination=e_name,
                        geometry_complete=seg.get("geometry_complete", True),
                        reason=leg_reason
                    ))
            else:
                # Fallback for single direct road routes
                mode_color = get_mode_color(mode_name)
                s_stat = c.route_metadata.get("score_status", "READY" if s_score is not None else "INSUFFICIENT_COVERAGE")
                s_cov = c.route_metadata.get("scoreable_coverage_ratio", 0.0)
                s_src = "SafeShe LightGBM Road Risk Model v2.0"
                s_disc = c.route_metadata.get("target_disclosure", "Synthetic environmental safety proxy based on road infrastructure features.")
                
                segments.append(RouteSegment(
                    leg_id=f"{c.route_identifier}_leg_1",
                    sequence=1,
                    segment_name=f"{source_name} -> {dest_name}",
                    transport_mode=mode_name,
                    polyline={
                        "type": "Feature",
                        "properties": {"color": mode_color, "mode": mode_name, "legIndex": 0},
                        "geometry": {"type": "LineString", "coordinates": coords}
                    },
                    color=mode_color,
                    distance=f"{dist_km:.1f} km",
                    eta=f"{max(1, int(round(eta_mins)))} min",
                    environmental_risk=int(env_risk),
                    adjusted_safety_score=float(round(s_score, 2)) if s_score is not None else None,
                    safety_score=float(round(s_score, 2)) if s_score is not None else None,
                    score_status=s_stat,
                    scoreable_coverage_ratio=s_cov,
                    score_source=s_src,
                    score_disclosure=s_disc,
                    distance_m=float(c.distance),
                    duration_s=float(c.duration),
                    origin=source_name,
                    destination=dest_name,
                    geometry_complete=True,
                    reason="Direct route"
                ))
            
            reasons = []
            if is_rec:
                reasons = ["Recommended dynamically computed option based on live telemetry."]
            
            c.route_metadata["ranking_tags"] = labels
            
            # Construct the route name dynamically based on backend verified mode and metadata
            original_route_name = getattr(c, "route_name", None) or c.route_metadata.get("route_name")
            
            if original_route_name and "gemini" not in original_route_name.lower() and original_route_name.strip() != "":
                route_name_str = original_route_name.replace("->", "+")
            else:
                if mode_name.lower() in ["two wheeler", "bike"]:
                    route_name_str = "Two Wheeler"
                elif mode_name.lower() in ["walk", "walking"]:
                    route_name_str = "Walking"
                elif mode_name.lower() in ["four wheeler", "driving"]:
                    route_name_str = "Personal Vehicle"
                elif mode_name.lower() == "cab" or "fallback" in mode_name.lower():
                    route_name_str = "Direct Cab"
                else:
                    route_name_str = mode_name

            raw_score = c.route_metadata.get("safety_score")
            route_status = c.route_metadata.get("score_status")
            numeric_safety_score = float(round(raw_score, 2)) if (raw_score is not None and route_status == "READY") else None

            if segments:
                chain_modes = [s.transport_mode for s in segments]
                dedup_chain = []
                for m in chain_modes:
                    if not dedup_chain or dedup_chain[-1] != m:
                        dedup_chain.append(m)
                chain_str = " -> ".join(dedup_chain)
            else:
                chain_str = mode_name

            mode_lower = mode_name.lower()
            if mode_name == "Multimodal" or any(s.transport_mode.lower() in ["metro", "suburban", "train", "mrts", "bus"] for s in segments):
                mode_cat = "Public Transit"
            elif "walk" in mode_lower:
                mode_cat = "Walking"
            elif any(pv in mode_lower for pv in ["two wheeler", "four wheeler", "personal vehicle", "driving", "bike"]):
                mode_cat = "Personal Vehicle"
            elif "auto" in mode_lower:
                mode_cat = "Auto"
            else:
                mode_cat = "Cab"

            # Query verified safety facilities and commercial shops along the route corridor
            from app.services.poi_service import get_poi_service
            poi_service = get_poi_service()
            poi_query_res = poi_service.query_pois_near_route(
                coords,
                corridor_m=800.0,
                legs=[s.model_dump() for s in segments] if segments else None,
                total_duration_s=float(getattr(c, "duration", 0.0) or 0.0)
            )
            raw_pois = poi_query_res.get("pois", [])
            route_pois = [RoutePOI(**p) for p in raw_pois]

            # Evaluate dedicated Night Activity Intelligence (v2.0)
            from app.intelligence.journey.night_activity_scorer import night_activity_scorer
            night_score = night_activity_scorer.evaluate_route(coords, pass_through_hour=22)

            # Extract genuine LightGBM TreeSHAP explainability
            raw_model_attr = c.route_metadata.get("model_explainability")
            parsed_model_attr = None
            if isinstance(raw_model_attr, dict) and raw_model_attr.get("status") == "VALIDATED_ATTRIBUTION":
                try:
                    parsed_model_attr = RouteModelAttribution(**raw_model_attr)
                except Exception as attr_err:
                    logger.warning(f"Failed to parse RouteModelAttribution: {attr_err}")
                    parsed_model_attr = None

            legacy_contribs = c.route_metadata.get("contributions", {})
            if not isinstance(legacy_contribs, dict):
                legacy_contribs = {}

            raw_fare = c.route_metadata.get("fare")
            parsed_fare = None
            if isinstance(raw_fare, dict):
                try:
                    from app.schemas.journey_schemas import RouteFare
                    parsed_fare = RouteFare(**raw_fare)
                except Exception as fare_err:
                    logger.warning(f"Failed to parse RouteFare: {fare_err}")

            recommended_routes.append(MultimodalRoute(
                id=c.route_identifier + f"_{i}",
                rank=i+1,
                route_name=route_name_str,
                ranking_labels=labels,
                travel_mode_chain=chain_str,
                mode=mode_cat,
                eta=f"{int(eta_mins)} min",
                cost=cost_str,
                fare=parsed_fare,
                distance=f"{dist_km:.1f} km",
                environmental_risk=int(env_risk),
                safety_score=numeric_safety_score,
                overall_safety_score=numeric_safety_score,
                model_explainability=legacy_contribs,
                model_attribution=parsed_model_attr,
                nearby_pois=route_pois,
                activity_zones=poi_query_res.get("activity_zones", []),
                night_activity_score=night_score,
                recommendation_reason=reasons,
                segments=segments,
                is_recommended=is_rec,
                score_status=route_status,
                scoreable_coverage_ratio=c.route_metadata.get("scoreable_coverage_ratio"),
                score_basis=c.route_metadata.get("score_basis", "matched_road_segments_only"),
                model_version=c.route_metadata.get("model_version", "2.0.0"),
                target_disclosure=c.route_metadata.get("target_disclosure", "Synthetic environmental safety proxy (100.0 - risk_score_raw); not verified crime or victimization ground truth.")
            ))
            # Ensure recommended route is placed first
            recommended_routes.sort(key=lambda r: 0 if r.is_recommended else 1)
            for idx, r in enumerate(recommended_routes):
                r.rank = idx + 1
                
        recommended = recommended_routes[0] if recommended_routes else None
        
        weather_dict = final_context.get("weather", {})
        weather_cond = weather_dict.get("condition", "Clear")
        weather_temp = weather_dict.get("temperature", 25)
        if weather_temp is None:
            weather_temp = 25
        weather_hazards = weather_dict.get("hazards", [])
        
        ai_expl = final_context.get("ai_explanation")
        if ai_expl and isinstance(ai_expl, dict):
            ai_title = ai_expl.get("title", "Objective Recommendation")
            ai_summary = ai_expl.get("summary", rec_payload.explanation.primary_reason if rec_payload.explanation else "Analyzed verified infrastructure constraints.")
            ai_reasoning = ai_expl.get("reasoning", " ".join(rec_payload.explanation.tradeoffs) if rec_payload.explanation else "Determined via multi-factor backend verification.")
        else:
            ai_title = "Objective Recommendation"
            ai_summary = rec_payload.explanation.primary_reason if rec_payload.explanation else "Analyzed verified infrastructure constraints."
            ai_reasoning = " ".join(rec_payload.explanation.tradeoffs) if rec_payload.explanation else "Determined via multi-factor backend verification."
        
        return JourneyPlanResponse(
            journey_id=journey_id,
            session_info=SessionInfo(
                created_at=datetime.datetime.utcnow().isoformat(),
                status="planned"
            ),
            journey_information=JourneyInformation(
                source=source_name,
                destination=dest_name,
                distance=float(recommended.distance.split()[0]) * 1000 if recommended else 0.0,
                estimated_duration=float(recommended.eta.split()[0]) * 60 if recommended else 0.0
            ),
            recommended_routes=recommended_routes,
            weather_summary=WeatherSummary(
                condition=weather_cond, temperature=int(weather_temp), hazards=weather_hazards
            ),
            community_summary=CommunitySummary(
                reports_along_route=0, severity_level="Low"
            ),
            alerts=[],
            ai_recommendation=AIRecommendation(
                title=ai_title, 
                summary=ai_summary,
                confidence=None, 
                reasoning=ai_reasoning,
                warnings=[
                    "Model output is a synthetic environmental safety proxy; not verified crime or victimization ground truth."
                ] + (rec_payload.explanation.limitations if rec_payload.explanation else []), 
                suggested_actions=["Review the objective metrics to make an informed choice."]
            ),
            source_loc=final_context.get("source_loc"),
            dest_loc=final_context.get("dest_loc"),
            zero_distance=final_context.get("zero_distance", False),
            warnings=final_context.get("warnings", []),
        )
        
    def build_emergency_status(self, final_context: Dict[str, Any], session_id: str, user_id: str) -> Any:
        from app.schemas.emergency_schemas import EmergencyResponse, LiveLocation, AgentStatus, EmergencyTimelineEvent, EmergencyContact, EmergencySafeZone, JourneyStatus
        
        emergency = final_context.get("EmergencyAgent", {}).get("emergency_status", {})
        
        timeline = []
        for t in emergency.get("timeline", []):
            timeline.append(EmergencyTimelineEvent(**t))
            
        return EmergencyResponse(
            session_id=session_id,
            status="active",
            live_location=LiveLocation(
                coordinates=(80.2707, 13.0827),
                address="Poonamallee High Rd, Chennai",
                accuracy=15,
                last_updated="Just now"
            ),
            agent_status=AgentStatus(
                action="Staging Emergency Context & Safe Haven Routing",
                recommendation="Stay in well-lit areas if possible. Keep device accessible.",
                context="Emergency demonstration protocol initiated.",
                confidence=90,
                reason="Protocol prioritizes verified safe havens and designated contact sharing."
            ),
            timeline=timeline,
            contacts=[
                EmergencyContact(id="c1", name="Sarah Connor", relationship="Sister", notification_status="Pending")
            ],
            safe_zones=[
                EmergencySafeZone(id="s1", type="Police", name="Periamet Police Station", distance="1.2 km", eta="4 mins", coordinates=(80.2730, 13.0815))
            ],
            journey_status=JourneyStatus(
                active_journey=False,
                destination="None",
                distance_remaining="0 km",
                safety_score=None
            )
        )

    @staticmethod
    def _extract_journey_state(active_journey: Any, journey_history: Any = None) -> Dict[str, Any]:
        if not active_journey:
            recent = []
            if journey_history and isinstance(journey_history, list):
                for j in journey_history:
                    dest = getattr(j, "destination", None) or (j.get("destination") if isinstance(j, dict) else None)
                    if dest:
                        recent.append(str(dest))
            return {
                "active_journey": False,
                "source": None,
                "destination": None,
                "safety_score": None,
                "eta": None,
                "weather": None,
                "community_alerts": None,
                "emergency_status": "Normal",
                "recent_journeys": recent,
                "pinned_info": []
            }

        source_val = getattr(active_journey, "source", None) or (active_journey.get("source") if isinstance(active_journey, dict) else None)
        dest_val = getattr(active_journey, "destination", None) or (active_journey.get("destination") if isinstance(active_journey, dict) else None)
        
        source_str = "Current Location"
        if isinstance(source_val, str):
            source_str = source_val
        elif hasattr(source_val, "coordinates"):
            source_str = f"{source_val.coordinates[1]:.4f}, {source_val.coordinates[0]:.4f}"

        dest_str = "Active Destination"
        if isinstance(dest_val, str):
            dest_str = dest_val
        elif hasattr(dest_val, "coordinates"):
            dest_str = f"{dest_val.coordinates[1]:.4f}, {dest_val.coordinates[0]:.4f}"

        safety_score = None
        plan = getattr(active_journey, "plan", None) or (active_journey.get("plan") if isinstance(active_journey, dict) else None)
        selected_route_id = getattr(active_journey, "selected_route_id", None) or (active_journey.get("selected_route_id") if isinstance(active_journey, dict) else None)
        
        if plan:
            selected_route = getattr(plan, "selected_route", None) or (plan.get("selected_route") if isinstance(plan, dict) else None)
            if selected_route:
                score_raw = getattr(selected_route, "safety_score", None) if hasattr(selected_route, "safety_score") else (selected_route.get("safety_score") if isinstance(selected_route, dict) else None)
                if score_raw is not None:
                    try:
                        safety_score = float(score_raw)
                    except (ValueError, TypeError):
                        safety_score = None

        if safety_score is None:
            planned_routes = getattr(active_journey, "planned_routes", None) or (active_journey.get("planned_routes") if isinstance(active_journey, dict) else None) or []
            for r in planned_routes:
                rid = getattr(r, "id", None) or getattr(r, "route_identifier", None) or (r.get("id") or r.get("route_identifier") if isinstance(r, dict) else None)
                if selected_route_id and rid == selected_route_id:
                    score_raw = getattr(r, "safety_score", None) or (r.get("safety_score") if isinstance(r, dict) else None)
                    if score_raw is not None:
                        try:
                            safety_score = float(score_raw)
                        except (ValueError, TypeError):
                            safety_score = None
                    break
            if safety_score is None and planned_routes:
                first = planned_routes[0]
                score_raw = getattr(first, "safety_score", None) or (first.get("safety_score") if isinstance(first, dict) else None)
                if score_raw is not None:
                    try:
                        safety_score = float(score_raw)
                    except (ValueError, TypeError):
                        safety_score = None

        weather_str = None
        if plan:
            weather_state = getattr(plan, "weather_state", None) or (plan.get("weather_state") if isinstance(plan, dict) else None)
            if weather_state:
                cond = getattr(weather_state, "condition", None) or (weather_state.get("condition") if isinstance(weather_state, dict) else None)
                if cond and cond != "UNKNOWN":
                    weather_str = cond

        eta_str = None
        progress = getattr(active_journey, "progress", None) or (active_journey.get("progress") if isinstance(active_journey, dict) else None)
        if progress:
            eta_rem = getattr(progress, "eta_remaining", None) or (progress.get("eta_remaining") if isinstance(progress, dict) else None)
            if eta_rem is not None and eta_rem > 0:
                eta_str = f"{int(round(eta_rem))} mins"
        if not eta_str and plan:
            selected_route = getattr(plan, "selected_route", None) or (plan.get("selected_route") if isinstance(plan, dict) else None)
            if selected_route:
                dur = getattr(selected_route, "duration", None) or (selected_route.get("duration") if isinstance(selected_route, dict) else None)
                if dur is not None and dur > 0:
                    eta_str = f"{max(1, int(round(dur / 60)))} mins"

        alerts = getattr(active_journey, "alerts", None) or (active_journey.get("alerts") if isinstance(active_journey, dict) else None) or []

        recent = []
        if journey_history and isinstance(journey_history, list):
            for j in journey_history:
                dest = getattr(j, "destination", None) or (j.get("destination") if isinstance(j, dict) else None)
                if dest:
                    recent.append(str(dest))

        return {
            "active_journey": True,
            "source": source_str,
            "destination": dest_str,
            "safety_score": safety_score,
            "eta": eta_str,
            "weather": weather_str,
            "community_alerts": len(alerts),
            "emergency_status": "Monitoring",
            "recent_journeys": recent,
            "pinned_info": []
        }

    def build_assistant_context(self, final_context: Dict[str, Any], user_id: str, active_journey: Any = None, journey_history: Any = None) -> Any:
        from app.schemas.assistant_schemas import (
            AssistantResponse, AgentStatus, ReasoningContext, 
            JourneyContextState, ProviderHealthStatus, MemoryState
        )
        import datetime
        import uuid
        
        if active_journey is None:
            active_journey = final_context.get("active_journey")
        if journey_history is None:
            journey_history = final_context.get("journey_history")

        j_state = self._extract_journey_state(active_journey, journey_history)

        reasoning_steps = [
            "System operating in verified boundaries",
            "Active journey context checked" if j_state["active_journey"] else "No active journey in progress"
        ]

        if j_state["active_journey"]:
            if j_state["safety_score"] is not None:
                content_text = f"Hello! Monitoring your active journey to {j_state['destination']}. Route safety score is {j_state['safety_score']:.1f}% (environmental proxy)."
            else:
                content_text = f"Hello! Monitoring your active journey to {j_state['destination']}. Route safety score is unavailable."
            suggestions = ["Explain my safety score", "Check route progress", "Show nearby Safe Zones"]
        else:
            content_text = "Hello! I am your NavSakhi Journey Intelligence Coordinator. How can I assist you today?"
            suggestions = ["Plan a new route", "Check emergency contacts", "Explain route safety scoring"]

        return AssistantResponse(
            message_id="msg_" + str(uuid.uuid4())[:8],
            role="assistant",
            content=content_text,
            timestamp=datetime.datetime.utcnow().isoformat(),
            agent_status=AgentStatus(status="Monitoring" if j_state["active_journey"] else "Idle", current_task="Awaiting next input"),
            reasoning=ReasoningContext(
                summary=reasoning_steps,
                confidence=None,
                decision_source="Journey Engine State",
                provider_summary="Operating within local verified boundaries"
            ),
            context=JourneyContextState(
                active_journey=j_state["active_journey"],
                source=j_state["source"],
                destination=j_state["destination"],
                safety_score=j_state["safety_score"],
                eta=j_state["eta"],
                weather=j_state["weather"],
                community_alerts=j_state["community_alerts"],
                emergency_status=j_state["emergency_status"]
            ),
            provider_health=[
                ProviderHealthStatus(name="Routing API (OSRM)", status="Connected")
            ],
            memory=MemoryState(
                recent_journeys=j_state["recent_journeys"],
                pinned_info=j_state["pinned_info"]
            ),
            quick_suggestions=suggestions
        )

    def build_assistant_chat(self, final_context: Dict[str, Any], user_id: str, query: str, active_journey: Any = None, journey_history: Any = None) -> Any:
        from app.schemas.assistant_schemas import (
            AssistantResponse, AgentStatus, ReasoningContext, 
            JourneyContextState, ProviderHealthStatus, MemoryState
        )
        import datetime
        import uuid
        
        if active_journey is None:
            active_journey = final_context.get("active_journey")
        if journey_history is None:
            journey_history = final_context.get("journey_history")

        j_state = self._extract_journey_state(active_journey, journey_history)
        has_active = j_state["active_journey"]
        safety_score = j_state["safety_score"]
        dest_desc = j_state["destination"]
        weather_str = j_state["weather"]
        eta_str = j_state["eta"]

        query_lower = query.lower()
        llm = final_context.get("LLM", {})
        raw_summary = llm.get("summary") if isinstance(llm, dict) else None

        # Prioritize genuine LLM response / rich intent-sensitive fallback from ReasoningTool
        if raw_summary and not any(kw in raw_summary.lower() for kw in ["98%", "optimal lighting", "low crowd density", "zero community incident"]):
            response_text = raw_summary
        elif any(w in query_lower for w in ["my safety score", "my score", "current score", "active score"]):
            if not has_active:
                response_text = (
                    "No active journey is currently being monitored. "
                    "You can plan and start a route in the Journey Planner to view model-evaluated road-segment safety scores."
                )
            elif safety_score is None:
                response_text = (
                    "The safety score for your active route is currently unavailable. "
                    "This occurs when road-segment coverage is below the required threshold (70%) or when using transit modes without road segment models. "
                    "NavSakhi does not invent default or estimated scores when coverage is missing."
                )
            else:
                response_text = (
                    f"Your active route has a calculated safety score of {safety_score:.1f}%. "
                    "NavSakhi scores reflect synthetic environmental proxy indicators (infrastructure, emergency service proximity, "
                    "and urban form) along matched road segments. They do not represent empirical crime occurrence, guarantee personal safety, "
                    "or predict victimization."
                )
        elif any(w in query_lower for w in ["weather", "rain", "temperature", "climate"]):
            if weather_str:
                response_text = f"The recorded weather along your route is {weather_str}."
            else:
                response_text = "Live weather telemetry is not currently attached to your journey."
        elif any(w in query_lower for w in ["police", "hospital", "station", "safe zone", "help", "emergency"]):
            response_text = (
                "Verified emergency resources and designated safe zones are accessible in the Emergency panel. "
                "In an immediate threat, activate SOS or call 112 (National Helpline) / 1091 (Women Helpline)."
            )
        elif any(w in query_lower for w in ["route", "destination", "eta", "progress"]):
            if has_active:
                response_text = f"Your journey to {dest_desc or 'your destination'} is active. ETA: {eta_str or 'calculating'}."
            else:
                response_text = "There is no active journey in progress. You can search and select routes in the Journey Planner."
        else:
            response_text = (
                "Hello! I am your NavSakhi Intelligence Coordinator. "
                "You can ask me about safe route planning across Chennai, transport modes (Metro, Bus, Suburban rail), "
                "emergency support, or how our safety scores are evaluated."
            )

        suggestions = (
            ["Explain my safety score", "Check route progress", "Show nearby Safe Zones"]
            if has_active
            else ["Plan a new route", "Check emergency contacts", "Explain route safety scoring"]
        )

        provider_val = llm.get("provider") if isinstance(llm, dict) else None
        ai_status_val = llm.get("ai_status") if isinstance(llm, dict) else None

        if provider_val == "gemini" and ai_status_val == "LIVE_SUCCESS":
            prov_summary = "Generated by Gemini AI companion"
            gemini_health = ProviderHealthStatus(name="Gemini AI", status="Connected")
        elif ai_status_val == "RATE_LIMITED_FALLBACK":
            prov_summary = "Operating in local verified boundaries (Gemini rate-limited 429)"
            gemini_health = ProviderHealthStatus(name="Gemini AI", status="Rate Limited (429)")
        elif provider_val == "local_companion":
            prov_summary = "Processed by NavSakhi Travel Companion intent layer"
            gemini_health = ProviderHealthStatus(name="Travel Companion Engine", status="Connected")
        elif ai_status_val == "CONFIG_MISSING_FALLBACK":
            prov_summary = "Operating in local verified boundaries (Gemini unconfigured)"
            gemini_health = ProviderHealthStatus(name="Gemini AI", status="Unconfigured")
        else:
            prov_summary = "Operating within local verified boundaries"
            gemini_health = ProviderHealthStatus(name="Gemini AI", status="Offline / Fallback")

        health_list = [
            ProviderHealthStatus(name="Routing API (OSRM)", status="Connected"),
            gemini_health
        ]

        return AssistantResponse(
            message_id="msg_" + str(uuid.uuid4())[:8],
            role="assistant",
            content=response_text,
            timestamp=datetime.datetime.utcnow().isoformat(),
            agent_status=AgentStatus(status="Monitoring" if has_active else "Idle", current_task="Awaiting next input"),
            reasoning=ReasoningContext(
                summary=["Query processed against verified route context", "Bounded to empirical telemetry data"],
                confidence=None,
                decision_source="Journey Engine State",
                provider_summary=prov_summary
            ),
            context=JourneyContextState(
                active_journey=has_active,
                source=j_state["source"],
                destination=j_state["destination"],
                safety_score=safety_score,
                eta=eta_str,
                weather=weather_str,
                community_alerts=j_state["community_alerts"],
                emergency_status=j_state["emergency_status"]
            ),
            provider_health=health_list,
            memory=MemoryState(
                recent_journeys=j_state["recent_journeys"],
                pinned_info=j_state["pinned_info"]
            ),
            quick_suggestions=suggestions
        )
        
    def build_profile_response(self, final_context: Dict[str, Any], user_id: str) -> Any:
        from app.schemas.profile_schemas import (
            ProfileResponse, UserInfo, ProfileStats, 
            ProfileJourneyHistory, ProfileEmergencyContact, ProfileAchievement
        )
        
        # Extract from ProfileAgent
        profile_data = final_context.get("ProfileAgent", {}).get("profile", {})
        
        user_info = UserInfo(
            full_name=profile_data.get("name", "Sarah Connor"),
            email=profile_data.get("email", "sarah.connor@example.com"),
            phone=profile_data.get("phone", "+1 (555) 019-8234"),
            avatar_url=profile_data.get("avatar_url", ""),
            current_city="Bengaluru",
            member_since=profile_data.get("join_date", "January 2024"),
            is_premium=True,
            is_online=True,
            last_active="Just now"
        )
        
        stats = ProfileStats(
            safe_journeys=42,
            total_distance_km=156.4,
            avg_safety_score=97.5,
            sos_triggered=0,
            dangerous_routes_avoided=14,
            ai_recommendations_followed=89,
            community_reports_submitted=12,
            verified_reports=10,
            helpful_votes=45,
            reputation_score=950,
            trust_level="Level 3 Verified"
        )
        
        journey_history = [
            ProfileJourneyHistory(
                id="j_123", source="Home", destination="Office", 
                date="2024-03-15", transport="Walking", safety_score=98, 
                duration="15m", status="Completed"
            )
        ]
        
        emergency_contacts = [
            ProfileEmergencyContact(
                id="c1", name="John Connor", relationship="Brother", 
                phone="+1 (555) 019-8235", status="Active", is_primary=True
            )
        ]
        
        achievements = [
            ProfileAchievement(
                id="a1", title="Safety First", icon="Shield", 
                unlocked=True, date="2024-02-10"
            )
        ]
        
        return ProfileResponse(
            user_info=user_info,
            stats=stats,
            journey_history=journey_history,
            emergency_contacts=emergency_contacts,
            achievements=achievements
        )

    def build_settings_response(self, final_context: Dict[str, Any], user_id: str) -> Any:
        from app.schemas.settings_schemas import (
            SettingsResponse, SettingsAppearance, SettingsNotifications, 
            SettingsPrivacy, SettingsEmergency, SettingsAiPreferences,
            SettingsLocation, SettingsLanguage, SettingsVoice, SettingsDeveloper
        )
        
        return SettingsResponse(
            appearance=SettingsAppearance(theme="System", accent_color="blue"),
            notifications=SettingsNotifications(
                journey_alerts=True, community_alerts=True, weather_alerts=True,
                emergency_alerts=True, ai_notifications=True, email_notifications=False,
                push_notifications=True
            ),
            privacy=SettingsPrivacy(
                share_live_location=False, anonymous_community_reports=True,
                location_history=True, analytics=True, crash_reports=True
            ),
            emergency=SettingsEmergency(
                default_sos_contacts=True, auto_location_sharing=True,
                emergency_countdown=True, auto_call_emergency_contact=False,
                share_journey_automatically=False
            ),
            ai_preferences=SettingsAiPreferences(
                assistant_personality="Professional", explanation_detail="Brief",
                safety_sensitivity="High", preferred_route_type="Safest",
                risk_tolerance="Low", agent_notifications=True,
                enable_ai_recommendations=True
            ),
            location=SettingsLocation(
                default_transport_mode="Walking", preferred_walking_speed="Average",
                avoid_highways=True, avoid_dark_areas=True, avoid_crowds=False,
                avoid_construction=True
            ),
            language=SettingsLanguage(
                language="English", region="US", time_format="12h", distance_unit="Metric"
            ),
            voice=SettingsVoice(
                voice_enabled=True, preferred_voice="Female 1", speech_speed=1.0
            ),
            developer=SettingsDeveloper(
                developer_mode=False, show_debug_info=False, provider_status=False,
                api_version="v1.0", app_version="1.0.0", build_version="2026.8.2"
            )
        )
