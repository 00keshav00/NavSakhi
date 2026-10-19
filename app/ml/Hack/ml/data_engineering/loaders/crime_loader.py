"""Crime Loader for the SafeShe dataset engineering pipeline.

This loader discovers the real crime CSVs in the repository, detects their
schemas automatically, maps each dataset into a unified internal schema,
preserves useful source attributes, and computes a bounded crime score.

The implementation is intentionally dataset-specific. It supports the actual
repository files rather than relying on a generic district/crime_value layout.
"""

from __future__ import annotations

import csv
import logging
import math
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from statistics import fmean
from typing import Any, Iterable, Sequence

from ...config.paths import PROCESSED_DATASETS_DIR, PROJECT_ROOT, RAW_DATASETS_DIR, CRIME_DIRECTORY, CRIME_FEATURES


RECORD_TYPE_MAP = {
    "Ariyalur":          "revenue_district",
    "Chengalpattu":      "revenue_district",
    "Chennai":           "revenue_district",
    "Coimbatore":        "revenue_district",
    "Cuddalore":         "revenue_district",
    "Dharmapuri":        "revenue_district",
    "Dindigul":          "revenue_district",
    "Erode":             "revenue_district",
    "Kallakurichi":      "revenue_district",
    "Kancheepuram":      "revenue_district",
    "Kanniyakumari":     "revenue_district",
    "Karur":             "revenue_district",
    "Krishnagiri":       "revenue_district",
    "Madurai":           "revenue_district",
    "Mayiladuthurai":    "revenue_district",
    "Nagapattinam":      "revenue_district",
    "Namakkal":          "revenue_district",
    "Perambalur":        "revenue_district",
    "Pudukkottai":       "revenue_district",
    "Ramanathapuram":    "revenue_district",
    "Ranipet":           "revenue_district",
    "Salem":             "revenue_district",
    "Sivaganga":         "revenue_district",
    "Tenkasi":           "revenue_district",
    "Thanjavur":         "revenue_district",
    "Theni":             "revenue_district",
    "The Nilgiris":      "revenue_district",
    "Thoothukudi":       "revenue_district",
    "Tiruchirappalli":   "revenue_district",
    "Tirunelveli":       "revenue_district",
    "Tirupattur":        "revenue_district",
    "Tiruppur":          "revenue_district",
    "Tiruvallur":        "revenue_district",
    "Tiruvannamalai":    "revenue_district",
    "Tiruvarur":         "revenue_district",
    "Vellore":           "revenue_district",
    "Viluppuram":        "revenue_district",
    "Virudhunagar":      "revenue_district",
    "Coimbatore City":       "commissionerate",
    "Madurai City":          "commissionerate",
    "Salem City":            "commissionerate",
    "Tirunelveli City":      "commissionerate",
    "Tiruchirappalli City":  "commissionerate",
    "Tiruppur City":         "commissionerate",
    "Avadi":                 "commissionerate",
    "Tambaram":              "commissionerate",
    "Railway Chennai":       "railway_police",
    "Railway Trichy":        "railway_police",
    "Cyber Cell":            "special_unit",
    "TOTAL":                 "aggregate_total",
    "TOTAL DISTRICT(S)":     "aggregate_total",
    "Other Units":           "aggregate_total",
    "India":                 "aggregate_total",
    "Tamil Nadu State":      "aggregate_total",
}


class CrimeLoaderError(RuntimeError):
    """Base error for the Crime Loader module."""


class CrimeSchemaError(CrimeLoaderError):
    """Raised when an input CSV does not match a supported crime schema."""


class CrimeDataLoadError(CrimeLoaderError):
    """Raised when a crime source file cannot be loaded."""


class CrimeScoreError(CrimeLoaderError):
    """Raised when crime score computation fails."""


