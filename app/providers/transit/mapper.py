from typing import Dict, Any, List

class TransitMapper:
    """Translates Vendor transit JSON into domain dictionaries."""
    @staticmethod
    def map_to_domain(vendor_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        return vendor_data.get("segments", [])
