# scripts/package_runtime_assets.py
"""
NavSakhi Phase 51.7 - Immutable Runtime Asset Packager

Creates a deterministic, checksum-verified tar.gz archive of all production runtime
assets and ML inputs required for building and running NavSakhi on Render.

Enforces:
- Strict explicit allowlist (no directory crawling)
- Pre-packaging SHA-256 verification of canonical frozen baselines
- Normalized tar metadata (mtime=0, uid=0, gid=0) for reproducibility
- Inclusion of an embedded verification manifest inside the archive
- Output written outside the Git repository to prevent accidental staging
"""

import argparse
import hashlib
import io
import json
import os
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Authoritative frozen checksums required prior to packaging
CANONICAL_FROZEN_HASHES = {
    "app/ml/Hack/ml/models/best_model.pkl": "bb8e6b04895caf1ca6efcaf37a7994b42690bb8b6237114507f7fa0ba8070dde",
    "app/ml/Hack/ml/models/preprocessing_pipeline.pkl": "c1ad4c28ae5ef5a7c3867535c16d9e6fdf0729a34027a18f463c0a1b79c550cd",
    "app/ml/Hack/ml/datasets/processed/master_feature_table.parquet": "72557fcabb752709e1e8e7500da706179275d3173e30d9ce6da0e41c1a3433e5",
    "app/ml/Hack/ml/datasets/processed/road_segments.parquet": "ffee5ce98efda020cbcf7c6e280bd46b73e1d035fa29741a49941fdd2aaa8d8b",
}

# Strict explicit allowlist of all 16 runtime assets
APPROVED_RUNTIME_ASSET_PATHS = [
    "app/ml/Hack/ml/models/best_model.pkl",
    "app/ml/Hack/ml/models/preprocessing_pipeline.pkl",
    "app/ml/Hack/ml/models/model_manifest.json",
    "app/ml/Hack/ml/models/feature_metadata.json",
    "app/ml/Hack/ml/datasets/processed/master_feature_table.parquet",
    "app/ml/Hack/ml/datasets/processed/road_segments.parquet",
    "poi_data/manifest.json",
    "poi_data/processed/chennai_pois.json",
    "transit_data/manifest.json",
    "transit_data/processed/bus_network.json",
    "transit_data/processed/metro_network.json",
    "transit_data/processed/suburban_network.json",
    "transit_data/processed/interchanges.json",
    "transit_data/processed/station_normalization_diagnostics.json",
    "transit_data/downloads/cmrl-gtfs.zip",
    "transit_data/downloads/srr-gtfs.zip",
]

ARCHIVE_VERSION = "2.0.0"
DEFAULT_ARCHIVE_NAME = f"navsakhi-runtime-assets-v{ARCHIVE_VERSION}.tar.gz"