@dataclass(slots=True)
class CrimeLoaderConfig:
    """Configuration for the SafeShe Crime Loader."""

    discovery_roots: tuple[Path, ...] = (CRIME_DIRECTORY, PROJECT_ROOT)
    output_path: Path = CRIME_FEATURES
    allow_project_root_fallback: bool = True
    district_aliases: dict[str, str] = field(default_factory=dict)
    remove_district_suffix: bool = True
    remove_city_suffix: bool = False
    neutral_score: float = 50.0
    cache_discovery: bool = True
    save_manifest: bool = False
    score_weights_by_schema: dict[str, dict[str, float]] = field(default_factory=dict)
    score_inversion_fields_by_schema: dict[str, tuple[str, ...]] = field(default_factory=dict)
    score_excluded_fields_by_schema: dict[str, tuple[str, ...]] = field(default_factory=dict)
    source_year_overrides: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class CrimeFileReport:
    """Per-file audit report for the Crime Loader run."""

    file_path: Path
    discovery_root: Path
    status: str
    schema_id: str | None = None
    rows_loaded: int = 0
    rows_written: int = 0
    detected_columns: tuple[str, ...] = ()
    mapped_columns: tuple[str, ...] = ()
    skipped_reason: str | None = None
    district_samples_before: tuple[str, ...] = ()
    district_samples_after: tuple[str, ...] = ()


