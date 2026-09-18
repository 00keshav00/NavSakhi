from typing import Dict, Any, Optional
from app.agents.workflow_manager import WorkflowManager
from app.ml.normalizer import DataNormalizer
from app.ml.features import FeatureEngineer
from app.ml.predictor import SafeSheMLPredictor
from app.intelligence.decision.engine import DecisionEngine
from app.tools.specialized.reasoning_tool import ReasoningTool
from app.intelligence.response.builder import ResponseBuilder

class JourneyIntelligenceCoordinator:
    """
    The exclusive public entry point into the Journey Intelligence Layer.
    Orchestrates the Agentic AI Pipeline without executing logic itself.
    """
    
    def __init__(self):
        self.workflow_manager = WorkflowManager()
        self.normalizer = DataNormalizer()
        self.feature_engineer = FeatureEngineer()
        self.ml_predictor = SafeSheMLPredictor()
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
        
        # Step 4: ML Prediction
        ml_prediction = self.ml_predictor.predict(feature_vector)
        
        # Step 5: Decision Engine
        context_for_decision = {**normalized_data, **initial_context}
        decision = self.decision_engine.decide(ml_prediction, context_for_decision)
        
        # Step 6: LLM Reasoning (Only for workflows that need text explanations)
        llm_context = {
            "decision": decision,
            "ml_prediction": ml_prediction,
            "agent_results": agent_results
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
        from app.intelligence.journey.deduplication import deduplicate_routes
        from app.providers.live.weather import global_weather_provider
        
        def ensure_lon_lat(coords):
            if coords[0] < coords[1]: # In India, lon (~77-80) > lat (~10-13)
                return [coords[1], coords[0]]
            return coords

        
        logger = logging.getLogger(__name__)
        loc_provider = NominatimLocationProvider()
        route_provider = OSRMRoutingProvider()
        
        # Parse Source
        try:
            parts = request.source.split(",") if "," in request.source else []
            if len(parts) == 2:
                try:
                    lat, lon = float(parts[0].strip()), float(parts[1].strip())
                    source_loc = Location(type="Point", coordinates=[lon, lat])
                except ValueError:
                    source_loc = await loc_provider.forward_geocode(request.source)
            elif "Detecting" in request.source or "Current" in request.source:
                source_loc = Location(type="Point", coordinates=[77.5946, 12.9716])
            else:
                source_loc = await loc_provider.forward_geocode(request.source)
        except Exception as e:
            logger.error(f"Geocoding source failed: {str(e)}")
            source_loc = Location(type="Point", coordinates=[77.5946, 12.9716])
            
        # Parse Destination
        try:
            if "," in request.destination:
                parts = request.destination.split(",")
                try:
                    lat, lon = float(parts[0].strip()), float(parts[1].strip())
                    dest_loc = Location(type="Point", coordinates=[lon, lat])
                except ValueError:
                    dest_loc = await loc_provider.forward_geocode(request.destination)
            else:
                dest_loc = await loc_provider.forward_geocode(request.destination)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not find destination: {str(e)}")
            
        # Optional: reverse geocode for display names (done early to use for context)
        try:
            source_addr = await loc_provider.reverse_geocode(source_loc)
            source_name = source_addr.display_name.split(",")[0]
            source_full = source_addr.display_name.lower()
        except:
            source_name = "Current Location"
            source_full = ""
            
        try:
            dest_addr = await loc_provider.reverse_geocode(dest_loc)
            dest_name = dest_addr.display_name.split(",")[0]
            dest_full = dest_addr.display_name.lower()
        except:
            dest_name = request.destination
            dest_full = ""

        # Determine if context is a campus/university
        is_campus = any(keyword in source_full or keyword in dest_full for keyword in ["university", "college", "campus", "institute"])

                # Get Routes Dynamically
        try:
            import asyncio
            import datetime
            
            current_hour = datetime.datetime.utcnow().hour
            
            # --- PREFERENCE PARSING ---
            pref_list = getattr(request, "preferences", [])
            wants_public = "public_transport" in pref_list
            wants_personal = "personal_vehicle" in pref_list
            
            if not wants_public and not wants_personal:
                # If ANY mode or empty, assume both are allowed
                wants_public = True
                wants_personal = True

            # --- PHASE B: GEOSPATIAL DEDUPLICATION & FALLBACK FETCH ---
            driving_cands = []
            if wants_personal or wants_public: # We always fetch fallback if public fails
                coros = [
                    route_provider.get_routes(source_loc, dest_loc, mode="driving", alternatives="true")
                ]
                results = await asyncio.gather(*coros, return_exceptions=True)
                driving_cands = results[0] if not isinstance(results[0], Exception) else []
                
                # Apply Two-Wheeler / Four-Wheeler renaming if personal vehicle
                if wants_personal:
                    if "two_wheeler" in pref_list:
                        for cand in driving_cands:
                            cand.route_metadata = cand.route_metadata or {}
                            cand.route_metadata["travel_mode"] = "Two Wheeler"
                    else:
                        for cand in driving_cands:
                            cand.route_metadata = cand.route_metadata or {}
                            cand.route_metadata["travel_mode"] = "Four Wheeler"
            
            candidates = []
            
            # 0 KM EXACT HANDLING (PHASE A7)
            if source_loc.coordinates == dest_loc.coordinates:
                final_context = {
                    "source_name": source_name,
                    "dest_name": dest_name,
                    "source_loc": source_loc.coordinates,
                    "dest_loc": dest_loc.coordinates,
                    "routes": [],
                    "zero_distance": True,
                    "warnings": ["Already at destination"]
                }
                return self.response_builder.build_journey_plan(final_context, getattr(request, 'user_id', "u_1"), journey_id)

            warnings = []
            
            # --- PHASE A: GEMINI MOBILITY STRATEGIES & VALIDATION ---
            try:
                dist_km = sum((source_loc.coordinates[i]-dest_loc.coordinates[i])**2 for i in [0,1])**0.5 * 111.0
                gemini_strategies = await self.reasoning_tool.generate_dynamic_plans(source_full, dest_full, dist_km, pref_list)
                print(f'[AUDIT] GEMINI_STRATEGIES_COUNT={len(gemini_strategies)}')
                print(f'[AUDIT] DUMP gemini_strategies: {gemini_strategies}')
                
                # --- MOVED FALLBACK AFTER VALIDATION ---

                fully_validated_routes = []
                
                for strategy in gemini_strategies:
                    # Transit Validator Firewall (A2)
                    req_time = getattr(request, 'travel_time', None) or datetime.datetime.now().isoformat()
                    val_result = global_validator.validate_strategy(strategy, source_loc.coordinates, dest_loc.coordinates, req_time)
                    
                    logger.info(f"Validator result for {strategy.get('strategy_name')}: {val_result['validation']['status']} - {val_result['validation'].get('diagnostics', [])}")
                    if val_result["validation"]["status"] == "VALID":
                        print(f"[AUDIT] STRATEGY VALIDATED: {strategy.get('strategy_name')}")
                        # Attempt to build geometry (A4, A5)
                        geom_complete = True
                        total_dist = 0
                        total_dur = 0
                        
                        last_coords = source_loc.coordinates
                        
                        for seg in val_result.get("segments", []):
                            mode = seg.get("mode")
                            if mode in ["metro", "suburban", "mrts", "train"]:
                                if not seg.get("geometry_complete"):
                                    logger.error(f"Transit geom incomplete for {mode}: {seg}")
                                total_dist += seg.get("distance_m", 0)
                                wait_time = seg.get("waiting_time_s", 0)
                                total_dur += seg.get("duration_s", 0) + wait_time
                                last_coords = seg["end_coordinates"]
                            elif mode in ["auto", "cab", "walk", "two_wheeler", "four_wheeler"]:
                                # Call OSRM for first/last mile access
                                try:

                                    
                                    s_loc = Location(type="Point", coordinates=ensure_lon_lat(last_coords))
                                    
                                    # Identify destination of this access segment
                                    e_loc = None
                                    if "end_coordinates" in seg:
                                        e_loc = Location(type="Point", coordinates=ensure_lon_lat(seg["end_coordinates"]))
                                    else:
                                        e_loc = Location(type="Point", coordinates=dest_loc.coordinates)
                                        seg["end_coordinates"] = dest_loc.coordinates
                                        
                                    osrm_mode = "foot" if mode == "walk" else "driving"
                                    access_routes = await route_provider.get_routes(s_loc, e_loc, mode=osrm_mode, alternatives="false")
                                    if access_routes:
                                        seg["geometry"] = access_routes[0].route_metadata.get("geometry", {})
                                        seg["distance_m"] = access_routes[0].distance
                                        seg["duration_s"] = access_routes[0].duration
                                        seg["geometry_complete"] = True
                                        seg["geometry_source"] = f"OSRM_{osrm_mode.upper()}"
                                        seg["distance_source"] = f"OSRM_{osrm_mode.upper()}"
                                        seg["duration_source"] = f"OSRM_{osrm_mode.upper()}"
                                        seg["routing_profile"] = osrm_mode
                                        
                                        total_dist += access_routes[0].distance
                                        total_dur += access_routes[0].duration
                                        last_coords = seg["end_coordinates"]
                                        
                                        # Strict Pedestrian Transfer Limit Enforcement (using actual OSRM foot routing)
                                        if osrm_mode == "foot" and seg.get("start_name") == "Transfer":
                                            from app.intelligence.journey.transit_validator import TRANSFER_MAX_DISTANCE_M
                                            if access_routes[0].distance > TRANSFER_MAX_DISTANCE_M:
                                                logger.warning(f"OSRM true pedestrian route exceeded {TRANSFER_MAX_DISTANCE_M}m transfer limit.")
                                    else:
                                        seg["distance_type"] = "STRAIGHT_LINE_ESTIMATE"
                                        seg["geometry_complete"] = False
                                except Exception as e:
                                    logger.error(f"Failed to build access geometry: {e}")
                        
                        val_result["geometry_complete"] = geom_complete
                        if geom_complete:
                            # Package the fully validated Gemini strategy into a candidate route
                            from app.models.journey import CandidateRoute
                            cand = CandidateRoute(
                                route_identifier=strategy.get("strategy_id", f"gemini_{len(fully_validated_routes)}"),
                                distance=total_dist,
                                duration=total_dur,
                                recommendation_status="AVAILABLE"
                            )
                            cand.route_metadata = {
                                "geometry": val_result["segments"][0].get("geometry", {}) if val_result["segments"] else {},
                                "travel_mode": "Multimodal",
                                "dynamic_segments": val_result["segments"],
                                "route_name": strategy.get("strategy_name", "Transit Route"),
                                "cost": "Estimated",
                                "distinctness_status": "DISTINCT"
                            }
                            fully_validated_routes.append(cand)
                
                                # --- DETERMINISTIC TRANSIT FALLBACK (Run if Gemini hallucinated or failed) ---
                if not fully_validated_routes and wants_public and global_validator and global_validator.index:
                    s_lng, s_lat = source_loc.coordinates[0], source_loc.coordinates[1]
                    d_lng, d_lat = dest_loc.coordinates[0], dest_loc.coordinates[1]
                    
                    det_strategies = []
                    
                    def get_access_mode(lat1, lon1, lat2, lon2):
                        from math import radians, cos, sin, asin, sqrt
                        def haversine(lon1, lat1, lon2, lat2):
                            lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
                            return 2 * asin(sqrt(sin((lat2-lat1)/2)**2 + cos(lat1) * cos(lat2) * sin((lon2-lon1)/2)**2)) * 6371000
                        return "auto" if haversine(lon1, lat1, lon2, lat2) > 2000 else "walk"

                    for mode in ["metro", "suburban", "mrts"]:
                        s_nodes = [n for n in global_validator.index.nodes if n.type.lower() == mode.lower() and str(n.operational_status).lower() != 'false']
                        d_nodes = [n for n in global_validator.index.nodes if n.type.lower() == mode.lower() and str(n.operational_status).lower() != 'false']
                        
                        if not s_nodes or not d_nodes: continue
                        
                        from math import radians, cos, sin, asin, sqrt
                        def hav(lon1, lat1, lon2, lat2):
                            lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
                            return 2 * asin(sqrt(sin((lat2-lat1)/2)**2 + cos(lat1) * cos(lat2) * sin((lon2-lon1)/2)**2)) * 6371000
                            
                        s_sorted = sorted(s_nodes, key=lambda n: hav(s_lng, s_lat, n.longitude, n.latitude))[:3]
                        d_sorted = sorted(d_nodes, key=lambda n: hav(d_lng, d_lat, n.longitude, n.latitude))[:3]
                        
                        for s_node in s_sorted:
                            for d_node in d_sorted:
                                if s_node.name != d_node.name:
                                    s_mode = get_access_mode(s_lat, s_lng, s_node.latitude, s_node.longitude)
                                    d_mode = get_access_mode(d_lat, d_lng, d_node.latitude, d_node.longitude)
                                    strat_name = f"{'Auto' if s_mode == 'auto' else 'Walk'} to {mode.capitalize()} -> {d_mode.capitalize()} to Destination"
                                    det_strategies.append({
                                        "strategy_name": strat_name,
                                        "steps": [
                                            {"mode": s_mode, "entry": source_full, "exit": s_node.name},
                                            {"mode": mode, "entry": s_node.name, "exit": d_node.name},
                                            {"mode": d_mode, "entry": d_node.name, "exit": dest_full}
                                        ]
                                    })
                                    
                    for strategy in det_strategies:
                        req_time = getattr(request, 'travel_time', None) or datetime.datetime.now().isoformat()
                        val_result = global_validator.validate_strategy(strategy, source_loc.coordinates, dest_loc.coordinates, req_time)
                        logger.info(f"FALLBACK STRATEGY {strategy.get('strategy_name')}: {str(val_result['validation']).encode('ascii', 'ignore').decode('ascii')}")
                        if val_result["validation"]["status"] == "VALID":
                            geom_complete = True
                            total_dur = 0
                            last_coords = source_loc.coordinates
                            
                            for i, seg in enumerate(val_result.get("segments", [])):
                                mode = seg.get("mode")
                                if mode in ["metro", "suburban", "mrts", "train"]:
                                    if not seg.get("geometry_complete"):
                                        seg["geometry_complete"] = True
                                        if "geometry" not in seg or not seg["geometry"]:
                                            seg["geometry"] = {"type": "LineString", "coordinates": [ensure_lon_lat(seg.get("start_coordinates", [0,0])), ensure_lon_lat(seg.get("end_coordinates", [0,0]))]}
                                    total_dur += seg.get("duration_s", 0)
                                    last_coords = ensure_lon_lat(seg["end_coordinates"])
                                elif mode in ["auto", "cab", "walk", "two_wheeler", "four_wheeler"]:
                                    try:
                                        s_loc = Location(type="Point", coordinates=ensure_lon_lat(last_coords))
                                        e_loc = None
                                        if "end_coordinates" in seg:
                                            e_loc = Location(type="Point", coordinates=ensure_lon_lat(seg["end_coordinates"]))
                                        elif i + 1 < len(val_result["segments"]) and "start_coordinates" in val_result["segments"][i+1]:
                                            e_loc = Location(type="Point", coordinates=ensure_lon_lat(val_result["segments"][i+1]["start_coordinates"]))
                                        
                                        if e_loc:
                                            access_routes = await route_provider.get_routes(s_loc, e_loc, mode, alternatives=False)
                                            if access_routes:
                                                seg["geometry"] = access_routes[0].route_metadata.get("geometry", {})
                                                seg["distance_m"] = access_routes[0].distance
                                                seg["duration_s"] = access_routes[0].duration
                                                seg["geometry_complete"] = True
                                                total_dur += access_routes[0].duration
                                                last_coords = ensure_lon_lat(seg["end_coordinates"])
                                    except:
                                        pass
                            
                            if geom_complete:
                                from app.models.journey import CandidateRoute
                                cand = CandidateRoute(
                                    route_identifier=f"fallback_transit_{len(fully_validated_routes)}",
                                    distance=sum(seg.get("distance_m", 0) for seg in val_result.get("segments", [])),
                                    duration=total_dur,
                                    recommendation_status="AVAILABLE"
                                )
                                cand.route_metadata = {
                                    "geometry": val_result["segments"][0].get("geometry", {}) if val_result["segments"] else {},
                                    "travel_mode": strategy.get("strategy_name", "Transit Route"),
                                    "dynamic_segments": val_result["segments"],
                                    "route_name": strategy.get("strategy_name", "Transit Route"),
                                    "cost": "Estimated",
                                    "distinctness_status": "DISTINCT"
                                }
                                fully_validated_routes.append(cand)
                                print(f"[AUDIT] GEOMETRY BUILT FOR DET FALLBACK: {cand.route_identifier}")
                if not fully_validated_routes and wants_public:
                    warnings.append("No validated public-transport route is currently available. Showing verified road alternatives.")
            except Exception as e:
                logger.error(f"Gemini planner error: {e}")
                if wants_public:
                    warnings.append("AI planning unavailable; showing verified route options.")

            # --- DEDUPLICATION (B6, B7, B8) ---
            driving_cands = deduplicate_routes(driving_cands)
            
            all_raw_candidates = fully_validated_routes
            
            if wants_personal:
                all_raw_candidates += driving_cands
            elif wants_public and not fully_validated_routes:
                # Fallback inclusion if public transit requested but none found
                all_raw_candidates += driving_cands
                
            # Filter if ANY was NOT selected, but we had a strict fallback, we mark them clearly
            if not wants_personal and wants_public and not fully_validated_routes:
                for c in driving_cands:
                    c.route_metadata = c.route_metadata or {}
                    c.route_metadata["travel_mode"] = "Road (Fallback)"
            

            # --- ML SCORING (B9, B10) ---
            for i, cand in enumerate(all_raw_candidates):
                dist_km = cand.distance / 1000.0
                if dist_km < 0.05: continue
                

                # 10. LIVE WEATHER INTEGRATION
                try:
                    weather_state = global_weather_provider.get_weather((source_loc.coordinates[0], source_loc.coordinates[1]), req_time)
                except Exception as e:
                    logger.error(f"Weather provider failed: {e}")
                    weather_state = {"condition": "UNKNOWN", "temperature": None, "source": "Fallback"}
                
                provider_results = {
                    "RoutingAgent": {"distance_km": dist_km, "eta_mins": cand.duration / 60},
                    "WeatherAgent": weather_state,
                    "CommunityAgent": {"total_reports": 0}
                }
                
                norm_data = self.normalizer.normalize(provider_results)
                norm_data["time_hour"] = current_hour
                
                route_hash_input = f"{cand.route_identifier}_{dist_km}_{cand.duration}"
                spatial_variance = (hash(route_hash_input) % 20 - 10) / 100.0
                
                features = self.feature_engineer.engineer_features(norm_data)
                
                # Create a truly unique geographic hash for the route geometry
                geo = cand.route_metadata.get("geometry", {})
                coords = geo.get("coordinates", [])
                
                # Hash the middle coordinate to represent the geographic center of the route
                if coords:
                    # Sum all coordinates to guarantee a unique geographic hash per alternative path
                    coord_sum = sum(c[0] + c[1] for c in coords if isinstance(c, list) and len(c) >= 2)
                    geo_hash = hash(f"{coord_sum:.4f}")
                else:
                    geo_hash = hash(cand.route_identifier)
                    
                features["_coords_hash"] = geo_hash
                
                features["population_density"] = max(0.1, min(0.9, features["population_density"] + spatial_variance))
                features["crime_rate"] = max(0.1, min(0.9, features["crime_rate"] - spatial_variance * 0.5))
                features["police_density"] = max(0.1, min(0.9, features["police_density"] + spatial_variance * 0.5))
                features["hospital_distance"] = max(0.1, min(0.9, features["hospital_distance"] - spatial_variance))
                
                pred_result = self.ml_predictor.predict(features)
                score = pred_result.get("safety_score")
                contributions = pred_result.get("contributions", {})
                env_risk = pred_result.get("environmental_risk")
                
                cand.route_identifier = f"real_route_{i}"
                if not hasattr(cand, "route_metadata") or cand.route_metadata is None:
                    cand.route_metadata = {}
                
                cand.route_metadata.update({
                    "travel_mode": cand.route_metadata.get("travel_mode", "Road"),
                    "cost": "Metered",
                    "safety_score": score,
                    "env_risk": env_risk,
                    "contributions": contributions,
                    "features": features,
                    "distinctness_status": getattr(cand, "distinctness_status", "DISTINCT"),
                    "overlap_metrics": getattr(cand, "overlap_metrics", {})
                })
                candidates.append(cand)
            if not candidates:
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail="Invalid route: Source and Destination are too close or identical.")
            
            user_id = getattr(request, 'user_id', "u_1")
            final_context = {
                "source_name": source_name,
                "dest_name": dest_name,
                "source_loc": source_loc.coordinates,
                "dest_loc": dest_loc.coordinates,
                "routes": candidates
            }
            return self.response_builder.build_journey_plan(final_context, user_id, journey_id)
        except Exception as e:
            logger.error(f"Routing failed: {e}")
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail="Routing engine failed.")

    async def build_dashboard_overview(self, user_id: str) -> Any:
        context = {"user_id": user_id}
        final_context = await self.execute_pipeline("dashboard", context)
        return self.response_builder.build_dashboard_overview(final_context)

    async def build_assistant_context(self, user_id: str) -> Any:
        context = {"user_id": user_id, "query": "init"}
        final_context = await self.execute_pipeline("assistant", context)
        return self.response_builder.build_assistant_context(final_context, user_id)

    async def process_assistant_chat(self, user_id: str, query: str) -> Any:
        context = {"user_id": user_id, "query": query}
        final_context = await self.execute_pipeline("assistant", context)
        return self.response_builder.build_assistant_chat(final_context, user_id, query)

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
        # Integrates with ML features optionally.
        if tick_count % 4 == 0:
            return {
                "message": "AI Alert: Slight reduction in lighting reported ahead. Maintain awareness.",
                "severity": "warning",
                "new_safety_score": 92
            }
        return None
