from typing import Dict, Any, List

class ReportsMapper:
    """Translates Vendor reports JSON into domain list of dictionaries."""
    @staticmethod
    def map_to_domain(vendor_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        return vendor_data.get("incidents", [])
