from app.agents.context import ExecutionContext

class IntentAnalyzer:
    """
    Determines the dominant intent of the user's request.
    Example: Journey Planning, Live Monitoring, Emergency Assistance, Safety Inquiry.
    """
    def analyze(self, context: ExecutionContext) -> str:
        # In a real LLM implementation, we would use the Prompt Builder to classify intent.
        # Since we use mock logic or extension points in this milestone:
        goal = context.goal.lower()
        if "sos" in goal or "emergency" in goal or "help" in goal:
            return "Emergency Assistance"
        elif "route" in goal or "safest path" in goal or "go to" in goal:
            return "Journey Planning"
        elif "monitor" in goal or "tracking" in goal:
            return "Live Monitoring"
        else:
            return "Safety Inquiry"
