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
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

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


class DisallowRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Prevents automatic redirect following so headers like Authorization can be sanitized."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


# Legitimate GitHub release asset storage host patterns
ALLOWED_REDIRECT_HOST_REGEXES = [
    re.compile(r"^objects\.githubusercontent\.com$", re.IGNORECASE),
    re.compile(r"^release-assets\.githubusercontent\.com$", re.IGNORECASE),
    re.compile(r"^github-production-release-asset-[a-z0-9]{4,16}\.s3(\.[a-z0-9-]+)?\.amazonaws\.com$", re.IGNORECASE),
    re.compile(r"^api\.github\.com$", re.IGNORECASE),
]


def validate_redirect_url(url: str) -> None:
    """
    Validates that a redirect destination URL meets strict security policies:
    - Scheme must be HTTPS
    - Userinfo (username/password) is prohibited
    - Non-standard ports are prohibited (only None or 443 allowed)
    - Hostname must be present and match approved GitHub release storage hosts
    """
    if not url or not isinstance(url, str):
        raise ValueError("Redirect URL must be a non-empty string.")

    parsed = urllib.parse.urlsplit(url)

    if parsed.scheme.lower() != "https":
        raise ValueError(
            f"Insecure redirect URL scheme '{parsed.scheme}'. Only HTTPS is permitted."
        )

    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Redirect URL contains embedded user credentials, which is prohibited.")

    if parsed.port is not None and parsed.port != 443:
        raise ValueError(f"Non-standard port '{parsed.port}' in redirect URL is prohibited.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Redirect URL missing a valid hostname.")

    if not any(r.match(hostname) for r in ALLOWED_REDIRECT_HOST_REGEXES):
        raise ValueError(
            f"Redirect destination host '{hostname}' is not in the approved GitHub storage host allowlist."
        )


def parse_and_validate_github_release_url(
    url: str,
    expected_repo: str = "00keshav00/NavSakhi"
) -> Tuple[str, str, str, str]:
    """
    Parses and strictly validates a GitHub release asset download URL.
    Expected format:
      https://github.com/{owner}/{repo}/releases/download/{tag}/{filename}
    Returns:
      (owner, repo, tag, filename)
    """
    if not url or not isinstance(url, str):
        raise ValueError("Archive URL must be a non-empty string.")

    parsed = urllib.parse.urlsplit(url)

    if parsed.scheme.lower() != "https":
        raise ValueError(f"Insecure URL scheme '{parsed.scheme}'. Only HTTPS is permitted.")

    if parsed.netloc.lower() != "github.com":
        raise ValueError(
            f"Invalid hostname '{parsed.netloc}'. Authenticated release downloads require 'github.com'."
        )

    if parsed.query:
        raise ValueError("URL query strings are not permitted in release download URL.")

    if parsed.fragment:
        raise ValueError("URL fragments are not permitted in release download URL.")

    path_clean = parsed.path.strip("/")
    parts = path_clean.split("/")

    if ".." in parts or any(".." in p for p in parts):
        raise ValueError("Path traversal sequences are prohibited in release URL.")

    if len(parts) != 6 or parts[2] != "releases" or parts[3] != "download":
        raise ValueError(
            f"Malformed GitHub release download path '{parsed.path}'. "
            "Expected format: '/{owner}/{repo}/releases/download/{tag}/{filename}'"
        )

    owner, repo, _, _, tag, filename = parts

    if any(p in (".", "..") for p in (owner, repo, tag, filename)):
        raise ValueError("Path traversal sequences are prohibited in release URL.")

    expected_owner, expected_repo_name = expected_repo.split("/")
    if owner.lower() != expected_owner.lower() or repo.lower() != expected_repo_name.lower():
        raise ValueError(
            f"Repository mismatch in release URL: expected '{expected_repo}', got '{owner}/{repo}'."
        )

    if not filename.strip():
        raise ValueError("Asset filename cannot be empty in release URL.")

    if not tag.strip():
        raise ValueError("Release tag cannot be empty in release URL.")

    return owner, repo, tag, filename


