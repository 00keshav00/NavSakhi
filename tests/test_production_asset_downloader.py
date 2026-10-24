# tests/test_production_asset_downloader.py
"""
NavSakhi Phase 51.14 - Production Asset Downloader Security & Authentication Tests

Validates:
- Anonymous HTTPS mode remains functional.
- Authenticated release metadata lookup and exact asset resolution.
- 401/403/404 handling with secret-safe actionable errors.
- Direct binary response and signed-URL redirect handling.
- Authorization header is strictly stripped before following redirects.
- Strict URL validation (HTTPS, github.com, expected repo, no query, no fragment).
- Checksum verification prevents extraction on hash mismatch.
- Malicious archive member detection (traversal, symlinks, unapproved files).
- Tokens are never leaked into logs or error messages.
"""

import io
import json
import logging
import os
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.download_production_assets import (
    ALLOWED_REDIRECT_HOST_REGEXES,
    APPROVED_DESTINATIONS,
    compute_sha256,
    download_anonymous_file,
    download_authenticated_github_release_asset,
    download_file,
    fetch_github_release_metadata,
    find_release_asset,
    is_safe_tar_member,
    main,
    parse_and_validate_github_release_url,
    validate_redirect_url,
    verify_and_extract_archive,
)


# ==============================================================================
# 1. URL Parsing & Strict Validation Tests
# ==============================================================================

def test_parse_valid_github_release_url():
    url = (
        "https://github.com/00keshav00/NavSakhi/releases/download/"
        "v2.0.0/navsakhi-runtime-assets-v2.0.0.tar.gz"
    )
    owner, repo, tag, filename = parse_and_validate_github_release_url(url)
    assert owner == "00keshav00"
    assert repo == "NavSakhi"
    assert tag == "v2.0.0"
    assert filename == "navsakhi-runtime-assets-v2.0.0.tar.gz"


def test_reject_insecure_http_scheme():
    url = (
        "http://github.com/00keshav00/NavSakhi/releases/download/"
        "v2.0.0/navsakhi-runtime-assets-v2.0.0.tar.gz"
    )
    with pytest.raises(ValueError, match="Insecure URL scheme 'http'"):
        parse_and_validate_github_release_url(url)


def test_reject_unexpected_host():
    url = (
        "https://evil-host.com/00keshav00/NavSakhi/releases/download/"
        "v2.0.0/navsakhi-runtime-assets-v2.0.0.tar.gz"
    )
    with pytest.raises(ValueError, match="Invalid hostname 'evil-host.com'"):
        parse_and_validate_github_release_url(url)


def test_reject_host_with_port():
    url = (
        "https://github.com:8443/00keshav00/NavSakhi/releases/download/"
        "v2.0.0/navsakhi-runtime-assets-v2.0.0.tar.gz"
    )
    with pytest.raises(ValueError, match="Invalid hostname"):
        parse_and_validate_github_release_url(url)


def test_reject_url_with_query_string():
    url = (
        "https://github.com/00keshav00/NavSakhi/releases/download/"
        "v2.0.0/navsakhi-runtime-assets-v2.0.0.tar.gz?token=secret123"
    )
    with pytest.raises(ValueError, match="query strings are not permitted"):
        parse_and_validate_github_release_url(url)


def test_reject_url_with_fragment():
    url = (
        "https://github.com/00keshav00/NavSakhi/releases/download/"
        "v2.0.0/navsakhi-runtime-assets-v2.0.0.tar.gz#section"
    )
    with pytest.raises(ValueError, match="fragments are not permitted"):
        parse_and_validate_github_release_url(url)


def test_reject_malformed_path():
    url = "https://github.com/00keshav00/NavSakhi/releases/tag/v2.0.0"
    with pytest.raises(ValueError, match="Malformed GitHub release download path"):
        parse_and_validate_github_release_url(url)


def test_reject_path_traversal_in_url():
    url = (
        "https://github.com/00keshav00/NavSakhi/releases/download/"
        "../v2.0.0/navsakhi-runtime-assets-v2.0.0.tar.gz"
    )
    with pytest.raises(ValueError, match="Path traversal sequences are prohibited"):
        parse_and_validate_github_release_url(url)


