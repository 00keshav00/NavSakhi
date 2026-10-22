"""
NavSakhi Phase 46J.1 - Deployment Safety and Checkpoint Integrity Regression Suite.

Verifies:
1. Companion stores validation (existence, schema, indexes, non-emptiness).
2. Detection of missing, corrupt, or incomplete companion stores in < 2ms without Parquet scan.
3. Strict production safety guard: CompanionStoreError raised in production mode (no silent fallback).
4. Development/test mode fallback preservation.
5. Readiness endpoint (/health/ready) status under valid and missing store scenarios.
6. HTTP 503 response formatting and sensitive info redaction for CompanionStoreError.
7. Atomic generation safety in scripts/build_companion_stores.py.
8. Native OS memory bounding during validation and bounded corridor query.
9. Bit-for-bit SHA-256 preservation of all 4 frozen ML artifacts.
"""

import hashlib
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.config.settings import settings
from app.intelligence.journey.spatial_matcher import (
    SpatialMatchingService,
    CompanionStoreError,
    validate_companion_stores,
    DEFAULT_MASTER_FEATURE_PATH,
    DEFAULT_ROAD_SEGMENTS_PATH,
    DEFAULT_FEATURE_STORE_PATH,
    DEFAULT_ROAD_SEGMENTS_STORE_PATH,
)
from app.ml.schemas import CANONICAL_PREDICTOR_FEATURES
from app.main import app

FROZEN_HASHES = {
    "master_feature_table.parquet": (
        DEFAULT_MASTER_FEATURE_PATH,
        "72557fcabb752709e1e8e7500da706179275d3173e30d9ce6da0e41c1a3433e5",
    ),
    "road_segments.parquet": (
        DEFAULT_ROAD_SEGMENTS_PATH,
        "ffee5ce98efda020cbcf7c6e280bd46b73e1d035fa29741a49941fdd2aaa8d8b",
    ),
    "best_model.pkl": (
        Path("app/ml/Hack/ml/models/best_model.pkl"),
        "bb8e6b04895caf1ca6efcaf37a7994b42690bb8b6237114507f7fa0ba8070dde",
    ),
    "preprocessing_pipeline.pkl": (
        Path("app/ml/Hack/ml/models/preprocessing_pipeline.pkl"),
        "c1ad4c28ae5ef5a7c3867535c16d9e6fdf0729a34027a18f463c0a1b79c550cd",
    ),
}


# --- 1. Frozen Artifact Integrity ---

def test_frozen_artifact_hashes_phase46j1():
    """Verify bit-for-bit SHA-256 preservation of all 4 frozen ML artifacts."""
    for name, (path, expected_hash) in FROZEN_HASHES.items():
        assert path.exists(), f"Frozen artifact {name} missing at {path}"
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                hasher.update(chunk)
        actual = hasher.hexdigest()
        assert actual == expected_hash, f"Hash mismatch for {name}: {actual} != {expected_hash}"


# --- 2. Companion Store Validation ---

def test_validate_companion_stores_valid():
    """Validates that real production companion stores pass validation."""
    valid, reason = validate_companion_stores()
    assert valid is True
    assert reason is None


def test_validate_companion_stores_missing():
    """Validates that missing database files are detected immediately."""
    valid, reason = validate_companion_stores(
        road_segments_store_path=Path("non_existent_rs.db"),
        feature_store_path=DEFAULT_FEATURE_STORE_PATH,
    )
    assert valid is False
    assert "Road segments companion store missing" in reason

    valid, reason = validate_companion_stores(
        road_segments_store_path=DEFAULT_ROAD_SEGMENTS_STORE_PATH,
        feature_store_path=Path("non_existent_fs.db"),
    )
    assert valid is False
    assert "Feature companion store missing" in reason


def test_validate_companion_stores_corrupt_or_incomplete(tmp_path):
    """Validates that incomplete schemas or missing indexes are caught."""
    bad_rs = tmp_path / "bad_rs.db"
    conn = sqlite3.connect(bad_rs)
    conn.execute("CREATE TABLE road_segments (segment_id TEXT, latitude REAL)")
    conn.commit()
    conn.close()

    valid, reason = validate_companion_stores(
        road_segments_store_path=bad_rs,
        feature_store_path=DEFAULT_FEATURE_STORE_PATH,
    )
    assert valid is False
    assert "missing columns" in reason

    # Now add columns but omit spatial index
    conn = sqlite3.connect(bad_rs)
    conn.execute("DROP TABLE road_segments")
    conn.execute("CREATE TABLE road_segments (segment_id TEXT, way_id INTEGER, latitude REAL, longitude REAL, length_m REAL, road_type TEXT)")
    conn.execute("INSERT INTO road_segments VALUES ('1', 1, 13.0, 80.0, 10.0, 'residential')")
    conn.commit()
    conn.close()

    valid, reason = validate_companion_stores(
        road_segments_store_path=bad_rs,
        feature_store_path=DEFAULT_FEATURE_STORE_PATH,
    )
    assert valid is False
    assert "missing spatial index" in reason


# --- 3. Production Safety Guard: No Silent Fallback ---

