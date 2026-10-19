from typing import Dict, Any

class LocationMapper:
    """Translates Vendor reverse-geocode JSON into domain string."""
    @staticmethod
    def map_to_domain(vendor_data: Dict[str, Any]) -> str:
        return vendor_data.get("display_name", "Unknown Location")