def test_reject_repository_mismatch():
    url = (
        "https://github.com/attacker/OtherRepo/releases/download/"
        "v2.0.0/navsakhi-runtime-assets-v2.0.0.tar.gz"
    )
    with pytest.raises(ValueError, match="Repository mismatch in release URL"):
        parse_and_validate_github_release_url(url)


def test_reject_empty_tag_or_filename():
    url1 = "https://github.com/00keshav00/NavSakhi/releases/download/ /asset.tar.gz"
    with pytest.raises(ValueError, match="Release tag cannot be empty"):
        parse_and_validate_github_release_url(url1)

    url2 = "https://github.com/00keshav00/NavSakhi/releases/download/v2.0.0/ "
    with pytest.raises(ValueError, match="Asset filename cannot be empty"):
        parse_and_validate_github_release_url(url2)


# ==============================================================================
# 2. Release Asset Lookup & Ambiguity Tests
# ==============================================================================

def test_find_release_asset_success():
    release_data = {
        "assets": [
            {"id": 101, "name": "other-asset.zip", "url": "https://api.github.com/assets/101"},
            {"id": 102, "name": "navsakhi-assets.tar.gz", "url": "https://api.github.com/assets/102"},
        ]
    }
    found = find_release_asset(release_data, "navsakhi-assets.tar.gz")
    assert found["id"] == 102


def test_find_release_asset_missing_fails_closed():
    release_data = {
        "assets": [
            {"id": 101, "name": "other-asset.zip"},
        ]
    }
    with pytest.raises(FileNotFoundError, match="Asset 'missing.tar.gz' not found in release"):
        find_release_asset(release_data, "missing.tar.gz")


def test_find_release_asset_ambiguous_fails_closed():
    release_data = {
        "assets": [
            {"id": 101, "name": "duplicate.tar.gz"},
            {"id": 102, "name": "duplicate.tar.gz"},
        ]
    }
    with pytest.raises(ValueError, match="Ambiguous release assets: found 2 assets"):
        find_release_asset(release_data, "duplicate.tar.gz")


# ==============================================================================
# 3. GitHub API Authentication & Error Handling Tests
# ==============================================================================

def test_fetch_metadata_401_unauthorized():
    err = urllib.error.HTTPError(
        url="https://api.github.com/repos/00keshav00/NavSakhi/releases/tags/v2.0.0",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=io.BytesIO(b'{"message": "Bad credentials"}'),
    )
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(PermissionError, match="HTTP 401 Unauthorized"):
            fetch_github_release_metadata("00keshav00", "NavSakhi", "v2.0.0", "bad_token")


def test_fetch_metadata_403_forbidden():
    err = urllib.error.HTTPError(
        url="https://api.github.com/repos/00keshav00/NavSakhi/releases/tags/v2.0.0",
        code=403,
        msg="Forbidden",
        hdrs={},
        fp=io.BytesIO(b'{"message": "Resource not accessible by personal access token"}'),
    )
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(PermissionError, match="HTTP 403 Forbidden"):
            fetch_github_release_metadata("00keshav00", "NavSakhi", "v2.0.0", "limited_token")


def test_fetch_metadata_404_not_found():
    err = urllib.error.HTTPError(
        url="https://api.github.com/repos/00keshav00/NavSakhi/releases/tags/v9.9.9",
        code=404,
        msg="Not Found",
        hdrs={},
        fp=io.BytesIO(b'{"message": "Not Found"}'),
    )
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(FileNotFoundError, match="Release tag 'v9.9.9' not found"):
            fetch_github_release_metadata("00keshav00", "NavSakhi", "v9.9.9", "valid_token")


# ==============================================================================
# 4. Binary Response & Redirect Security Tests
# ==============================================================================

