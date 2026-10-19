from typing import Dict, Any

class CrowdMapper:
    """Translates Vendor crowd JSON into domain float."""
    @staticmethod
    def map_to_domain(vendor_data: Dict[str, Any]) -> float:
        # High crowd score = highly crowded
        return float(vendor_data.get("density_score", 0.0))
