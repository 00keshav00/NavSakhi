import time
import uuid
import datetime
from contextlib import contextmanager

class JourneyTrace:
    def __init__(self):
        self.journey_id = f"journey_{uuid.uuid4().hex[:8]}"
        self.trace_data = []

    @contextmanager
    def measure(self, stage_name: str):
        start_time = time.time()
        stage_info = {
            "stage": stage_name,
            "status": "RUNNING",
            "duration_ms": 0,
            "errors": []
        }
        try:
            yield stage_info
            stage_info["status"] = "SUCCESS"
        except Exception as e:
            stage_info["status"] = "FAILED"
            stage_info["errors"].append(str(e))
            raise
        finally:
            stage_info["duration_ms"] = int((time.time() - start_time) * 1000)
            self.trace_data.append(stage_info)
