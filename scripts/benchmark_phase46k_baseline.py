import sys
from pathlib import Path

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

"""
NavSakhi Phase 46K - Reproducible Local Baseline Benchmark.
Benchmarks a long Chennai route (32 km from VIT Chennai area to Anna Nagar)
measuring per-stage latency, call counts, index builds, and process RSS.
"""

import time
import os
import numpy as np

def get_native_rss_mb() -> float:
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
        if GetProcessMemoryInfo(GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            return counters.WorkingSetSize / (1024 * 1024)
    else:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    return 0.0

print(f"Initial Process RSS: {get_native_rss_mb():.2f} MB")

# Stage 1: Cold start initialization
t0 = time.perf_counter()
rss_pre_init = get_native_rss_mb()
from app.ml.predictor import get_ml_safety_predictor
from app.intelligence.journey.spatial_matcher import SpatialMatchingService
from app.services.ml_route_scoring_service import MLRouteScoringService
from app.models.journey import CandidateRoute

predictor = get_ml_safety_predictor()
matcher = SpatialMatchingService()
scorer = MLRouteScoringService(spatial_matcher=matcher, predictor=predictor)
t_cold_init = time.perf_counter() - t0
rss_post_init = get_native_rss_mb()
print(f"Cold Initialization: {t_cold_init:.3f} s (RSS: {rss_post_init:.2f} MB, Delta: +{rss_post_init - rss_pre_init:.2f} MB)")

# Create representative 32 km route fixtures across Chennai (VIT Chennai -> Anna Nagar)
lats = np.linspace(12.8401, 13.08106, 120)
lons = np.linspace(80.1528, 80.19602, 120)
coords_main = [[float(lo), float(la)] for lo, la in zip(lons, lats)]

# Candidate 1: Personal Vehicle (~32 km driving)
cand1 = CandidateRoute(
    route_identifier="driving_0",
    distance=32000.0,
    duration=3600.0,
    recommendation_status="AVAILABLE",
    route_metadata={"travel_mode": "Personal Vehicle", "geometry": {"type": "LineString", "coordinates": coords_main}}
)

# Candidate 2: Alternative Road Corridor (offset ~32 km driving)
coords_alt = [[float(lo) + 0.003, float(la) - 0.002] for lo, la in zip(lons, lats)]
cand2 = CandidateRoute(
    route_identifier="driving_1",
    distance=33500.0,
    duration=3900.0,
    recommendation_status="AVAILABLE",
    route_metadata={"travel_mode": "Cab Direct", "geometry": {"type": "LineString", "coordinates": coords_alt}}
)

# Candidate 3: Multimodal Route (Walk -> Suburban Rail -> Bus -> Walk)
n_pts = len(coords_main)
walk_access_coords = coords_main[:20] # ~5 km
train_coords = coords_main[20:80]      # ~16 km
bus_coords = coords_main[80:105]       # ~7 km
walk_egress_coords = coords_main[105:] # ~4 km

cand3 = CandidateRoute(
    route_identifier="multimodal_0",
    distance=32000.0,
    duration=4200.0,
    recommendation_status="AVAILABLE",
    route_metadata={
        "travel_mode": "Multimodal",
        "dynamic_segments": [
            {"mode": "walk", "geometry": {"type": "LineString", "coordinates": walk_access_coords}, "distance_m": 5000.0, "duration_s": 900.0},
            {"mode": "suburban", "geometry": {"type": "LineString", "coordinates": train_coords}, "distance_m": 16000.0, "duration_s": 1500.0},
            {"mode": "bus", "geometry": {"type": "LineString", "coordinates": bus_coords}, "distance_m": 7000.0, "duration_s": 1200.0},
            {"mode": "walk", "geometry": {"type": "LineString", "coordinates": walk_egress_coords}, "distance_m": 4000.0, "duration_s": 600.0},
        ]
    }
)

candidates = [cand1, cand2, cand3]
print(f"Benchmark Candidates: {len(candidates)} routes (Driving, Alternative Cab, Multimodal)")

# Stage 2: Scoring candidates
t0 = time.perf_counter()
rss_pre_score = get_native_rss_mb()
results = scorer.score_candidate_routes(candidates)
t_score = time.perf_counter() - t0
rss_post_score = get_native_rss_mb()

print(f"Scoring Stage Elapsed: {t_score:.3f} s (RSS: {rss_post_score:.2f} MB, Delta: +{rss_post_score - rss_pre_score:.2f} MB)")
print(f"Segments in matcher index: {len(matcher._segment_records)}")
for r in results:
    print(f"  {r.route_identifier}: score={r.safety_score}, status={r.score_status}, cov={r.scoreable_coverage_ratio:.2f}")

print(f"Total Warm Request Pipeline: {t_score:.3f} s")