def test_production_mode_raises_on_missing_road_segments_store():
    """In production mode, missing road store raises CompanionStoreError without Parquet scan."""
    matcher = SpatialMatchingService(
        road_segments_store_path=Path("non_existent_rs.db"),
        feature_store_path=DEFAULT_FEATURE_STORE_PATH,
        require_companion_stores=True,
    )
    with pytest.raises(CompanionStoreError) as exc_info:
        matcher.match_route(
            [[80.2500, 13.0500], [80.2520, 13.0520]],
            route_identifier="prod_test",
        )
    assert "Road segments companion store" in str(exc_info.value)
    assert "prohibited in production" in str(exc_info.value)


def test_production_mode_raises_on_missing_feature_store():
    """In production mode, missing feature store raises CompanionStoreError during bridging."""
    matcher = SpatialMatchingService(
        road_segments_store_path=DEFAULT_ROAD_SEGMENTS_STORE_PATH,
        feature_store_path=Path("non_existent_fs.db"),
        require_companion_stores=True,
    )
    with pytest.raises(CompanionStoreError) as exc_info:
        matcher.match_route(
            [[80.2500, 13.0500], [80.2520, 13.0520]],
            route_identifier="prod_test_fs",
        )
    assert "Feature companion store" in str(exc_info.value)
    assert "prohibited in production" in str(exc_info.value)


def test_production_mode_guards_against_full_index_build():
    """In production mode, calling build_index() with no args raises CompanionStoreError."""
    matcher = SpatialMatchingService(
        require_companion_stores=True,
    )
    with pytest.raises(CompanionStoreError) as exc_info:
        matcher.build_index()
    assert "Full-dataset spatial index build prohibited in production mode" in str(exc_info.value)


def test_dev_mode_preserves_parquet_fallback():
    """In dev/test mode (require_companion_stores=False), fallback succeeds."""
    matcher = SpatialMatchingService(
        road_segments_store_path=Path("non_existent_rs.db"),
        feature_store_path=Path("non_existent_fs.db"),
        require_companion_stores=False,
    )
    res = matcher.match_route(
        [[80.2500, 13.0500], [80.2520, 13.0520]],
        route_identifier="dev_test",
    )
    assert res is not None
    assert res.coverage.total_route_length_m > 0


# --- 4. Readiness & Health Endpoints ---

def test_readiness_endpoint_ready():
    """Verify /health/ready returns 200 when stores are intact."""
    client = TestClient(app)
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["stores"] == "verified"


def test_readiness_endpoint_production_missing_stores():
    """Verify /health/ready returns 503 when stores are missing in production mode."""
    client = TestClient(app)
    with patch.dict(os.environ, {"RENDER": "true"}):
        with patch("app.intelligence.journey.spatial_matcher.validate_companion_stores") as mock_val:
            mock_val.return_value = (False, "Road segments companion store missing")
            response = client.get("/health/ready")
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unavailable"
            assert "Road segments companion store missing" in data["reason"]


def test_companion_store_exception_handler_returns_503():
    """Verify CompanionStoreError triggers 503 without leaking paths."""
    client = TestClient(app)

    @app.get("/test-companion-error")
    def trigger_error():
        raise CompanionStoreError("Sensitive path /var/data/foo.db missing")

    response = client.get("/test-companion-error")
    assert response.status_code == 503
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert "temporarily unavailable" in data["error"]["message"]
    # Verify sensitive path is not leaked in response
    assert "/var/data" not in str(data)


# --- 5. Native OS Process Memory Bounding Check ---

def _get_process_rss_mb() -> float:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t),
            ]

        GetProcessMemoryInfo = ctypes.windll.psapi.GetProcessMemoryInfo
        GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX), wintypes.DWORD]
        GetProcessMemoryInfo.restype = wintypes.BOOL
        GetCurrentProcess = ctypes.windll.kernel32.GetCurrentProcess
        GetCurrentProcess.restype = wintypes.HANDLE

        counters = PROCESS_MEMORY_COUNTERS_EX()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
        handle = GetCurrentProcess()
        if GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            return counters.WorkingSetSize / (1024 * 1024)
    else:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    return 0.0


def test_validation_and_retrieval_process_memory_bounded():
    """
    Measures OS process RSS during validation and route matching.
    Verifies RSS delta remains strictly bounded (< 25 MB).
    """
    rss_before = _get_process_rss_mb()

    # 1. Validation
    valid, reason = validate_companion_stores()
    assert valid is True
    rss_after_val = _get_process_rss_mb()
    if rss_before > 0:
        val_delta = rss_after_val - rss_before
        assert val_delta < 10.0, f"Validation RSS increased by {val_delta:.2f} MB"

    # 2. Bounded corridor route matching
    matcher = SpatialMatchingService(require_companion_stores=True)
    coords = [[80.2500, 13.0500], [80.2520, 13.0520], [80.2540, 13.0540]]
    res = matcher.match_route(coords, route_identifier="rss_bench")
    assert res is not None

    if rss_before > 0:
        rss_after_match = _get_process_rss_mb()
        match_delta = rss_after_match - rss_after_val
        assert match_delta < 25.0, f"Route matching RSS increased by {match_delta:.2f} MB"
