"""
Test suite for Phase 51.97: Legal, Transparency, and Navigation Discoverability.
Verifies that:
1. All 7 mandatory legal/informational pages exist as Next.js workspace routes.
2. Header.tsx profile dropdown includes links to all legal pages.
3. MobileNav.tsx includes direct navigation to legal pages.
4. settings/page.tsx includes a dedicated 'legal' tab linking to all 7 disclosures.
5. profile/page.tsx includes the legal card and Footer component.
"""

from pathlib import Path

LEGAL_SLUGS = [
    "terms",
    "privacy",
    "limitations",
    "safety-guidelines",
    "about",
    "help",
    "accessibility"
]

WORKSPACE_DIR = Path("frontend/src/app/(workspace)")


def test_all_seven_legal_routes_exist():
    """Verify that all 7 legal routes have page.tsx files."""
    for slug in LEGAL_SLUGS:
        page_file = WORKSPACE_DIR / slug / "page.tsx"
        assert page_file.exists(), f"Missing legal route file: {page_file}"
        content = page_file.read_text(encoding="utf-8")
        assert len(content) > 100, f"Legal page {slug} is empty or stub"
        assert "export default" in content, f"Legal page {slug} does not default export a React component"


def test_header_includes_legal_links():
    """Verify Header.tsx profile menu contains links to all legal and help pages."""
    header_file = Path("frontend/src/components/layout/Header.tsx")
    assert header_file.exists()
    content = header_file.read_text(encoding="utf-8")

    for slug in LEGAL_SLUGS:
        assert f"/{slug}" in content, f"Header.tsx does not link to /{slug}"


def test_mobilenav_includes_legal_links():
    """Verify MobileNav.tsx contains direct links to policy routes."""
    nav_file = Path("frontend/src/components/layout/MobileNav.tsx")
    assert nav_file.exists()
    content = nav_file.read_text(encoding="utf-8")

    assert "/privacy" in content
    assert "/terms" in content
    assert "/accessibility" in content


def test_settings_page_includes_legal_tab_and_grid():
    """Verify settings/page.tsx includes 'legal' in tabs and renders the 7-page grid."""
    settings_file = WORKSPACE_DIR / "settings" / "page.tsx"
    assert settings_file.exists()
    content = settings_file.read_text(encoding="utf-8")

    assert '"legal"' in content or "'legal'" in content
    for slug in LEGAL_SLUGS:
        assert f"/{slug}" in content, f"settings/page.tsx does not link to /{slug}"


def test_profile_page_includes_legal_card_and_footer():
    """Verify profile/page.tsx includes legal policy links and the global Footer."""
    profile_file = WORKSPACE_DIR / "profile" / "page.tsx"
    assert profile_file.exists()
    content = profile_file.read_text(encoding="utf-8")

    assert "Legal, Privacy & Policies" in content
    assert "/terms" in content
    assert "/privacy" in content
    assert "/limitations" in content
    assert "<Footer" in content
