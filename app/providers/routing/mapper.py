from typing import Dict, Any
from app.models.journey import CandidateRoute
from app.providers.routing.models import VendorRouteResponse
from app.providers.shared.exceptions import ProviderResponseMappingError

class RouteMapper:
    """Translates Vendor route JSON into CandidateRoute domain models."""
    @staticmethod
    def map_to_domain(vendor_data: Dict[str, Any]) -> CandidateRoute:
        try:
            response = VendorRouteResponse(**vendor_data)
            first_route = response.routes[0]
            
            return CandidateRoute(
                route_identifier="vendor_route_" + str(hash(str(first_route))),
                distance=first_route.get("distance", 0.0),
                duration=first_route.get("duration", 0.0),
                recommendation_status="PENDING",
                route_metadata={"geometry": first_route.get("geometry")}
            )
        except Exception as e:
            raise ProviderResponseMappingError(f"Failed to map route: {str(e)}")
