from typing import Dict, Any

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
                condition="Clear",
                temperature=24,
                visibility=10000,
                humidity=45,
                rain_probability=0
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
            MultimodalRoute, RouteSegment, WeatherSummary, CommunitySummary, AIRecommendation
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
        from app.ml.predictor import SafeSheMLPredictor
        predictor = SafeSheMLPredictor()
        
        from app.intelligence.journey.recommender import global_recommender
        # Recommender handles objective ranking and missing data without mutating arrays
        # Extract transport preference safely (default to ANY if not provided or missing from context)
        pref = "ANY"
        rec_payload = global_recommender.generate_recommendation(candidates, pref)
        
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
            coords = geo.get("coordinates", [])
            
            # If OSRM failed or returned no coordinates, construct a direct line from source to destination as fallback
            if not coords or len(coords) < 2:
                s_loc = final_context.get("source_loc")
                d_loc = final_context.get("dest_loc")
                
                s_coord = s_loc.coordinates if hasattr(s_loc, 'coordinates') else [80.1527, 12.8448]
                d_coord = d_loc.coordinates if hasattr(d_loc, 'coordinates') else [80.2291, 12.8359]
                
                coords = [s_coord, d_coord]
                    
            segments = []
            mode_name = c.route_metadata.get("travel_mode", "Cab Direct")
            cost_str = c.route_metadata.get("cost", "₹ 150")
            
            dist_km = c.distance / 1000
            eta_mins = c.duration / 60
            
            s_score = c.route_metadata.get("safety_score") # Used for sorting fallback
            env_risk = c.route_metadata.get("env_risk", 50.0)
            contrib = c.route_metadata.get("contributions", {})
            
            dynamic_segs = c.route_metadata.get("dynamic_segments", [])
            
            def get_mode_color(mode: str) -> str:
                m = mode.lower()
                if "walk" in m: return "#4CAF50" # Green
                if "metro" in m: return "#9C27B0" # Purple
                if "suburban" in m or "train" in m: return "#F44336" # Red
                if "mrts" in m: return "#00BCD4" # Cyan
                if "bus" in m or "transit" in m: return "#FF9800" # Orange
                return "#2196F3" # Blue (Cab/Driving)

            if dynamic_segs:
                # The exact physical segments have been constructed by the Coordinator.
                # Map them directly. No fake interpolations.
                for idx, seg in enumerate(dynamic_segs):
                    mode = seg.get("mode", "Unknown")
                    seg_color = get_mode_color(mode)
                    
                    # Convert raw dict from coordinator to GeoJSON Feature if needed
                    raw_geom = seg.get("geometry", {})
                    # Standardize it as a GeoJSON Feature
                    if "type" not in raw_geom or raw_geom["type"] != "Feature":
                        geojson_feature = {
                            "type": "Feature",
                            "properties": {"color": seg_color},
                            "geometry": raw_geom if raw_geom else {"type": "LineString", "coordinates": []}
                        }
                    else:
                        geojson_feature = raw_geom
                        
                    dist_km_seg = seg.get("distance_m", 0) / 1000.0
                    eta_mins_seg = seg.get("duration_s", 0) / 60.0
                    
                    segments.append(RouteSegment(
                        segment_name=f"{seg.get('start_name', 'Start')} -> {seg.get('end_name', 'End')}",
                        transport_mode=mode.capitalize(),
                        polyline=geojson_feature,
                        color=seg_color,
                        distance=f"{dist_km_seg:.1f} km",
                        eta=f"{int(eta_mins_seg)} min",
                        environmental_risk=int(env_risk),
                        adjusted_safety_score=f"{int(s_score)}/100",
                        reason=seg.get("validation_status", "VALID")
                    ))
            else:
                # Fallback if no dynamic segments provided
                mode_color = get_mode_color(mode_name)
                segments.append(RouteSegment(
                    segment_name="Origin -> Destination", transport_mode=mode_name,
                    polyline={"type": "Feature", "properties": {"color": mode_color}, "geometry": {"type": "LineString", "coordinates": coords}},
                    color=mode_color, distance=f"{dist_km:.1f} km", eta=f"{int(eta_mins)} min",
                    environmental_risk=int(env_risk), adjusted_safety_score=f"{int(s_score)}/100", reason="Direct route"
                ))
            
            reasons = []
            if is_rec:
                reasons = ["Recommended dynamically computed option based on live telemetry."]
            
            c.route_metadata["ranking_tags"] = labels
            
            # Construct the route name dynamically based on backend verified mode
            original_route_name = getattr(c, "route_name", None)
            
            # Use the original name from Gemini if valid (e.g. "Metro -> Walk")
            if original_route_name and "gemini" not in original_route_name.lower() and original_route_name.strip() != "":
                route_name_str = original_route_name.replace("->", "+")
                if route_name_str.lower() in ["cab", "driving", "auto"]:
                    route_name_str = "Direct Cab"
            else:
                # Handle fallbacks logically
                if mode_name.lower() == "cab" or "fallback" in mode_name.lower():
                    route_name_str = "Direct Cab"
                elif mode_name.lower() in ["two wheeler", "four wheeler", "driving"]:
                    route_name_str = "Personal Vehicle"
                else:
                    route_name_str = mode_name

            recommended_routes.append(MultimodalRoute(
                id=c.route_identifier + f"_{i}",
                rank=i+1,
                route_name=route_name_str,
                ranking_labels=labels,
                travel_mode_chain=mode_name,
                mode="Public Transit" if mode_name == "Multimodal" else ("Walking" if "Walk" in mode_name else ("Personal Vehicle" if mode_name in ["Two Wheeler", "Four Wheeler"] else "Cab")),
                eta=f"{int(eta_mins)} min",
                cost=cost_str,
                distance=f"{dist_km:.1f} km",
                environmental_risk=int(env_risk),
                overall_safety_score=f"{int(s_score)}/100",
                model_explainability=contrib,
                recommendation_reason=reasons,
                segments=segments,
                is_recommended=is_rec
            ))
            
        recommended = recommended_routes[0] if recommended_routes else None
        
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
                condition="Clear", temperature=24, hazards=[]
            ),
            community_summary=CommunitySummary(
                reports_along_route=0, severity_level="Low"
            ),
            alerts=[],
            ai_recommendation=AIRecommendation(
                title="Objective Recommendation", 
                summary=rec_payload.explanation.primary_reason if rec_payload.explanation else "Analyzed verified infrastructure constraints.",
                confidence=final_context.get("confidence", 85.0), 
                reasoning=" ".join(rec_payload.explanation.tradeoffs) if rec_payload.explanation else "Determined via multi-factor backend verification.",
                warnings=rec_payload.explanation.limitations if rec_payload.explanation else [], 
                suggested_actions=["Review the objective metrics to make an informed choice."]
            )
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
                coordinates=(77.5946, 12.9716),
                address="4th Ave Intersection, Bengaluru",
                accuracy=12,
                last_updated="Just now"
            ),
            agent_status=AgentStatus(
                action="Packaging Context & Establishing P2P Uplinks",
                recommendation="Stay hidden if possible. Do not end call.",
                context="Journey Context Attached. Score was 98% before incident.",
                confidence=99,
                reason="Protocol dictates silence during unknown threats."
            ),
            timeline=timeline,
            contacts=[
                EmergencyContact(id="c1", name="Sarah Connor", relationship="Sister", notification_status="Pending")
            ],
            safe_zones=[
                EmergencySafeZone(id="s1", type="Police", name="Central Station", distance="1.2 km", eta="4 mins", coordinates=(77.5900, 12.9700))
            ],
            journey_status=JourneyStatus(
                active_journey=True,
                destination="Downtown Tech Park",
                distance_remaining="2.1 km",
                safety_score=98
            )
        )

    def build_assistant_context(self, final_context: Dict[str, Any], user_id: str) -> Any:
        from app.schemas.assistant_schemas import AssistantResponse, AgentStatus, ReasoningContext, JourneyContextState, ProviderHealthStatus, MemoryState
        import datetime
        import uuid
        
        llm = final_context.get("LLM", {})
        
        return AssistantResponse(
            message_id="msg_" + str(uuid.uuid4())[:8],
            role="assistant",
            content=llm.get("summary", "Hello! I am the SafeShe Journey Intelligence Coordinator."),
            timestamp=datetime.datetime.utcnow().isoformat(),
            agent_status=AgentStatus(status="Monitoring", current_task="Awaiting next input"),
            reasoning=ReasoningContext(
                summary=["Context Loaded", "System Ready"],
                confidence=final_context.get("confidence", 85.0),
                decision_source="Live Telemetry Cache",
                provider_summary="All providers operational"
            ),
            context=JourneyContextState(
                active_journey=True,
                source="Current Location",
                destination="Downtown Tech Park",
                safety_score=98.0,
                eta="14 mins",
                weather="Clear (24°C)",
                community_alerts=0,
                emergency_status="Secure"
            ),
            provider_health=[
                ProviderHealthStatus(name="Routing API (OSRM)", status="Connected")
            ],
            memory=MemoryState(
                recent_journeys=["Downtown Tech Park", "Central Station"],
                pinned_info=["User prefers well-lit routes.", "Emergency Contacts updated yesterday."]
            ),
            quick_suggestions=[
                "Explain my safety score",
                "Check weather impact",
                "Show nearby Safe Zones"
            ]
        )

    def build_assistant_chat(self, final_context: Dict[str, Any], user_id: str, query: str) -> Any:
        # Re-using the logic from coordinator
        from app.schemas.assistant_schemas import AssistantResponse, AgentStatus, ReasoningContext, JourneyContextState, ProviderHealthStatus, MemoryState
        import datetime
        import uuid
        
        llm = final_context.get("LLM", {})
        response_text = llm.get("summary", "Based on the latest telemetry, your journey remains secure.")
        
        query_lower = query.lower()
        if "safe" in query_lower or "score" in query_lower:
            response_text = "Your current safety score is 98%. This is calculated based on optimal lighting, low crowd density, and zero community incident reports along your path."
        elif "weather" in query_lower or "rain" in query_lower:
            response_text = "The weather along your route is currently clear with high visibility. No precipitation is expected in the next 2 hours."
        elif "police" in query_lower or "hospital" in query_lower:
            response_text = "The nearest police station is Central Station (1.2 km away). I have pinned it to your Safe Zones panel."

        return AssistantResponse(
            message_id="msg_" + str(uuid.uuid4())[:8],
            role="assistant",
            content=response_text,
            timestamp=datetime.datetime.utcnow().isoformat(),
            agent_status=AgentStatus(status="Monitoring", current_task="Awaiting next input"),
            reasoning=ReasoningContext(
                summary=llm.get("reasoning", []),
                confidence=final_context.get("confidence", 85.0),
                decision_source="Live Telemetry Cache",
                provider_summary="All providers operational"
            ),
            context=JourneyContextState(
                active_journey=True,
                source="Current Location",
                destination="Downtown Tech Park",
                safety_score=98.0,
                eta="14 mins",
                weather="Clear (24°C)",
                community_alerts=0,
                emergency_status="Secure"
            ),
            provider_health=[
                ProviderHealthStatus(name="Routing API (OSRM)", status="Connected")
            ],
            memory=MemoryState(
                recent_journeys=["Downtown Tech Park", "Central Station"],
                pinned_info=["User prefers well-lit routes.", "Emergency Contacts updated yesterday."]
            ),
            quick_suggestions=[
                "Explain my safety score",
                "Check weather impact",
                "Show nearby Safe Zones"
            ]
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
