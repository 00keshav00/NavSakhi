import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TelemetryManager:
    """
    Manages live active journeys.
    Responsible for polling telemetry (or receiving it via websockets) and triggering the Intelligence Pipeline 
    every 30 seconds to check for environmental changes.
    """
    def __init__(self, coordinator=None):
        self.active_journeys: Dict[str, Dict[str, Any]] = {}
        self.coordinator = coordinator # JourneyIntelligenceCoordinator instance
        self.polling_task: Optional[asyncio.Task] = None
        self._running = False

    def start_polling(self):
        if not self._running:
            self._running = True
            self.polling_task = asyncio.create_task(self._poll_loop())
            logger.info("TelemetryManager polling loop started.")

    def stop_polling(self):
        self._running = False
        if self.polling_task:
            self.polling_task.cancel()
            logger.info("TelemetryManager polling loop stopped.")

    def register_journey(self, journey_id: str, context: Dict[str, Any]):
        self.active_journeys[journey_id] = {
            "context": context,
            "last_updated": datetime.utcnow().isoformat(),
            "status": "active",
            "metrics": {
                "distance_remaining": 0,
                "current_eta_mins": 0
            }
        }
        logger.info(f"Registered journey {journey_id} for telemetry tracking.")
        if not self._running:
            self.start_polling()

    def unregister_journey(self, journey_id: str):
        if journey_id in self.active_journeys:
            del self.active_journeys[journey_id]
            logger.info(f"Unregistered journey {journey_id}.")
        if not self.active_journeys:
            self.stop_polling()

    def update_telemetry(self, journey_id: str, telemetry: Dict[str, Any]):
        """
        Called when the client pushes new GPS coordinates or speed.
        """
        if journey_id in self.active_journeys:
            self.active_journeys[journey_id]["context"].update(telemetry)
            self.active_journeys[journey_id]["last_updated"] = datetime.utcnow().isoformat()

    async def _poll_loop(self):
        while self._running:
            try:
                await asyncio.sleep(30) # 30 second refresh cycle
                if not self.active_journeys:
                    continue
                    
                logger.info(f"TelemetryManager: Refreshing {len(self.active_journeys)} active journeys.")
                for journey_id, data in list(self.active_journeys.items()):
                    await self._refresh_journey(journey_id, data)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in telemetry poll loop: {e}")

    async def _refresh_journey(self, journey_id: str, data: Dict[str, Any]):
        """
        Executes the entire agentic pipeline for the journey and evaluates if rerouting is necessary.
        """
        if not self.coordinator:
            return
            
        try:
            # Re-execute the intelligence pipeline using the latest context
            context = data["context"]
            
            # The coordinator will automatically trigger Routing, Weather, Community tools
            final_context = await self.coordinator.execute_pipeline("journey_plan", context)
            
            # Extract decision
            decision = final_context.get("Decision", {})
            ml_prediction = final_context.get("MLPrediction", {})
            routing = final_context.get("RoutingAgent", {})
            
            # Check for route change recommendation
            recommended_route = decision.get("recommended_route")
            current_route = context.get("current_route_id")
            
            # We simulate a recommendation push if the newly recommended route is different
            if recommended_route and current_route and recommended_route != current_route:
                logger.info(f"TelemetryManager: Safer route available for {journey_id}! Pushing recommendation.")
                await self._push_notification(journey_id, {
                    "type": "ROUTE_CHANGE_RECOMMENDATION",
                    "message": "A significantly safer route is available.",
                    "new_safety_score": ml_prediction.get("safety_score", 99.0),
                    "reason": decision.get("warnings", ["Optimal conditions on alternative route"])[0]
                })
                
            # Update internal metrics
            data["metrics"]["distance_remaining"] = routing.get("distance", "Unknown")
            data["metrics"]["current_eta_mins"] = routing.get("eta", "Unknown")
            
        except Exception as e:
            logger.error(f"Error refreshing journey {journey_id}: {e}")

    async def _push_notification(self, journey_id: str, payload: Dict[str, Any]):
        """
        In a real implementation, this would publish to a Redis pub/sub channel
        or push directly to connected WebSocket clients.
        """
        # For now, we will store it in a globally accessible event queue or print
        logger.info(f"Notification for {journey_id}: {payload}")
        
        # We can implement a simple in-memory queue that the websocket endpoint can consume from
        from app.api.websockets.journey_ws import journey_manager
        await journey_manager.send_personal_message(payload, journey_id)
