from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

class DataSourceRecord(BaseModel):
    source_id: str
    name: str
    authority_level: str
    dataset_type: str
    transport_mode: str
    coverage: str
    license: str
    access_type: str
    update_frequency: str
    last_verified: str
    freshness_policy: str
    status: str
    notes: str

class DataRegistry:
    """
    Authoritative record of what SafeShe trusts.
    Provides evidence hierarchy and provenance gating.
    """
    def __init__(self):
        self.sources: Dict[str, DataSourceRecord] = {}
        self._initialize_baseline_sources()
        
    def _initialize_baseline_sources(self):
        self.register_source(DataSourceRecord(
            source_id="osm_suburban_chennai_2026",
            name="OpenStreetMap Suburban/MRTS Geometry",
            authority_level="TIER 4",
            dataset_type="Static Geographic Network",
            transport_mode="SUBURBAN_RAIL",
            coverage="Chennai Metropolitan Area",
            license="ODbL",
            access_type="Open Data Download",
            update_frequency="Monthly",
            last_verified=datetime.utcnow().isoformat(),
            freshness_policy="30_DAYS",
            status="ACTIVE",
            notes="Geospatial track layout only. Does not assert official service schedules."
        ))
        
        self.register_source(DataSourceRecord(
            source_id="mtc_gtfs_core",
            name="MTC Official GTFS Static",
            authority_level="TIER 1",
            dataset_type="Schedule and Stop Network",
            transport_mode="BUS",
            coverage="Chennai Metropolitan Area",
            license="TBD",
            access_type="Official Partnership Request",
            update_frequency="Weekly",
            last_verified="PENDING_ACQUISITION",
            freshness_policy="7_DAYS",
            status="PENDING",
            notes="Formal acquisition package dispatched to authorities. Currently firewalled."
        ))

    def register_source(self, record: DataSourceRecord):
        self.sources[record.source_id] = record
        
    def get_source(self, source_id: str) -> Optional[DataSourceRecord]:
        return self.sources.get(source_id)
        
    def get_all_active(self) -> List[DataSourceRecord]:
        return [s for s in self.sources.values() if s.status == "ACTIVE"]

global_data_registry = DataRegistry()
