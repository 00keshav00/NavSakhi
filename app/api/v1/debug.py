from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any

from app.intelligence.journey.providers import RoutingProvider, LocationProvider, WeatherProvider, ReportsProvider, TransitProvider
from app.models.journey import Location, CandidateRoute, Address, POICollection, RoadInfo, WeatherState, TransitCollection, RouteCollection
from app.models.community import ReportCollection
from app.api.dependencies import get_routing_provider, get_location_provider, get_weather_provider, get_reports_provider, get_transit_provider, get_journey_coordinator
from app.intelligence.journey.coordinator import JourneyIntelligenceCoordinator

router = APIRouter()

class CoordinateInput(BaseModel):
    lat: float
    lon: float

class DebugRoutingRequest(BaseModel):
    source: CoordinateInput
    destination: CoordinateInput

class DebugLocationRequest(BaseModel):
    latitude: float
    longitude: float

class DebugLocationResponse(BaseModel):
    address: Address
    road_info: RoadInfo
    hospitals: POICollection
    police_stations: POICollection
    restaurants: POICollection
    bus_stops: POICollection
    metro_stations: POICollection

class DebugWeatherRequest(BaseModel):
    latitude: float
    longitude: float

class DebugReportsRequest(BaseModel):
    latitude: float
    longitude: float
    radius: int = 1000

class DebugTransitRequest(BaseModel):
    source: CoordinateInput
    destination: CoordinateInput

class DebugJourneyRequest(BaseModel):
    source: CoordinateInput
    destination: CoordinateInput

class DebugJourneyResponse(BaseModel):
    routes: RouteCollection
    weather: WeatherState
    pois: POICollection
    reports: ReportCollection
    transit: TransitCollection

@router.post("/providers/routing", response_model=CandidateRoute)
async def debug_routing_provider(
    request: DebugRoutingRequest,
    provider: RoutingProvider = Depends(get_routing_provider)
) -> CandidateRoute:
    """
    Debug endpoint to directly fetch a route from the Routing Provider.
    """
    source_loc = Location(coordinates=[request.source.lon, request.source.lat])
    dest_loc = Location(coordinates=[request.destination.lon, request.destination.lat])
    
    # Defaulting mode to driving for debug purposes
    route = await provider.get_route(source=source_loc, destination=dest_loc, mode="driving")
    return route

@router.post("/providers/location", response_model=DebugLocationResponse)
async def debug_location_provider(
    request: DebugLocationRequest,
    provider: LocationProvider = Depends(get_location_provider)
) -> DebugLocationResponse:
    """
    Debug endpoint to fetch complete location context from Location Provider.
    """
    loc = Location(coordinates=[request.longitude, request.latitude])
    
    address = await provider.reverse_geocode(loc)
    road_info = await provider.get_road_type(loc)
    
    hospitals = await provider.get_nearby_pois(loc, "hospital", 1000)
    police = await provider.get_nearby_pois(loc, "police", 1500)
    restaurants = await provider.get_nearby_pois(loc, "restaurant", 500)
    bus_stops = await provider.get_nearby_pois(loc, "bus_stop", 500)
    metro = await provider.get_nearby_pois(loc, "metro", 1000)
    
    return DebugLocationResponse(
        address=address,
        road_info=road_info,
        hospitals=hospitals,
        police_stations=police,
        restaurants=restaurants,
        bus_stops=bus_stops,
        metro_stations=metro
    )

@router.post("/providers/weather", response_model=WeatherState)
async def debug_weather_provider(
    request: DebugWeatherRequest,
    provider: WeatherProvider = Depends(get_weather_provider)
) -> WeatherState:
    """
    Debug endpoint to fetch weather state from Weather Provider.
    """
    loc = Location(coordinates=[request.longitude, request.latitude])
    return await provider.get_weather(loc)

@router.post("/providers/reports", response_model=ReportCollection)
async def debug_reports_provider(
    request: DebugReportsRequest,
    provider: ReportsProvider = Depends(get_reports_provider)
) -> ReportCollection:
    """
    Debug endpoint to fetch nearby reports from Reports Provider.
    """
    loc = Location(coordinates=[request.longitude, request.latitude])
    return await provider.get_nearby_reports(loc, request.radius)

@router.post("/providers/transit", response_model=TransitCollection)
async def debug_transit_provider(
    request: DebugTransitRequest,
    provider: TransitProvider = Depends(get_transit_provider)
) -> TransitCollection:
    """
    Debug endpoint to fetch transit segments from Transit Provider.
    """
    source_loc = Location(coordinates=[request.source.lon, request.source.lat])
    dest_loc = Location(coordinates=[request.destination.lon, request.destination.lat])
    return await provider.get_transit_segments(source_loc, dest_loc)

@router.post("/journey", response_model=DebugJourneyResponse)
async def debug_journey_orchestration(
    request: DebugJourneyRequest,
    coordinator: JourneyIntelligenceCoordinator = Depends(get_journey_coordinator)
) -> DebugJourneyResponse:
    """
    Debug endpoint to fetch complete orchestrated journey context.
    """
    source_loc = Location(coordinates=[request.source.lon, request.source.lat])
    dest_loc = Location(coordinates=[request.destination.lon, request.destination.lat])
    
    context = await coordinator.gather_journey_context(source_loc, dest_loc)
    
    return DebugJourneyResponse(**context)
