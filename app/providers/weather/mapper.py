from typing import Dict, Any

class WeatherMapper:
    """Translates Vendor weather JSON into domain dictionary."""
    @staticmethod
    def map_to_domain(vendor_data: Dict[str, Any]) -> Dict[str, Any]:
        # Minimal mapping for now
        return {
            "temperature": vendor_data.get("main", {}).get("temp"),
            "condition": vendor_data.get("weather", [{}])[0].get("main", "UNKNOWN")
        }
