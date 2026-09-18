from abc import ABC, abstractmethod
from typing import Dict, Any, List
from app.models.journey import Location, CandidateRoute, POI, Address, RoadInfo, WeatherState, TransitSegment, POICollection, TransitCollection, RouteCollection
from app.models.community import CommunityReport, ReportCollection

class RoutingProvider(ABC):
    @abstractmethod
    def get_routes(self, source: Location, destination: Location, mode: str, alternatives: int = 3) -> List[CandidateRoute]:
        raise NotImplementedError

class WeatherProvider(ABC):
    @abstractmethod
    def get_weather(self, location: Location) -> WeatherState:
        raise NotImplementedError

class SafetyProvider(ABC):
    @abstractmethod
    def get_safety_score(self, location: Location) -> float:
        raise NotImplementedError

class CrowdProvider(ABC):
    @abstractmethod
    def get_crowd_density(self, location: Location) -> float:
        raise NotImplementedError

class ReportsProvider(ABC):
    @abstractmethod
    def get_nearby_reports(self, location: Location, radius_m: int = 1000) -> ReportCollection:
        raise NotImplementedError

    @abstractmethod
    def get_recent_reports(self, limit: int = 50) -> ReportCollection:
        raise NotImplementedError

    @abstractmethod
    def get_report_count(self, location: Location, radius_m: int = 1000) -> int:
        raise NotImplementedError

    @abstractmethod
    def get_report_by_id(self, report_id: str) -> CommunityReport:
        raise NotImplementedError

    @abstractmethod
    def create_report(self, report: CommunityReport) -> CommunityReport:
        raise NotImplementedError

class TransitProvider(ABC):
    @abstractmethod
    def get_transit_segments(self, source: Location, destination: Location) -> TransitCollection:
        raise NotImplementedError

class LocationProvider(ABC):
    @abstractmethod
    def reverse_geocode(self, location: Location) -> Address:
        raise NotImplementedError

    @abstractmethod
    def forward_geocode(self, address: str) -> Location:
        raise NotImplementedError

    @abstractmethod
    def get_nearby_pois(self, location: Location, poi_type: str, radius_m: int = 500) -> POICollection:
        raise NotImplementedError

    @abstractmethod
    def get_road_type(self, location: Location) -> RoadInfo:
        raise NotImplementedError