def compute_sha256(file_path: Path) -> str:
    """Computes SHA-256 digest of a file in 1MB chunks."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest().lower()


def package_assets(output_dir: Path) -> Tuple[Path, str, Dict]:
    """
    Validates, manifests, and packages approved runtime assets into a deterministic tar.gz.
    Returns (archive_path, archive_sha256, manifest_dict).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / DEFAULT_ARCHIVE_NAME

    print(f"[*] Validating {len(APPROVED_RUNTIME_ASSET_PATHS)} runtime assets from allowlist...")

    manifest_entries: List[Dict] = []
    total_uncompressed_bytes = 0

    for rel_path_str in APPROVED_RUNTIME_ASSET_PATHS:
        full_path = PROJECT_ROOT / Path(rel_path_str)
        if not full_path.exists():
            raise FileNotFoundError(f"Missing required runtime asset: {rel_path_str} at {full_path}")

        actual_sha256 = compute_sha256(full_path)
        file_size = full_path.stat().st_size
        total_uncompressed_bytes += file_size

        # Check against canonical frozen baseline if applicable
        if rel_path_str in CANONICAL_FROZEN_HASHES:
            expected = CANONICAL_FROZEN_HASHES[rel_path_str]
            if actual_sha256 != expected:
                raise ValueError(
                    f"Integrity check failed for frozen artifact '{rel_path_str}'!\n"
                    f"Expected: {expected}\nActual:   {actual_sha256}"
                )

        manifest_entries.append({
            "path": rel_path_str,
            "size_bytes": file_size,
            "sha256": actual_sha256
        })
        print(f"    [OK] {rel_path_str} ({file_size:,} bytes, sha256={actual_sha256[:12]}...)")

    embedded_manifest = {
        "version": ARCHIVE_VERSION,
        "archive_name": DEFAULT_ARCHIVE_NAME,
        "file_count": len(manifest_entries),
        "total_uncompressed_bytes": total_uncompressed_bytes,
        "assets": manifest_entries,
    }

    manifest_bytes = json.dumps(embedded_manifest, indent=2).encode("utf-8")

    print(f"[*] Creating deterministic tar.gz at: {archive_path}")

    # Write tar.gz with normalized tarinfo entries for reproducible archive generation
    with tarfile.open(archive_path, "w:gz", format=tarfile.PAX_FORMAT) as tar:
        # 1. Add embedded archive manifest at root of tar
        manifest_info = tarfile.TarInfo(name="manifest.json")
        manifest_info.size = len(manifest_bytes)
        manifest_info.mtime = 0
        manifest_info.uid = 0
        manifest_info.gid = 0
        manifest_info.uname = ""
        manifest_info.gname = ""
        manifest_info.mode = 0o644
        tar.addfile(manifest_info, io.BytesIO(manifest_bytes))

        # 2. Add each approved runtime asset preserving relative path
        for entry in manifest_entries:
            rel_str = entry["path"]
            source_file = PROJECT_ROOT / Path(rel_str)
            tar_name = rel_str.replace("\\", "/")

            ti = tarfile.TarInfo(name=tar_name)
            ti.size = entry["size_bytes"]
            ti.mtime = 0
            ti.uid = 0
            ti.gid = 0
            ti.uname = ""
            ti.gname = ""
            ti.mode = 0o644

            with open(source_file, "rb") as f:
                tar.addfile(ti, f)

    archive_sha256 = compute_sha256(archive_path)
    archive_size = archive_path.stat().st_size

    print(f"[+] Archive created successfully:")
    print(f"    Path:           {archive_path}")
    print(f"    Archive Size:   {archive_size:,} bytes ({archive_size / (1024*1024):.2f} MB)")
    print(f"    Uncompressed:   {total_uncompressed_bytes:,} bytes ({total_uncompressed_bytes / (1024*1024):.2f} MB)")
    print(f"    Archive SHA256: {archive_sha256}")

    # Save manifest companion next to archive in output dir
    manifest_out = output_dir / f"{DEFAULT_ARCHIVE_NAME}.manifest.json"
    with open(manifest_out, "w", encoding="utf-8") as f:
        embedded_manifest["archive_sha256"] = archive_sha256
        embedded_manifest["archive_size_bytes"] = archive_size
        json.dump(embedded_manifest, f, indent=2)

    return archive_path, archive_sha256, embedded_manifest


def main():
    parser = argparse.ArgumentParser(description="Package NavSakhi runtime assets into versioned tar.gz archive.")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Target output directory outside the repository (defaults to OS temporary directory)."
    )
    args = parser.parse_args()

    if args.output_dir:
        out_dir = Path(args.output_dir).resolve()
    else:
        out_dir = Path(tempfile.gettempdir()) / "navsakhi_runtime_assets"

    # Safety check: Prevent writing directly inside git workspace
    try:
        rel = out_dir.relative_to(PROJECT_ROOT)
        print(f"[ERROR] Output directory '{out_dir}' is inside the project repository! Aborting.", file=sys.stderr)
        sys.exit(1)
    except ValueError:
        pass  # Good: out_dir is outside PROJECT_ROOT

    package_assets(out_dir)


if __name__ == "__main__":
    main()
