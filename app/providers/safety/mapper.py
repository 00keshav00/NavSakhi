from typing import Dict, Any

class SafetyMapper:
    """Translates Vendor safety JSON into domain float."""
    @staticmethod
    def map_to_domain(vendor_data: Dict[str, Any]) -> float:
        # Default fallback logic
        return float(vendor_data.get("risk_score", 0.5))