def _stream_response_to_file(response, dest_path: Path) -> None:
    """Streams an HTTP response to disk in 1MB chunks and verifies byte completeness."""
    total_len = response.getheader("Content-Length")
    total_bytes = int(total_len) if total_len and total_len.isdigit() else 0
    downloaded = 0
    chunk_size = 1024 * 1024  # 1MB chunks

    with open(dest_path, "wb") as out_file:
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

    if total_bytes > 0 and downloaded < total_bytes:
        raise IOError(
            f"Download stream interrupted prematurely: expected {total_bytes:,} bytes, "
            f"received {downloaded:,} bytes."
        )


def fetch_github_release_metadata(owner: str, repo: str, tag: str, token: str) -> dict:
    """Queries GitHub REST API for release metadata by tag name using Bearer authentication."""
    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{urllib.parse.quote(tag, safe='')}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "NavSakhi-AssetDownloader/2.0",
    }
    req = urllib.request.Request(api_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise PermissionError(
                "GitHub API authentication failed (HTTP 401 Unauthorized). "
                "The NAVSAKHI_GITHUB_TOKEN is invalid or expired."
            )
        elif e.code == 403:
            raise PermissionError(
                "GitHub API access forbidden (HTTP 403 Forbidden). "
                "Ensure NAVSAKHI_GITHUB_TOKEN has 'Contents: Read-only' permission on "
                f"'{owner}/{repo}', or check GitHub API rate limits."
            )
        elif e.code == 404:
            raise FileNotFoundError(
                f"Release tag '{tag}' not found in GitHub repository '{owner}/{repo}' (HTTP 404 Not Found)."
            )
        else:
            raise RuntimeError(
                f"GitHub API release metadata lookup failed with HTTP {e.code}: {e.reason}"
            )
    except urllib.error.URLError as e:
        raise ConnectionError(f"Network error connecting to GitHub API: {e.reason}")


def find_release_asset(release_data: dict, filename: str) -> dict:
    """Finds the single exact matching asset by filename in release metadata."""
    assets = release_data.get("assets", [])
    matching = [a for a in assets if a.get("name") == filename]
    if not matching:
        available = [a.get("name") for a in assets if a.get("name")]
        raise FileNotFoundError(
            f"Asset '{filename}' not found in release. "
            f"Available assets ({len(available)}): {', '.join(available) if available else 'none'}"
        )
    if len(matching) > 1:
        raise ValueError(
            f"Ambiguous release assets: found {len(matching)} assets matching filename '{filename}'."
        )
    return matching[0]


def download_authenticated_github_release_asset(
    owner: str,
    repo: str,
    tag: str,
    filename: str,
    token: str,
    dest_path: Path
) -> None:
    """
    Downloads release asset via GitHub REST API with Bearer token authentication.
    Intercepts redirects to signed storage URLs (e.g., S3 / objects.githubusercontent.com)
    and strictly strips the Authorization header before following the redirect.
    Enforces an explicit redirect destination allowlist, maximum hop count, and loop rejection.
    """
    logger.info(f"Querying GitHub REST API for release '{tag}' in '{owner}/{repo}'...")
    release_data = fetch_github_release_metadata(owner, repo, tag, token)

    logger.info(f"Locating asset '{filename}' in release '{tag}'...")
    asset = find_release_asset(release_data, filename)

    asset_id = asset.get("id")
    asset_api_url = asset.get("url") or f"https://api.github.com/repos/{owner}/{repo}/releases/assets/{asset_id}"

    logger.info(f"Requesting release asset binary stream for asset ID {asset_id}...")

    current_url = asset_api_url
    headers = {
        "Accept": "application/octet-stream",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "NavSakhi-AssetDownloader/2.0",
    }

    opener = urllib.request.build_opener(DisallowRedirectHandler())
    visited_urls = {current_url}
    hop_count = 0
    max_hops = 3

    while True:
        req = urllib.request.Request(current_url, headers=headers)
        try:
            with opener.open(req, timeout=300) as response:
                if hop_count == 0:
                    logger.info("Direct binary response received. Streaming asset to disk...")
                else:
                    logger.info("Storage provider binary response received. Streaming asset to disk...")
                _stream_response_to_file(response, dest_path)
                return
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308):
                hop_count += 1
                if hop_count > max_hops:
                    raise RuntimeError(f"Exceeded maximum allowed redirect hops ({max_hops}).")

                redirect_url = e.headers.get("Location")
                if not redirect_url:
                    raise RuntimeError(f"Asset redirect response (HTTP {e.code}) missing 'Location' header.")

                redirect_url = urllib.parse.urljoin(current_url, redirect_url)

                # Validate redirect destination URL against strict security policy
                validate_redirect_url(redirect_url)

                if redirect_url in visited_urls:
                    raise RuntimeError("Redirect loop detected.")
                visited_urls.add(redirect_url)

                parsed_redir = urllib.parse.urlsplit(redirect_url)
                logger.info(
                    f"Following validated redirect hop {hop_count}/{max_hops} to storage host '{parsed_redir.hostname}' "
                    "without GitHub Authorization token..."
                )

                # Strictly strip Authorization header for all redirected requests
                current_url = redirect_url
                headers = {
                    "User-Agent": "NavSakhi-AssetDownloader/2.0",
                    "Accept": "application/octet-stream",
                }
            elif e.code == 401:
                raise PermissionError(
                    "GitHub asset download authentication failed (HTTP 401 Unauthorized)."
                )
            elif e.code == 403:
                raise PermissionError(
                    "GitHub asset download forbidden (HTTP 403 Forbidden). "
                    "Check token permissions for release assets."
                )
            elif e.code == 404:
                raise FileNotFoundError(
                    f"Release asset '{filename}' (ID: {asset_id}) not found on GitHub (HTTP 404 Not Found)."
                )
            else:
                raise RuntimeError(
                    f"GitHub asset download failed with HTTP {e.code}: {e.reason}"
                )
        except urllib.error.URLError as e:
            raise ConnectionError(f"Network error during asset download: {e.reason}")