@dataclass(slots=True)
class CrimeLoaderResult:
    """Result metadata returned after building the crime dataset."""

    output_path: Path
    rows_written: int
    column_count: int
    unique_district_count: int
    crime_score_min: float | None
    crime_score_max: float | None
    file_reports: tuple[CrimeFileReport, ...]


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.replace("\r", " ").replace("\n", " ")
    normalized = re.sub(r"[\.,/\\()\-]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip().casefold()
    return normalized


def _canonical_field_name(header: str) -> str:
    normalized = _normalize_text(header)
    normalized = normalized.replace("&", " and ")
    normalized = normalized.replace("%", " percent ")
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized


def _to_number(value: Any) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return value
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", "")
    text = text.replace("%", "")
    if text in {"-", "na", "n/a", "null", "none"}:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if number.is_integer():
        return int(number)
    return number


def _normalize_district_name(value: Any, config: CrimeLoaderConfig) -> str:
    if value is None:
        return "Unknown"
    text = str(value).strip()
    if not text:
        return "Unknown"

    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("\r", " ").replace("\n", " ")
    normalized = re.sub(r"[\.,/\\_]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    
    if normalized.upper() in ("TOTAL", "TOTAL DISTRICT(S)"):
        return normalized.upper()

    cf_normalized = normalized.casefold()
    if config.remove_district_suffix:
        cf_normalized = re.sub(r"\b(district|dist|dt)\b", "", cf_normalized)
    if config.remove_city_suffix:
        cf_normalized = re.sub(r"\b(city|cities)\b", "", cf_normalized)

    cf_normalized = re.sub(r"\s+", " ", cf_normalized).strip()
    if not cf_normalized:
        return "Unknown"

    if cf_normalized in config.district_aliases:
        cf_normalized = config.district_aliases[cf_normalized]

    cf_normalized = re.sub(r"\s+", " ", cf_normalized).strip()
    result = cf_normalized.title() if cf_normalized else "Unknown"

    SPELLING_CORRECTIONS = {
        "Kanchipuram":     "Kancheepuram",
        "Kanyakumari":     "Kanniyakumari",
        "Nilgiris":        "The Nilgiris",
        "Pudukottai":      "Pudukkottai",
        "Ramnathapuram":   "Ramanathapuram",
        "Sivagangai":      "Sivaganga",
        "Thirunelveli":    "Tirunelveli",
        "Thiruvallur":     "Tiruvallur",
        "Thiruvannamalai": "Tiruvannamalai",
        "Thiruvarur":      "Tiruvarur",
        "Trichy":          "Tiruchirappalli",
        "Trichy City":     "Tiruchirappalli City",
        "Villupuram":      "Viluppuram",
        "Tiruppattur":     "Tirupattur",
        "Thirunelveli City": "Tirunelveli City",
    }
    
    return SPELLING_CORRECTIONS.get(result, result)


def _min_max(values: Sequence[float | int | None]) -> tuple[float, float] | None:
    numeric: list[float] = []
    for value in values:
        if value is None:
            continue
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(numeric_value):
            continue
        numeric.append(numeric_value)
    if not numeric:
        return None
    minimum = min(numeric)
    maximum = max(numeric)
    return minimum, maximum


def _normalize_value(value: float | int | None, value_range: tuple[float, float] | None, neutral_score: float) -> float:
    if value is None or value_range is None:
        return float(neutral_score)
    minimum, maximum = value_range
    if math.isclose(minimum, maximum):
        return float(neutral_score)
    normalized = (float(value) - minimum) / (maximum - minimum)
    normalized = max(0.0, min(1.0, normalized))
    return float(normalized * 100.0)


def _weighted_score(
    record: dict[str, Any],
    score_fields: tuple[str, ...],
    field_ranges: dict[str, tuple[float, float]],
    field_weights: dict[str, float],
    inverse_fields: tuple[str, ...],
    neutral_score: float,
) -> float:
    weighted_values: list[tuple[float, float]] = []
    for field in score_fields:
        raw_value = record.get(field)
        numeric_value = _to_number(raw_value)
        if numeric_value is None:
            continue
        normalized_value = _normalize_value(numeric_value, field_ranges.get(field), neutral_score)
        if field in inverse_fields:
            normalized_value = 100.0 - normalized_value
        weight = float(field_weights.get(field, 1.0))
        if weight <= 0:
            continue
        weighted_values.append((normalized_value, weight))

    if not weighted_values:
        return float(neutral_score)

    total_weight = sum(weight for _, weight in weighted_values)
    if total_weight <= 0:
        return float(neutral_score)
    return float(sum(value * weight for value, weight in weighted_values) / total_weight)


class CrimeDatasetAdapter:
    """Adapter for a supported crime dataset schema."""

    schema_id: str = "base"
    display_name: str = "Base Crime Dataset"
    required_columns: tuple[str, ...] = ()
    district_columns: tuple[str, ...] = ()
    metadata_columns: tuple[str, ...] = ()
    ignored_columns: tuple[str, ...] = ()
    score_excluded_columns: tuple[str, ...] = ()
    default_district: str | None = None
    default_state: str | None = None
    default_year: int | None = None
    score_field_weights: dict[str, float] = {}
    score_inverse_fields: tuple[str, ...] = ()

    def can_handle(self, normalized_headers: set[str], file_name: str) -> bool:
        return all(_normalize_text(column) in normalized_headers for column in self.required_columns)

    def file_name_matches(self, file_name: str) -> bool:
        return True

    def validate_headers(self, headers: tuple[str, ...]) -> None:
        normalized = {_normalize_text(header) for header in headers}
        missing = [column for column in self.required_columns if _normalize_text(column) not in normalized]
        if missing:
            raise CrimeSchemaError(
                f"{self.display_name} is missing required columns: {missing}"
            )

    def adapt(self, file_path: Path, rows: list[dict[str, str]], config: CrimeLoaderConfig) -> tuple[list[dict[str, Any]], CrimeFileReport]:
        if not rows:
            raise CrimeSchemaError(f"Crime source file is empty: {file_path}")

        headers = tuple(rows[0].keys())
        self.validate_headers(headers)

        normalized_headers = {_normalize_text(header): header for header in headers}
        raw_district_samples: list[str] = []
        adapted_records: list[dict[str, Any]] = []

        for row_index, row in enumerate(rows, start=1):
            record = self._adapt_row(row, row_index=row_index, file_path=file_path, config=config, normalized_headers=normalized_headers)
            if record.get("district_raw") not in (None, ""):
                raw_district_samples.append(str(record.get("district_raw")))
            adapted_records.append(record)

        score_fields = self._score_fields(adapted_records)
        field_ranges = {
            field: rng
            for field, rng in self._compute_field_ranges(adapted_records, score_fields).items()
        }
        field_weights = self._field_weights(config)
        inverse_fields = self._inverse_fields(config)

        for record in adapted_records:
            record["crime_score"] = round(
                _weighted_score(
                    record,
                    score_fields=score_fields,
                    field_ranges=field_ranges,
                    field_weights=field_weights,
                    inverse_fields=inverse_fields,
                    neutral_score=config.neutral_score,
                ),
                2,
            )

        report = CrimeFileReport(
            file_path=file_path,
            discovery_root=file_path.parent,
            status="processed",
            schema_id=self.schema_id,
            rows_loaded=len(rows),
            rows_written=len(adapted_records),
            detected_columns=headers,
            mapped_columns=tuple(self._mapped_columns(headers)),
            district_samples_before=tuple(raw_district_samples[:5]),
            district_samples_after=tuple(sorted({str(record.get("district")) for record in adapted_records if record.get("district")} )[:5]),
        )
        return adapted_records, report

    def _adapt_row(
        self,
        row: dict[str, str],
        row_index: int,
        file_path: Path,
        config: CrimeLoaderConfig,
        normalized_headers: dict[str, str],
    ) -> dict[str, Any]:
        record: dict[str, Any] = {
            "schema_id": self.schema_id,
            "schema_name": self.display_name,
            "source_file": file_path.name,
            "source_path": str(file_path),
            "source_row": row_index,
            "record_type": self.schema_id,
        }

        if self.default_district is not None:
            record["district_raw"] = self.default_district
            record["district"] = self.default_district
        else:
            district_column = self._resolve_source_column(row, self.district_columns)
            raw_district = row.get(district_column, "") if district_column else ""
            record["district_raw"] = raw_district
            record["district"] = _normalize_district_name(raw_district, config)

        if self.default_state is not None:
            record["state_name"] = self.default_state

        if self.default_year is not None:
            record["year"] = self.default_year
        else:
            year_column = self._resolve_source_column(row, ("year", "year_of_data"))
            if year_column:
                record["year"] = _to_number(row.get(year_column))

        for header, value in row.items():
            canonical_header = _canonical_field_name(header)
            if canonical_header in { _canonical_field_name(col) for col in self.ignored_columns }:
                continue
            if canonical_header in { _canonical_field_name(col) for col in self.metadata_columns }:
                continue
            record[canonical_header] = self._coerce_value(value)

        return record

    def _mapped_columns(self, headers: tuple[str, ...]) -> tuple[str, ...]:
        mapped = []
        ignored = {_canonical_field_name(column) for column in self.ignored_columns}
        metadata = {_canonical_field_name(column) for column in self.metadata_columns}
        for header in headers:
            canonical = _canonical_field_name(header)
            if canonical not in ignored and canonical not in metadata:
                mapped.append(f"{header} -> {canonical}")
        return tuple(mapped)

    def _score_fields(self, records: list[dict[str, Any]]) -> tuple[str, ...]:
        excluded = {_canonical_field_name(column) for column in self.score_excluded_columns}
        excluded.update({_canonical_field_name(column) for column in self.metadata_columns})
        numeric_fields: list[str] = []
        seen: set[str] = set()
        for record in records:
            for key, value in record.items():
                canonical_key = _canonical_field_name(key)
                if canonical_key in excluded or canonical_key in seen:
                    continue
                if key in {"crime_score", "schema_id", "schema_name", "source_file", "source_path", "source_row", "record_type", "district", "district_raw", "state_name"}:
                    continue
                if _to_number(value) is not None:
                    seen.add(canonical_key)
                    numeric_fields.append(key)
        return tuple(numeric_fields)

    def _field_weights(self, config: CrimeLoaderConfig) -> dict[str, float]:
        weights = dict(self.score_field_weights)
        weights.update(config.score_weights_by_schema.get(self.schema_id, {}))
        return weights

    def _inverse_fields(self, config: CrimeLoaderConfig) -> tuple[str, ...]:
        configured = config.score_inversion_fields_by_schema.get(self.schema_id)
        if configured is not None:
            return configured
        return self.score_inverse_fields

    def _compute_field_ranges(self, records: list[dict[str, Any]], score_fields: tuple[str, ...]) -> dict[str, tuple[float, float]]:
        ranges: dict[str, tuple[float, float]] = {}
        for field in score_fields:
            values = [_to_number(record.get(field)) for record in records]
            field_range = _min_max(values)
            if field_range is not None:
                ranges[field] = field_range
        return ranges

    @staticmethod
    def _coerce_value(value: Any) -> Any:
        numeric_value = _to_number(value)
        if numeric_value is not None:
            return numeric_value
        text = "" if value is None else str(value).strip()
        if text == "":
            return None
        return text

    @staticmethod
    def _resolve_source_column(row: dict[str, str], candidate_columns: Sequence[str]) -> str | None:
        normalized_row = {_normalize_text(key): key for key in row.keys()}
        for candidate in candidate_columns:
            normalized_candidate = _normalize_text(candidate)
            if normalized_candidate in normalized_row:
                return normalized_row[normalized_candidate]
        return None


class TNOverallAdapter(CrimeDatasetAdapter):
    schema_id = "tn_overall"
    display_name = "Tamil Nadu Crime Statistics 2014-2024"
    required_columns = (
        "Year",
        "Total_Crime_Cases",
        "IPC_Cases",
        "SLL_Cases",
        "Murders",
        "Attempt_to_Murder",
        "Rape",
        "Assault_on_Women",
        "Theft",
        "Burglary",
        "Robbery",
        "Crime_Against_Women",
        "Conviction_Rate",
        "Crime_Rate_per_100k",
    )
    metadata_columns = ("Year",)
    default_district = "Tamil Nadu State"
    default_state = "Tamil Nadu"
    score_excluded_columns = ("Year",)
    score_inverse_fields = ("conviction_rate",)


class TNWomenAdapter(CrimeDatasetAdapter):
    schema_id = "tn_women"
    display_name = "Tamil Nadu Crimes Against Women 2023"
    required_columns = ("Districts/City",)
    district_columns = ("Districts/City",)
    metadata_columns = ("Sl No", "Districts/City")
    default_state = "Tamil Nadu"
    default_year = 2023
    score_excluded_columns = ("Sl No", "Districts/City")


class NCRBJuvenileAdapterA(CrimeDatasetAdapter):
    schema_id = "ncrb_juvenile_a"
    display_name = "NCRB CII 2023 Table 5A.4A"
    required_columns = ("Crime Head",)
    metadata_columns = ("Sl. No.", "Crime Head")
    default_district = "India"
    default_state = "India"
    default_year = 2023
    score_excluded_columns = ("Sl. No.", "Crime Head")

    def file_name_matches(self, file_name: str) -> bool:
        normalized = _normalize_text(file_name)
        return "5a 4a" in normalized or "5a4a" in normalized


class NCRBJuvenileAdapterB(CrimeDatasetAdapter):
    schema_id = "ncrb_juvenile_b"
    display_name = "NCRB CII 2023 Table 5A.4B"
    required_columns = ("Crime Head",)
    metadata_columns = ("Sl. No.", "Crime Head")
    default_district = "India"
    default_state = "India"
    default_year = 2023
    score_excluded_columns = ("Sl. No.", "Crime Head")

    def file_name_matches(self, file_name: str) -> bool:
        normalized = _normalize_text(file_name)
        return "5a 4b" in normalized or "5a4b" in normalized


class ComplaintReportsAdapter(CrimeDatasetAdapter):
    schema_id = "district_complaints"
    display_name = "District Complaint Reports"
    required_columns = ("District", "Total Complaints")
    district_columns = ("District",)
    metadata_columns = ("Sl. No", "District")
    default_state = "Tamil Nadu"
    score_excluded_columns = ("Sl. No", "District")


@dataclass(slots=True)
class CrimeLoaderReport:
    """Complete run report for the Crime Loader."""

    processed_files: tuple[CrimeFileReport, ...]
    skipped_files: tuple[CrimeFileReport, ...]
    output_path: Path
    rows_written: int
    column_count: int
    unique_district_count: int
    crime_score_min: float | None
    crime_score_max: float | None


class CrimeLoader:
    """Load, validate, merge, and score the real crime CSV files in the repo."""

    def __init__(self, config: CrimeLoaderConfig | None = None, logger: logging.Logger | None = None) -> None:
        self.config = config or CrimeLoaderConfig()
        self.logger = logger or logging.getLogger(__name__)
        self.adapters: tuple[CrimeDatasetAdapter, ...] = (
            TNOverallAdapter(),
            TNWomenAdapter(),
            NCRBJuvenileAdapterA(),
            NCRBJuvenileAdapterB(),
            ComplaintReportsAdapter(),
        )

    def build(self) -> CrimeLoaderReport:
        """Discover, adapt, score, and write the unified crime dataset."""
        import time
        start_time = time.time()
        self.logger.info(f"START: CrimeLoader | Output: {self.config.output_path}")
        discovered_files = self.discover_files()
        processed_rows: list[dict[str, Any]] = []
        processed_reports: list[CrimeFileReport] = []
        skipped_reports: list[CrimeFileReport] = []

        for file_path, discovery_root in discovered_files:
            try:
                records, report = self._process_file(file_path=file_path, discovery_root=discovery_root)
            except CrimeSchemaError as exc:
                skipped_reports.append(
                    CrimeFileReport(
                        file_path=file_path,
                        discovery_root=discovery_root,
                        status="skipped",
                        skipped_reason=str(exc),
                    )
                )
                self.logger.warning("Skipped %s: %s", file_path, exc)
                continue
            except CrimeDataLoadError as exc:
                skipped_reports.append(
                    CrimeFileReport(
                        file_path=file_path,
                        discovery_root=discovery_root,
                        status="skipped",
                        skipped_reason=str(exc),
                    )
                )
                self.logger.warning("Skipped %s: %s", file_path, exc)
                continue

            processed_rows.extend(records)
            processed_reports.append(report)
            self.logger.info(
                "Processed %s | schema=%s | rows_loaded=%s | rows_written=%s",
                file_path.name,
                report.schema_id,
                report.rows_loaded,
                report.rows_written,
            )

        if not processed_rows:
            raise CrimeLoaderError("No supported crime CSV files could be processed.")

        revenue_districts = []
        commissionerates = []
        railway_police = []
        special_units = []

        for row in processed_rows:
            dist = row.get("district", "Unknown")
            classification = RECORD_TYPE_MAP.get(dist, "unknown")
            if classification == "revenue_district":
                revenue_districts.append(row)
            elif classification == "commissionerate":
                commissionerates.append(row)
            elif classification == "railway_police":
                railway_police.append(row)
            elif classification == "special_unit":
                special_units.append(row)

        if not revenue_districts:
            raise CrimeLoaderError("No revenue district records found after processing.")

        self._write_output(revenue_districts, self.config.output_path)
        if commissionerates:
            self._write_output(commissionerates, self.config.output_path.with_name("crime_score_commissionerates.csv"))
        if railway_police:
            self._write_output(railway_police, self.config.output_path.with_name("crime_score_railway.csv"))
        if special_units:
            self._write_output(special_units, self.config.output_path.with_name("crime_score_special_units.csv"))

        crime_scores = [float(row["crime_score"]) for row in revenue_districts if row.get("crime_score") is not None]
        districts = {str(row.get("district")) for row in revenue_districts if row.get("district")}

        result = CrimeLoaderReport(
            processed_files=tuple(processed_reports),
            skipped_files=tuple(skipped_reports),
            output_path=self.config.output_path,
            rows_written=len(revenue_districts),
            column_count=len(self._union_fieldnames(revenue_districts)),
            unique_district_count=len(districts),
            crime_score_min=min(crime_scores) if crime_scores else None,
            crime_score_max=max(crime_scores) if crime_scores else None,
        )

        if self.config.save_manifest:
            manifest_path = self.config.output_path.with_suffix(".manifest.json")
            self._write_manifest(result, manifest_path)

        duration = time.time() - start_time
        self.logger.info(
            f"COMPLETED: CrimeLoader | Duration: {duration:.2f}s | Processed Rows: {result.rows_written} | Output: {result.output_path}"
        )
        return result

    def discover_files(self) -> tuple[tuple[Path, Path], ...]:
        """Discover all crime CSV files under the configured roots."""

        discovered: list[tuple[Path, Path]] = []
        seen: set[Path] = set()

        primary_root = RAW_DATASETS_DIR
        if primary_root.exists():
            for csv_file in primary_root.rglob("*.csv"):
                resolved = csv_file.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                discovered.append((resolved, primary_root.resolve()))

        if not discovered and self.config.allow_project_root_fallback:
            fallback_root = PROJECT_ROOT
            if fallback_root.exists():
                for csv_file in fallback_root.rglob("*.csv"):
                    resolved = csv_file.resolve()
                    if resolved in seen:
                        continue
                    seen.add(resolved)
                    discovered.append((resolved, fallback_root.resolve()))

        return tuple(sorted(discovered, key=lambda item: str(item[0])))

    def _process_file(self, file_path: Path, discovery_root: Path) -> tuple[list[dict[str, Any]], CrimeFileReport]:
        rows = self._read_csv(file_path)
        headers = tuple(rows[0].keys()) if rows else tuple()
        normalized_headers = {_normalize_text(header) for header in headers}

        adapter = self._detect_adapter(file_path=file_path, normalized_headers=normalized_headers)
        if adapter is None:
            raise CrimeSchemaError(f"Unsupported crime CSV schema: {file_path.name}")

        records, adapter_report = adapter.adapt(file_path=file_path, rows=rows, config=self.config)
        report = CrimeFileReport(
            file_path=file_path,
            discovery_root=discovery_root,
            status="processed",
            schema_id=adapter.schema_id,
            rows_loaded=len(rows),
            rows_written=len(records),
            detected_columns=adapter_report.detected_columns,
            mapped_columns=adapter_report.mapped_columns,
            district_samples_before=adapter_report.district_samples_before,
            district_samples_after=adapter_report.district_samples_after,
        )
        self._log_file_mapping(file_path=file_path, adapter=adapter, report=report)
        return records, report

    def _detect_adapter(self, file_path: Path, normalized_headers: set[str]) -> CrimeDatasetAdapter | None:
        for adapter in self.adapters:
            if adapter.can_handle(normalized_headers=normalized_headers, file_name=file_path.name) and adapter.file_name_matches(file_path.name):
                return adapter
        return None

    def _read_csv(self, file_path: Path) -> list[dict[str, str]]:
        if not file_path.exists():
            raise CrimeDataLoadError(f"Crime CSV file does not exist: {file_path}")
        if not file_path.is_file():
            raise CrimeDataLoadError(f"Crime CSV path is not a file: {file_path}")
        try:
            with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                headers = reader.fieldnames or []
                if not headers:
                    raise CrimeSchemaError(f"Crime source file has no header row: {file_path}")
                rows = [dict(row) for row in reader]
        except csv.Error as exc:
            raise CrimeDataLoadError(f"Invalid CSV format: {file_path}") from exc
        if not rows:
            raise CrimeSchemaError(f"Crime source file is empty: {file_path}")
        return rows

    def _write_output(self, rows: list[dict[str, Any]], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = self._union_fieldnames(rows)
        try:
            with output_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    writer.writerow({field: self._stringify_value(row.get(field)) for field in fieldnames})
        except OSError as exc:
            raise CrimeLoaderError(f"Failed to write processed crime dataset to {output_path}") from exc

    def _write_manifest(self, report: CrimeLoaderReport, manifest_path: Path) -> None:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "output_path": str(report.output_path),
            "rows_written": report.rows_written,
            "column_count": report.column_count,
            "unique_district_count": report.unique_district_count,
            "crime_score_min": report.crime_score_min,
            "crime_score_max": report.crime_score_max,
            "processed_files": [str(item.file_path) for item in report.processed_files],
            "skipped_files": [str(item.file_path) for item in report.skipped_files],
        }
        import json

        with manifest_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)

    def _union_fieldnames(self, rows: list[dict[str, Any]]) -> list[str]:
        preferred = [
            "schema_id",
            "schema_name",
            "source_file",
            "source_path",
            "source_row",
            "record_type",
            "district_raw",
            "district",
            "state_name",
            "year",
            "crime_head",
            "crime_score",
        ]
        observed: list[str] = []
        seen: set[str] = set()
        for row in rows:
            for field in row.keys():
                if field not in seen:
                    seen.add(field)
                    observed.append(field)
        ordered = [field for field in preferred if field in seen]
        ordered.extend(sorted(field for field in observed if field not in preferred))
        return ordered

    def _log_file_mapping(self, file_path: Path, adapter: CrimeDatasetAdapter, report: CrimeFileReport) -> None:
        self.logger.info(
            "File processed: %s | schema=%s | rows_loaded=%s | rows_written=%s | district_samples_before=%s | district_samples_after=%s",
            file_path,
            adapter.schema_id,
            report.rows_loaded,
            report.rows_written,
            report.district_samples_before,
            report.district_samples_after,
        )

    @staticmethod
    def _stringify_value(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, float) and math.isnan(value):
            return ""
        return str(value)
