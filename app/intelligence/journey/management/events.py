from app.intelligence.journey.models import JourneyEvent
import logging

logger = logging.getLogger(__name__)

class EventProcessor:
    """
    First-class component that dispatches all runtime events to intelligence handlers.
    """
    
    def process_event(self, event: JourneyEvent) -> None:
        """
        Dispatches event dynamically based on event_type.
        """
        if event.event_type == "GPS_UPDATE":
            self._handle_gps_update(event)
        elif event.event_type == "SOS_TRIGGERED":
            self._handle_sos_triggered(event)
        elif event.event_type == "MANUAL_REROUTE":
            self._handle_manual_reroute(event)
        else:
            logger.info(f"Unhandled event type: {event.event_type}")

    def _handle_gps_update(self, event: JourneyEvent) -> None:
        # Stub: Forward to monitor
        pass
        
    def _handle_sos_triggered(self, event: JourneyEvent) -> None:
        # Stub: Trigger immediate high-priority safety reroutes
        pass

    def _handle_manual_reroute(self, event: JourneyEvent) -> None:
        # Stub: Forward to reroute manager
        pass