def test_authenticated_direct_binary_response(tmp_path):
    dest = tmp_path / "downloaded.tar.gz"
    fake_binary = b"NAVSAKHI_BINARY_PAYLOAD_DIRECT"

    mock_release = {
        "assets": [
            {
                "id": 999,
                "name": "assets.tar.gz",
                "url": "https://api.github.com/repos/00keshav00/NavSakhi/releases/assets/999",
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.getheader.return_value = str(len(fake_binary))
    mock_response.read.side_effect = [fake_binary, b""]
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = None

    with patch("scripts.download_production_assets.fetch_github_release_metadata", return_value=mock_release):
        with patch("urllib.request.OpenerDirector.open", return_value=mock_response) as mock_open:
            download_authenticated_github_release_asset(
                owner="00keshav00",
                repo="NavSakhi",
                tag="v2.0.0",
                filename="assets.tar.gz",
                token="test_token_123",
                dest_path=dest,
            )

            # Verify request headers to GitHub API
            called_req = mock_open.call_args[0][0]
            assert called_req.get_header("Authorization") == "Bearer test_token_123"
            assert called_req.get_header("Accept") == "application/octet-stream"
            assert dest.read_bytes() == fake_binary


def test_validate_redirect_url_destination_policy():
    """Validates strict URL scheme, credential, port, and hostname filtering."""
    # Legitimate destinations
    validate_redirect_url("https://objects.githubusercontent.com/some/path?sig=abc")
    validate_redirect_url("https://objects.githubusercontent.com:443/some/path?sig=abc")
    validate_redirect_url("https://github-production-release-asset-2e65be.s3.amazonaws.com/asset.tar.gz")
    validate_redirect_url("https://github-production-release-asset-2e65be.s3.us-east-1.amazonaws.com/asset.tar.gz")
    validate_redirect_url("https://api.github.com/repos/00keshav00/NavSakhi/releases/assets/123")

    # Insecure schemes
    with pytest.raises(ValueError, match="Insecure redirect URL scheme 'http'"):
        validate_redirect_url("http://objects.githubusercontent.com/asset.tar.gz")

    # Embedded credentials
    with pytest.raises(ValueError, match="embedded user credentials"):
        validate_redirect_url("https://user:pass@objects.githubusercontent.com/asset.tar.gz")

    # Non-standard ports
    with pytest.raises(ValueError, match="Non-standard port '8443'"):
        validate_redirect_url("https://objects.githubusercontent.com:8443/asset.tar.gz")

    # Unexpected or unapproved hosts
    with pytest.raises(ValueError, match="not in the approved GitHub storage host allowlist"):
        validate_redirect_url("https://evil-attacker.com/asset.tar.gz")

    with pytest.raises(ValueError, match="not in the approved GitHub storage host allowlist"):
        validate_redirect_url("https://attacker-bucket.s3.amazonaws.com/asset.tar.gz")

    with pytest.raises(ValueError, match="not in the approved GitHub storage host allowlist"):
        validate_redirect_url("https://github-production-release-asset-2e65be.s3.amazonaws.com.evil.com/asset.tar.gz")

    # Localhost, loopback, link-local metadata
    with pytest.raises(ValueError, match="not in the approved GitHub storage host allowlist"):
        validate_redirect_url("https://localhost/asset.tar.gz")

    with pytest.raises(ValueError, match="not in the approved GitHub storage host allowlist"):
        validate_redirect_url("https://127.0.0.1/asset.tar.gz")

    with pytest.raises(ValueError, match="not in the approved GitHub storage host allowlist"):
        validate_redirect_url("https://169.254.169.254/latest/meta-data/")


def test_authenticated_signed_url_redirect_strips_token(tmp_path):
    dest = tmp_path / "downloaded.tar.gz"
    fake_binary = b"NAVSAKHI_SIGNED_S3_BINARY_PAYLOAD"
    signed_s3_url = "https://objects.githubusercontent.com/github-production-release-asset-999?signed_token=xyz"

    mock_release = {
        "assets": [
            {
                "id": 888,
                "name": "assets.tar.gz",
                "url": "https://api.github.com/repos/00keshav00/NavSakhi/releases/assets/888",
            }
        ]
    }

    # Opener will raise 302 Found on first call, return binary on second call
    redirect_err = urllib.error.HTTPError(
        url="https://api.github.com/repos/00keshav00/NavSakhi/releases/assets/888",
        code=302,
        msg="Found",
        hdrs={"Location": signed_s3_url},
        fp=io.BytesIO(b""),
    )

    mock_s3_resp = MagicMock()
    mock_s3_resp.getheader.return_value = str(len(fake_binary))
    mock_s3_resp.read.side_effect = [fake_binary, b""]
    mock_s3_resp.__enter__.return_value = mock_s3_resp
    mock_s3_resp.__exit__.return_value = None

    with patch("scripts.download_production_assets.fetch_github_release_metadata", return_value=mock_release):
        with patch("urllib.request.OpenerDirector.open", side_effect=[redirect_err, mock_s3_resp]) as mock_open:
            download_authenticated_github_release_asset(
                owner="00keshav00",
                repo="NavSakhi",
                tag="v2.0.0",
                filename="assets.tar.gz",
                token="SUPER_SECRET_GITHUB_BEARER_TOKEN",
                dest_path=dest,
            )

            # Verification: Exactly 2 requests were made
            assert mock_open.call_count == 2

            # Request 1: To GitHub API with Authorization header
            req1 = mock_open.call_args_list[0][0][0]
            assert req1.full_url == "https://api.github.com/repos/00keshav00/NavSakhi/releases/assets/888"
            assert req1.get_header("Authorization") == "Bearer SUPER_SECRET_GITHUB_BEARER_TOKEN"

            # Request 2: To signed storage URL WITHOUT Authorization header
            req2 = mock_open.call_args_list[1][0][0]
            assert req2.full_url == signed_s3_url
            assert req2.get_header("Authorization") is None
            assert "SUPER_SECRET_GITHUB_BEARER_TOKEN" not in str(req2.headers)

            assert dest.read_bytes() == fake_binary


def test_authenticated_multi_hop_redirect_succeeds(tmp_path):
    dest = tmp_path / "downloaded.tar.gz"
    fake_binary = b"NAVSAKHI_MULTI_HOP_PAYLOAD"
    hop1_url = "https://objects.githubusercontent.com/cdn/asset"
    hop2_url = "https://github-production-release-asset-2e65be.s3.amazonaws.com/storage/asset"

    mock_release = {
        "assets": [
            {
                "id": 888,
                "name": "assets.tar.gz",
                "url": "https://api.github.com/repos/00keshav00/NavSakhi/releases/assets/888",
            }
        ]
    }

    err_hop1 = urllib.error.HTTPError(
        url="https://api.github.com/repos/00keshav00/NavSakhi/releases/assets/888",
        code=302,
        msg="Found",
        hdrs={"Location": hop1_url},
        fp=io.BytesIO(b""),
    )
    err_hop2 = urllib.error.HTTPError(
        url=hop1_url,
        code=307,
        msg="Temporary Redirect",
        hdrs={"Location": hop2_url},
        fp=io.BytesIO(b""),
    )

    mock_final_resp = MagicMock()
    mock_final_resp.getheader.return_value = str(len(fake_binary))
    mock_final_resp.read.side_effect = [fake_binary, b""]
    mock_final_resp.__enter__.return_value = mock_final_resp
    mock_final_resp.__exit__.return_value = None

    with patch("scripts.download_production_assets.fetch_github_release_metadata", return_value=mock_release):
        with patch("urllib.request.OpenerDirector.open", side_effect=[err_hop1, err_hop2, mock_final_resp]) as mock_open:
            download_authenticated_github_release_asset(
                owner="00keshav00",
                repo="NavSakhi",
                tag="v2.0.0",
                filename="assets.tar.gz",
                token="SUPER_SECRET_TOKEN",
                dest_path=dest,
            )

            assert mock_open.call_count == 3
            # Check Authorization is stripped on hops 1 and 2
            assert mock_open.call_args_list[1][0][0].get_header("Authorization") is None
            assert mock_open.call_args_list[2][0][0].get_header("Authorization") is None
            assert dest.read_bytes() == fake_binary


def test_redirect_to_unexpected_hostname_rejected(tmp_path):
    dest = tmp_path / "downloaded.tar.gz"
    mock_release = {"assets": [{"id": 888, "name": "assets.tar.gz", "url": "https://api.github.com/assets/888"}]}
    unapproved_err = urllib.error.HTTPError(
        url="https://api.github.com/assets/888",
        code=302,
        msg="Found",
        hdrs={"Location": "https://evil-unapproved-storage.com/asset.tar.gz"},
        fp=io.BytesIO(b""),
    )

    with patch("scripts.download_production_assets.fetch_github_release_metadata", return_value=mock_release):
        with patch("urllib.request.OpenerDirector.open", side_effect=unapproved_err):
            with pytest.raises(ValueError, match="not in the approved GitHub storage host allowlist"):
                download_authenticated_github_release_asset(
                    owner="00keshav00",
                    repo="NavSakhi",
                    tag="v2.0.0",
                    filename="assets.tar.gz",
                    token="valid_token",
                    dest_path=dest,
                )


def test_redirect_to_insecure_http_rejected(tmp_path):
    dest = tmp_path / "downloaded.tar.gz"
    mock_release = {"assets": [{"id": 888, "name": "assets.tar.gz", "url": "https://api.github.com/assets/888"}]}
    insecure_err = urllib.error.HTTPError(
        url="https://api.github.com/assets/888",
        code=302,
        msg="Found",
        hdrs={"Location": "http://objects.githubusercontent.com/asset.tar.gz"},
        fp=io.BytesIO(b""),
    )

    with patch("scripts.download_production_assets.fetch_github_release_metadata", return_value=mock_release):
        with patch("urllib.request.OpenerDirector.open", side_effect=insecure_err):
            with pytest.raises(ValueError, match="Insecure redirect URL scheme 'http'"):
                download_authenticated_github_release_asset(
                    owner="00keshav00",
                    repo="NavSakhi",
                    tag="v2.0.0",
                    filename="assets.tar.gz",
                    token="valid_token",
                    dest_path=dest,
                )


def test_redirect_with_missing_location_rejected(tmp_path):
    dest = tmp_path / "downloaded.tar.gz"
    mock_release = {"assets": [{"id": 888, "name": "assets.tar.gz", "url": "https://api.github.com/assets/888"}]}
    missing_loc_err = urllib.error.HTTPError(
        url="https://api.github.com/assets/888",
        code=302,
        msg="Found",
        hdrs={},
        fp=io.BytesIO(b""),
    )

    with patch("scripts.download_production_assets.fetch_github_release_metadata", return_value=mock_release):
        with patch("urllib.request.OpenerDirector.open", side_effect=missing_loc_err):
            with pytest.raises(RuntimeError, match="missing 'Location' header"):
                download_authenticated_github_release_asset(
                    owner="00keshav00",
                    repo="NavSakhi",
                    tag="v2.0.0",
                    filename="assets.tar.gz",
                    token="valid_token",
                    dest_path=dest,
                )


def test_redirect_loop_detected_fails_closed(tmp_path):
    dest = tmp_path / "downloaded.tar.gz"
    mock_release = {"assets": [{"id": 888, "name": "assets.tar.gz", "url": "https://api.github.com/assets/888"}]}
    loop_url = "https://objects.githubusercontent.com/loop"

    loop_err1 = urllib.error.HTTPError(
        url="https://api.github.com/assets/888",
        code=302,
        msg="Found",
        hdrs={"Location": loop_url},
        fp=io.BytesIO(b""),
    )
    loop_err2 = urllib.error.HTTPError(
        url=loop_url,
        code=302,
        msg="Found",
        hdrs={"Location": loop_url},
        fp=io.BytesIO(b""),
    )

    with patch("scripts.download_production_assets.fetch_github_release_metadata", return_value=mock_release):
        with patch("urllib.request.OpenerDirector.open", side_effect=[loop_err1, loop_err2]):
            with pytest.raises(RuntimeError, match="Redirect loop detected"):
                download_authenticated_github_release_asset(
                    owner="00keshav00",
                    repo="NavSakhi",
                    tag="v2.0.0",
                    filename="assets.tar.gz",
                    token="valid_token",
                    dest_path=dest,
                )


def test_excessive_redirect_hops_fails_closed(tmp_path):
    dest = tmp_path / "downloaded.tar.gz"
    mock_release = {"assets": [{"id": 888, "name": "assets.tar.gz", "url": "https://api.github.com/assets/888"}]}

    # 4 hops to distinct approved URLs
    hops = [
        urllib.error.HTTPError(url="https://api.github.com/assets/888", code=302, msg="Found", hdrs={"Location": f"https://objects.githubusercontent.com/hop{i}"}, fp=io.BytesIO(b""))
        for i in range(1, 5)
    ]

    with patch("scripts.download_production_assets.fetch_github_release_metadata", return_value=mock_release):
        with patch("urllib.request.OpenerDirector.open", side_effect=hops):
            with pytest.raises(RuntimeError, match="Exceeded maximum allowed redirect hops"):
                download_authenticated_github_release_asset(
                    owner="00keshav00",
                    repo="NavSakhi",
                    tag="v2.0.0",
                    filename="assets.tar.gz",
                    token="valid_token",
                    dest_path=dest,
                )


def test_redirect_chain_revalidated_at_every_hop(tmp_path):
    dest = tmp_path / "downloaded.tar.gz"
    mock_release = {"assets": [{"id": 888, "name": "assets.tar.gz", "url": "https://api.github.com/assets/888"}]}

    # Hop 1 is approved (objects.githubusercontent.com), but Hop 2 tries to escape to evil.com
    hop1 = urllib.error.HTTPError(
        url="https://api.github.com/assets/888",
        code=302,
        msg="Found",
        hdrs={"Location": "https://objects.githubusercontent.com/hop1"},
        fp=io.BytesIO(b""),
    )
    hop2 = urllib.error.HTTPError(
        url="https://objects.githubusercontent.com/hop1",
        code=302,
        msg="Found",
        hdrs={"Location": "https://evil.com/payload"},
        fp=io.BytesIO(b""),
    )

    with patch("scripts.download_production_assets.fetch_github_release_metadata", return_value=mock_release):
        with patch("urllib.request.OpenerDirector.open", side_effect=[hop1, hop2]):
            with pytest.raises(ValueError, match="not in the approved GitHub storage host allowlist"):
                download_authenticated_github_release_asset(
                    owner="00keshav00",
                    repo="NavSakhi",
                    tag="v2.0.0",
                    filename="assets.tar.gz",
                    token="valid_token",
                    dest_path=dest,
                )


# ==============================================================================
# 5. Secret Token Hygiene Tests
# ==============================================================================

def test_token_value_never_in_exception_or_logs(caplog):
    secret_token = "ghp_CANARY_SECRET_TOKEN_VALUE_NEVER_LEAK"
    url = (
        "https://github.com/00keshav00/NavSakhi/releases/download/"
        "v2.0.0/navsakhi-runtime-assets-v2.0.0.tar.gz"
    )

    err = urllib.error.HTTPError(
        url="https://api.github.com/repos/00keshav00/NavSakhi/releases/tags/v2.0.0",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=io.BytesIO(b'{"message": "Bad credentials"}'),
    )

    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(PermissionError) as exc_info:
            with caplog.at_level(logging.DEBUG):
                download_file(url, Path("dummy.tar.gz"), token=secret_token)

        assert secret_token not in str(exc_info.value)
        assert secret_token not in caplog.text


# ==============================================================================
# 6. Anonymous Mode & Interruption Tests
# ==============================================================================

def test_anonymous_mode_when_token_absent(tmp_path):
    dest = tmp_path / "anonymous.tar.gz"
    fake_content = b"ANONYMOUS_PAYLOAD"

    mock_resp = MagicMock()
    mock_resp.getheader.return_value = str(len(fake_content))
    mock_resp.read.side_effect = [fake_content, b""]
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
        download_file("https://example.com/assets.tar.gz", dest, token=None)
        req = mock_open.call_args[0][0]
        assert req.get_header("Authorization") is None
        assert dest.read_bytes() == fake_content


def test_download_interrupted_fails_closed(tmp_path):
    dest = tmp_path / "incomplete.tar.gz"
    mock_resp = MagicMock()
    mock_resp.getheader.return_value = "1000"  # Expected 1000 bytes
    mock_resp.read.side_effect = [b"short_data", b""]  # Only 10 bytes returned
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    with patch("urllib.request.urlopen", return_value=mock_resp):
        with pytest.raises(IOError, match="Download stream interrupted prematurely"):
            download_anonymous_file("https://example.com/assets.tar.gz", dest)


# ==============================================================================
# 7. Archive Integrity & Malicious Member Rejection Tests
# ==============================================================================

def _create_minimal_valid_archive(output_path: Path) -> str:
    """Helper creating a test tar.gz with an approved member and embedded manifest."""
    manifest_data = {
        "version": "2.0.0",
        "assets": [
            {
                "path": "poi_data/manifest.json",
                "size_bytes": 13,
                "sha256": compute_sha256_bytes(b'{"test": true}'),
            }
        ]
    }
    with tarfile.open(output_path, "w:gz") as tar:
        # manifest.json
        m_bytes = json.dumps(manifest_data).encode("utf-8")
        ti_m = tarfile.TarInfo(name="manifest.json")
        ti_m.size = len(m_bytes)
        tar.addfile(ti_m, io.BytesIO(m_bytes))

        # approved member
        p_bytes = b'{"test": true}'
        ti_p = tarfile.TarInfo(name="poi_data/manifest.json")
        ti_p.size = len(p_bytes)
        tar.addfile(ti_p, io.BytesIO(p_bytes))

    return compute_sha256(output_path)


def compute_sha256_bytes(b: bytes) -> str:
    import hashlib
    return hashlib.sha256(b).hexdigest().lower()


def test_archive_checksum_mismatch_prevents_extraction(tmp_path):
    archive_path = tmp_path / "test.tar.gz"
    actual_hash = _create_minimal_valid_archive(archive_path)
    wrong_hash = "0" * 64

    with pytest.raises(ValueError, match="Archive SHA-256 checksum mismatch"):
        verify_and_extract_archive(archive_path, wrong_hash)


def test_malicious_path_traversal_member_rejected(tmp_path):
    archive_path = tmp_path / "traversal.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        evil_ti = tarfile.TarInfo(name="../etc/passwd")
        evil_ti.size = 5
        tar.addfile(evil_ti, io.BytesIO(b"evil!"))

    archive_hash = compute_sha256(archive_path)
    with pytest.raises(ValueError, match="unsafe or forbidden member"):
        verify_and_extract_archive(archive_path, archive_hash)


def test_malicious_unapproved_member_rejected(tmp_path):
    archive_path = tmp_path / "unapproved.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        ti = tarfile.TarInfo(name="malicious_payload.py")
        ti.size = 5
        tar.addfile(ti, io.BytesIO(b"evil!"))

    archive_hash = compute_sha256(archive_path)
    with pytest.raises(ValueError, match="unsafe or forbidden member"):
        verify_and_extract_archive(archive_path, archive_hash)


def test_malicious_symlink_member_rejected(tmp_path):
    archive_path = tmp_path / "symlink.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        ti = tarfile.TarInfo(name="poi_data/manifest.json")
        ti.type = tarfile.SYMTYPE
        ti.linkname = "/etc/passwd"
        tar.addfile(ti)

    archive_hash = compute_sha256(archive_path)
    with pytest.raises(ValueError, match="unsafe or forbidden member"):
        verify_and_extract_archive(archive_path, archive_hash)


# ==============================================================================
# 8. Main CLI Environment Variable Gate Tests
# ==============================================================================

def test_main_missing_archive_url_exits():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1


def test_main_missing_archive_sha256_exits():
    env = {"NAVSAKHI_ASSET_ARCHIVE_URL": "https://github.com/00keshav00/NavSakhi/releases/download/v2.0.0/assets.tar.gz"}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1


def test_main_invalid_hash_length_exits():
    env = {
        "NAVSAKHI_ASSET_ARCHIVE_URL": "https://github.com/00keshav00/NavSakhi/releases/download/v2.0.0/assets.tar.gz",
        "NAVSAKHI_ASSET_ARCHIVE_SHA256": "too_short_hash",
    }
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
