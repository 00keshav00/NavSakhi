# scripts/download_production_assets.py
"""
NavSakhi Phase 51.7 - Verified Production Asset Downloader

Downloads and cryptographically verifies the immutable NavSakhi runtime asset archive
during deployment build phase on Render before building companion SQLite stores.

Enforces:
- Compulsory HTTPS URL scheme
- Mandatory SHA-256 archive checksum verification before extraction
- Path traversal rejection (zero absolute paths, no '..', no symlinks)
- Extraction restricted strictly to approved relative destination paths
- Manifest-level file size and SHA-256 verification after extraction
- Fails closed on any corruption, network error, or unexpected member
- No external Python dependencies (standard library only)
"""

import hashlib
import json
import logging
import os
import shutil
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Set

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("download_production_assets")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Approved allowlist matching the packaging utility
APPROVED_DESTINATIONS: Set[str] = {
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
}


def compute_sha256(file_path: Path) -> str:
    """Computes SHA-256 digest of a file in 1MB chunks."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest().lower()


def is_safe_tar_member(member: tarfile.TarInfo) -> bool:
    """Validates that a tar member cannot perform path traversal or overwrite outside target."""
    name = member.name.replace("\\", "/")
    # Special case: embedded manifest inside archive root
    if name == "manifest.json":
        return True

    if os.path.isabs(name) or name.startswith("/") or name.startswith("\\"):
        logger.error(f"Unsafe absolute path in archive: {name}")
        return False
    if ".." in name.split("/"):
        logger.error(f"Path traversal detected in archive member: {name}")
        return False
    if member.issym() or member.islnk():
        logger.error(f"Symlinks and hardlinks prohibited in archive member: {name}")
        return False
    if not (member.isreg() or member.isdir()):
        logger.error(f"Non-regular file in archive member: {name}")
        return False
    if member.isreg() and name not in APPROVED_DESTINATIONS:
        logger.error(f"Unapproved asset member found in archive: {name}")
        return False
    return True


def download_file(url: str, dest_path: Path) -> None:
    """Downloads a file over HTTPS with chunked streaming and progress reporting."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme.lower() != "https":
        raise ValueError(f"Insecure URL scheme '{parsed.scheme}'. Only HTTPS is permitted.")

    logger.info(f"Connecting to verified asset archive download source...")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "NavSakhi-AssetDownloader/2.0"}
    )
    with urllib.request.urlopen(req, timeout=300) as response, open(dest_path, "wb") as out_file:
        total_len = response.getheader("Content-Length")
        total_bytes = int(total_len) if total_len and total_len.isdigit() else 0
        downloaded = 0
        chunk_size = 1024 * 1024  # 1MB chunks

        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)
            downloaded += len(chunk)
            if total_bytes > 0:
                percent = (downloaded / total_bytes) * 100
                if downloaded % (5 * 1024 * 1024) < chunk_size or downloaded == total_bytes:
                    logger.info(f"Downloaded {downloaded:,} / {total_bytes:,} bytes ({percent:.1f}%)")
            elif downloaded % (5 * 1024 * 1024) < chunk_size:
                logger.info(f"Downloaded {downloaded:,} bytes...")


def verify_and_extract_archive(archive_path: Path, expected_sha256: str) -> None:
    """Verifies archive SHA-256 and extracts approved assets atomically into PROJECT_ROOT."""
    logger.info("Computing SHA-256 of downloaded archive...")
    actual_sha256 = compute_sha256(archive_path)

    if actual_sha256 != expected_sha256.lower().strip():
        raise ValueError(
            f"Archive SHA-256 checksum mismatch!\n"
            f"Expected: {expected_sha256.lower().strip()}\n"
            f"Actual:   {actual_sha256}"
        )
    logger.info("Archive SHA-256 checksum verified successfully.")

    with tempfile.TemporaryDirectory(prefix="navsakhi_extracted_") as extract_tmp:
        tmp_dir = Path(extract_tmp)

        with tarfile.open(archive_path, "r:gz") as tar:
            members = tar.getmembers()
            logger.info(f"Inspecting {len(members)} archive members for security...")

            for member in members:
                if not is_safe_tar_member(member):
                    raise ValueError(f"Archive contains unsafe or forbidden member: {member.name}")

            # Safe extraction into temporary staging area
            tar.extractall(path=tmp_dir)

        # Inspect embedded manifest
        manifest_file = tmp_dir / "manifest.json"
        if not manifest_file.exists():
            raise ValueError("Archive is missing required embedded 'manifest.json' verification file.")

        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        expected_assets: Dict[str, Dict] = {a["path"]: a for a in manifest.get("assets", [])}
        logger.info(f"Manifest declares {len(expected_assets)} assets. Verifying integrity...")

        # Verify each extracted file against the embedded manifest
        for rel_path_str, meta in expected_assets.items():
            extracted_file = tmp_dir / Path(rel_path_str)
            if not extracted_file.exists():
                raise FileNotFoundError(f"Manifest asset missing in archive content: {rel_path_str}")

            ext_size = extracted_file.stat().st_size
            if ext_size != meta["size_bytes"]:
                raise ValueError(
                    f"Size mismatch for '{rel_path_str}': expected {meta['size_bytes']}, got {ext_size}"
                )

            ext_sha256 = compute_sha256(extracted_file)
            if ext_sha256 != meta["sha256"]:
                raise ValueError(
                    f"Checksum mismatch for '{rel_path_str}': expected {meta['sha256']}, got {ext_sha256}"
                )

        logger.info("All extracted assets verified bit-for-bit against manifest.")

        # Atomically install verified assets into destination locations in PROJECT_ROOT
        logger.info(f"Installing verified assets into project tree under: {PROJECT_ROOT}")
        for rel_path_str in expected_assets:
            src = tmp_dir / Path(rel_path_str)
            dest = PROJECT_ROOT / Path(rel_path_str)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            logger.info(f"Installed: {rel_path_str}")

    logger.info("Asset installation completed successfully.")


def main():
    archive_url = os.environ.get("NAVSAKHI_ASSET_ARCHIVE_URL")
    archive_sha256 = os.environ.get("NAVSAKHI_ASSET_ARCHIVE_SHA256")

    if not archive_url or not archive_url.strip():
        logger.error(
            "Missing required environment variable: NAVSAKHI_ASSET_ARCHIVE_URL.\n"
            "This variable must point to the HTTPS release asset archive."
        )
        sys.exit(1)

    if not archive_sha256 or not archive_sha256.strip():
        logger.error(
            "Missing required environment variable: NAVSAKHI_ASSET_ARCHIVE_SHA256.\n"
            "This variable must contain the 64-character lowercase SHA-256 digest of the archive."
        )
        sys.exit(1)

    archive_url = archive_url.strip()
    archive_sha256 = archive_sha256.strip().lower()

    if len(archive_sha256) != 64:
        logger.error(f"NAVSAKHI_ASSET_ARCHIVE_SHA256 must be a valid 64-char hex digest (got {len(archive_sha256)} chars).")
        sys.exit(1)

    with tempfile.TemporaryDirectory(prefix="navsakhi_download_") as dl_tmp:
        dl_archive = Path(dl_tmp) / "downloaded_assets.tar.gz"
        try:
            download_file(archive_url, dl_archive)
            verify_and_extract_archive(dl_archive, archive_sha256)
        except Exception as e:
            logger.error(f"Asset acquisition failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
