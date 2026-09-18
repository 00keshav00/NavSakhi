"""Source adapters for assembling dataset inputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Sequence

import pandas as pd


class TabularSource(Protocol):
    """Protocol for a tabular feature source."""

    def fetch(self) -> pd.DataFrame:
        """Fetch source data as a DataFrame."""


@dataclass(slots=True)
class OsmSource:
    """OpenStreetMap-derived tabular source."""

    name: str
    data: pd.DataFrame

    def fetch(self) -> pd.DataFrame:
        return self.data.copy()


@dataclass(slots=True)
class CrimeSource:
    """Crime dataset source."""

    data: pd.DataFrame

    def fetch(self) -> pd.DataFrame:
        return self.data.copy()


@dataclass(slots=True)
class PopulationSource:
    """Population dataset source."""

    data: pd.DataFrame

    def fetch(self) -> pd.DataFrame:
        return self.data.copy()


@dataclass(slots=True)
class EnvironmentalSource:
    """Weather dataset or API-derived source."""

    data: pd.DataFrame

    def fetch(self) -> pd.DataFrame:
        return self.data.copy()


@dataclass(slots=True)
class MobilitySource:
    """Routing and travel-distance source."""

    data: pd.DataFrame

    def fetch(self) -> pd.DataFrame:
        return self.data.copy()


@dataclass(slots=True)
class CommunityReportsSource:
    """Community report source."""

    data: pd.DataFrame

    def fetch(self) -> pd.DataFrame:
        return self.data.copy()


@dataclass(slots=True)
class DataSourceBundle:
    """Container for all upstream feature sources."""

    osm_sources: dict[str, TabularSource] = field(default_factory=dict)
    crime_source: CrimeSource | None = None
    population_source: PopulationSource | None = None
    environmental_source: EnvironmentalSource | None = None
    mobility_source: MobilitySource | None = None
    community_reports_source: CommunityReportsSource | None = None

    def fetch_all(self) -> dict[str, pd.DataFrame]:
        """Fetch every available source into memory."""

        payload: dict[str, pd.DataFrame] = {name: source.fetch() for name, source in self.osm_sources.items()}
        if self.crime_source is not None:
            payload["crime"] = self.crime_source.fetch()
        if self.population_source is not None:
            payload["population"] = self.population_source.fetch()
        if self.environmental_source is not None:
            payload["environmental"] = self.environmental_source.fetch()
        if self.mobility_source is not None:
            payload["mobility"] = self.mobility_source.fetch()
        if self.community_reports_source is not None:
            payload["community_reports"] = self.community_reports_source.fetch()
        return payload
