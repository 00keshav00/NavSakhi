"""Source loader modules for SafeShe dataset engineering."""

from .crime_loader import CrimeFileReport, CrimeLoader, CrimeLoaderConfig, CrimeLoaderError, CrimeSchemaError

try:  # Optional dependency guard so the Crime Loader can be imported standalone.
	from .population_loader import (
		PopulationDataLoadError,
		PopulationLoader,
		PopulationLoaderConfig,
		PopulationLoaderError,
		PopulationLookupError,
		PopulationSchemaError,
	)
except ImportError:  # pragma: no cover - optional dependency may be absent in minimal environments
	PopulationDataLoadError = None  # type: ignore[assignment]
	PopulationLoader = None  # type: ignore[assignment]
	PopulationLoaderConfig = None  # type: ignore[assignment]
	PopulationLoaderError = None  # type: ignore[assignment]
	PopulationLookupError = None  # type: ignore[assignment]
	PopulationSchemaError = None  # type: ignore[assignment]
