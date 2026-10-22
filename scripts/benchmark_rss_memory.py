"""
NavSakhi Phase 46I - Native Process RSS Memory Measurement Harness.

Measures true OS-level Working Set / RSS memory before, during,
and after spatial corridor matching and feature bridging under:
A) Optimized SQLite Companion Stores (Phase 46I)
B) Legacy Full Parquet Dataset Scanning
"""

import ctypes
from ctypes import wintypes
import gc
import os
import sys
import time
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if sys.platform == "win32":
    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
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
        ]

    GetProcessMemoryInfo = ctypes.windll.psapi.GetProcessMemoryInfo
    GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wintypes.DWORD]
    GetProcessMemoryInfo.restype = wintypes.BOOL

    GetCurrentProcess = ctypes.windll.kernel32.GetCurrentProcess
    GetCurrentProcess.restype = wintypes.HANDLE

    def get_memory_stats():
        pmc = PROCESS_MEMORY_COUNTERS()
        pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        GetProcessMemoryInfo(GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
        return {
            "rss_mb": pmc.WorkingSetSize / (1024 * 1024),
            "peak_rss_mb": pmc.PeakWorkingSetSize / (1024 * 1024),
        }
else:
    import resource
    def get_memory_stats():
        ru = resource.getrusage(resource.RUSAGE_SELF)
        return {
            "rss_mb": ru.ru_maxrss / 1024,
            "peak_rss_mb": ru.ru_maxrss / 1024,
        }

from app.models.journey import CandidateRoute
from app.services.ml_route_scoring_service import MLRouteScoringService
from app.ml.predictor import get_ml_safety_predictor
from app.intelligence.journey.spatial_matcher import (
    SpatialMatchingService,
    DEFAULT_MASTER_FEATURE_PATH,
    DEFAULT_ROAD_SEGMENTS_PATH,
    DEFAULT_FEATURE_STORE_PATH,
    DEFAULT_ROAD_SEGMENTS_STORE_PATH,
)


def benchmark_run(use_companion_stores: bool, route_coords: list, name: str):
    gc.collect()
    time.sleep(0.5)
    mem_start = get_memory_stats()

    if use_companion_stores:
        matcher = SpatialMatchingService(
            road_segments_store_path=DEFAULT_ROAD_SEGMENTS_STORE_PATH,
            feature_store_path=DEFAULT_FEATURE_STORE_PATH,
        )
    else:
        # Force fallback to Parquet scan by passing dummy non-existent paths
        matcher = SpatialMatchingService(
            road_segments_store_path=Path("non_existent_rs.db"),
            feature_store_path=Path("non_existent_fs.db"),
        )

    predictor = get_ml_safety_predictor()
    scoring_service = MLRouteScoringService(predictor=predictor, spatial_matcher=matcher)

    candidate = CandidateRoute(
        route_identifier=f"route_bench_{name}",
        distance=1200.0,
        duration=180.0,
        recommendation_status="AVAILABLE",
        route_metadata={
            "travel_mode": "Road",
            "geometry": route_coords,
        },
    )

    t0 = time.perf_counter()
    mem_before_score = get_memory_stats()

    result = scoring_service.score_candidate_routes([candidate])

    mem_after_score = get_memory_stats()
    elapsed = (time.perf_counter() - t0) * 1000

    scored = result[0]
    matched_count = len(matcher._segment_records)
    cached_feats = len(matcher._feature_cache)

    print(f"[{name}]")
    print(f"  Stores Used: {'SQLite Companion Stores' if use_companion_stores else 'Legacy Parquet Full-Scan'}")
    print(f"  Start RSS:        {mem_start['rss_mb']:.2f} MB (Peak: {mem_start['peak_rss_mb']:.2f} MB)")
    print(f"  Pre-Score RSS:    {mem_before_score['rss_mb']:.2f} MB (Peak: {mem_before_score['peak_rss_mb']:.2f} MB)")
    print(f"  Post-Score RSS:   {mem_after_score['rss_mb']:.2f} MB (Peak: {mem_after_score['peak_rss_mb']:.2f} MB)")
    print(f"  RSS Delta:        {mem_after_score['rss_mb'] - mem_start['rss_mb']:+.2f} MB")
    print(f"  Elapsed Time:     {elapsed:.1f} ms")
    print(f"  Segments Matched: {matched_count}")
    print(f"  Features Cached:  {cached_feats}")
    print(f"  Score Status:     {scored.score_status}")
    print(f"  Safety Score:     {scored.safety_score}")
    print()

    return {
        "name": name,
        "mode": "companion" if use_companion_stores else "parquet",
        "rss_start": mem_start['rss_mb'],
        "rss_peak": mem_after_score['peak_rss_mb'],
        "rss_post": mem_after_score['rss_mb'],
        "rss_delta": mem_after_score['rss_mb'] - mem_start['rss_mb'],
        "elapsed_ms": elapsed,
        "segments": matched_count,
        "features": cached_feats,
        "score": scored.safety_score,
    }


def main():
    print("=" * 65)
    print("NAVSAKHI PHASE 46I - NATIVE PROCESS RSS MEMORY BENCHMARK")
    print(f"PID: {os.getpid()} | Python {sys.version.split()[0]} | Platform: {sys.platform}")
    print("=" * 65)
    print(f"Feature Store DB size: {DEFAULT_FEATURE_STORE_PATH.stat().st_size / (1024*1024):.2f} MB")
    print(f"Road Store DB size:    {DEFAULT_ROAD_SEGMENTS_STORE_PATH.stat().st_size / (1024*1024):.2f} MB")
    print()

    # Route coords in Chennai
    coords = [
        [80.2500, 13.0500],
        [80.2520, 13.0530],
        [80.2550, 13.0560],
        [80.2580, 13.0590],
    ]

    # Benchmark 1: Companion Stores
    res_companion = benchmark_run(True, coords, "Phase 46I SQLite Companion Stores")

    # Benchmark 2: Legacy Parquet Scanning
    res_parquet = benchmark_run(False, coords, "Legacy Parquet Dataset Scan")

    print("=" * 65)
    print("BENCHMARK COMPARISON SUMMARY:")
    print(f"  SQLite Companion Stores: Delta = {res_companion['rss_delta']:+.2f} MB, Time = {res_companion['elapsed_ms']:.1f} ms")
    print(f"  Legacy Parquet Scan:     Delta = {res_parquet['rss_delta']:+.2f} MB, Time = {res_parquet['elapsed_ms']:.1f} ms")
    saved_mb = res_parquet['rss_peak'] - res_companion['rss_peak']
    speedup = res_parquet['elapsed_ms'] / max(res_companion['elapsed_ms'], 0.001)
    print(f"  Memory Peak Reduction:   {saved_mb:.2f} MB lower peak RSS")
    print(f"  Execution Speedup:       {speedup:.1f}x faster")
    print("=" * 65)


if __name__ == "__main__":
    main()