def download_anonymous_file(url: str, dest_path: Path) -> None:
    """Downloads a file over anonymous HTTPS with chunked streaming and progress reporting."""
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme.lower() != "https":
        raise ValueError(f"Insecure URL scheme '{parsed.scheme}'. Only HTTPS is permitted.")

    logger.info("Connecting to anonymous asset archive download source...")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "NavSakhi-AssetDownloader/2.0"}
    )
    with urllib.request.urlopen(req, timeout=300) as response:
        _stream_response_to_file(response, dest_path)


def download_file(url: str, dest_path: Path, token: Optional[str] = None) -> None:
    """
    Downloads the asset archive.
    If `token` is provided, parses and validates the GitHub release URL and downloads
    via GitHub REST API with Bearer authentication and redirect token stripping.
    If `token` is None or empty, performs anonymous HTTPS download.
    """
    if token and token.strip():
        owner, repo, tag, filename = parse_and_validate_github_release_url(url)
        download_authenticated_github_release_asset(
            owner=owner,
            repo=repo,
            tag=tag,
            filename=filename,
            token=token.strip(),
            dest_path=dest_path
        )
    else:
        download_anonymous_file(url, dest_path)


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
    github_token = os.environ.get("NAVSAKHI_GITHUB_TOKEN")

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

    token_clean = github_token.strip() if github_token and github_token.strip() else None

    with tempfile.TemporaryDirectory(prefix="navsakhi_download_") as dl_tmp:
        dl_archive = Path(dl_tmp) / "downloaded_assets.tar.gz"
        try:
            download_file(archive_url, dl_archive, token=token_clean)
            verify_and_extract_archive(dl_archive, archive_sha256)
        except Exception as e:
            err_msg = str(e)
            if token_clean:
                err_msg = err_msg.replace(token_clean, "[REDACTED]")
            logger.error(f"Asset acquisition failed: {err_msg}")
            sys.exit(1)


if __name__ == "__main__":
    main()
