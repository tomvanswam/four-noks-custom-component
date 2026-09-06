"""Unit tests for the release script."""

import json
from pathlib import Path

import pytest

from scripts.release import (
    CommitInfo,
    calculate_next_version,
    format_semver,
    generate_changelog,
    get_commits_since,
    get_current_manifest_version,
    parse_semver,
    update_manifest_version,
)


def test_parse_semver_valid():
    """Test valid semver parsing."""
    assert parse_semver("1.2.3") == (1, 2, 3)
    assert parse_semver("v1.2.3") == (1, 2, 3)
    assert parse_semver("  v0.1.0  ") == (0, 1, 0)


def test_parse_semver_invalid():
    """Test invalid semver strings raise ValueError."""
    with pytest.raises(ValueError, match="Invalid semver"):
        parse_semver("1.2")
    with pytest.raises(ValueError, match="Invalid semver"):
        parse_semver("abc")
    with pytest.raises(ValueError, match="Invalid semver"):
        parse_semver("1.2.3.4")


def test_format_semver():
    """Test semver formatting."""
    assert format_semver((1, 2, 3)) == "1.2.3"
    assert format_semver((0, 1, 0)) == "0.1.0"


def test_calculate_next_version_major_breaking():
    """Test major bump when breaking changes exist."""
    commits = [
        CommitInfo(
            hash="abc",
            short_hash="abc",
            author="Dev",
            subject="feat!: breaking change",
            body="",
            commit_type="feat",
            scope=None,
            is_breaking=True,
            description="breaking change",
        )
    ]
    # In 0.x, breaking change bumps to 1.0.0
    next_ver, bump = calculate_next_version("0.2.0", commits)
    assert bump == "major"
    assert next_ver == "1.0.0"

    # In 1.x, breaking change bumps to 2.0.0
    next_ver2, bump2 = calculate_next_version("1.3.4", commits)
    assert bump2 == "major"
    assert next_ver2 == "2.0.0"


def test_calculate_next_version_minor_feature():
    """Test minor bump when new features exist."""
    commits = [
        CommitInfo(
            hash="abc",
            short_hash="abc",
            author="Dev",
            subject="feat(sensor): add power sensor",
            body="",
            commit_type="feat",
            scope="sensor",
            is_breaking=False,
            description="add power sensor",
        ),
        CommitInfo(
            hash="def",
            short_hash="def",
            author="Dev",
            subject="fix: small bug",
            body="",
            commit_type="fix",
            scope=None,
            is_breaking=False,
            description="small bug",
        ),
    ]
    next_ver, bump = calculate_next_version("0.1.0", commits)
    assert bump == "minor"
    assert next_ver == "0.2.0"


def test_calculate_next_version_patch():
    """Test patch bump for bug fixes or chores."""
    commits = [
        CommitInfo(
            hash="abc",
            short_hash="abc",
            author="Dev",
            subject="fix(config_flow): handle invalid host",
            body="",
            commit_type="fix",
            scope="config_flow",
            is_breaking=False,
            description="handle invalid host",
        ),
        CommitInfo(
            hash="def",
            short_hash="def",
            author="Dev",
            subject="chore: clean up code",
            body="",
            commit_type="chore",
            scope=None,
            is_breaking=False,
            description="clean up code",
        ),
    ]
    next_ver, bump = calculate_next_version("0.2.0", commits)
    assert bump == "patch"
    assert next_ver == "0.2.1"


def test_generate_changelog_categorization():
    """Test changelog generates correct sections and markdown."""
    commits = [
        CommitInfo(
            hash="1111111",
            short_hash="1111111",
            author="Alice",
            subject="feat!: breaking new api",
            body="",
            commit_type="feat",
            scope=None,
            is_breaking=True,
            description="breaking new api",
        ),
        CommitInfo(
            hash="2222222",
            short_hash="2222222",
            author="Bob",
            subject="feat(plug): add power reading",
            body="",
            commit_type="feat",
            scope="plug",
            is_breaking=False,
            description="add power reading",
        ),
        CommitInfo(
            hash="3333333",
            short_hash="3333333",
            author="Charlie",
            subject="fix: resolve timeout",
            body="",
            commit_type="fix",
            scope=None,
            is_breaking=False,
            description="resolve timeout",
        ),
        CommitInfo(
            hash="4444444",
            short_hash="4444444",
            author="Diana",
            subject="docs: update readme",
            body="",
            commit_type="docs",
            scope=None,
            is_breaking=False,
            description="update readme",
        ),
    ]

    changelog = generate_changelog(
        version="1.0.0",
        commits=commits,
        previous_tag="v0.2.0",
        repo_url="https://github.com/example/repo",
    )

    assert "## Changes in v1.0.0" in changelog
    assert "### 💥 Breaking Changes" in changelog
    assert "- breaking new api (1111111 by @Alice)" in changelog
    assert "### ✨ Features" in changelog
    assert "- **plug**: add power reading (2222222 by @Bob)" in changelog
    assert "### 🐛 Bug Fixes" in changelog
    assert "- resolve timeout (3333333 by @Charlie)" in changelog
    assert "### 🧰 Maintenance & Improvements" in changelog
    assert "- update readme (4444444 by @Diana)" in changelog
    assert (
        "**Full Changelog**: https://github.com/example/repo/compare/v0.2.0...v1.0.0"
        in changelog
    )


def test_generate_changelog_initial_release():
    """Test changelog for initial release without previous tag."""
    commits = [
        CommitInfo(
            hash="1111111",
            short_hash="1111111",
            author="Alice",
            subject="feat: initial commit",
            body="",
            commit_type="feat",
            scope=None,
            is_breaking=False,
            description="initial commit",
        )
    ]

    changelog = generate_changelog(
        version="0.1.0",
        commits=commits,
        previous_tag=None,
        repo_url="https://github.com/example/repo",
    )

    assert "**Commits**: https://github.com/example/repo/commits/v0.1.0" in changelog


def test_update_manifest_version(tmp_path: Path):
    """Test manifest.json version updating."""
    test_manifest = tmp_path / "manifest.json"
    initial_content = {
        "domain": "four_noks",
        "name": "4-noks",
        "version": "0.1.0",
        "documentation": "https://example.com",
    }
    test_manifest.write_text(json.dumps(initial_content, indent=2), encoding="utf-8")

    assert get_current_manifest_version(test_manifest) == "0.1.0"

    update_manifest_version(test_manifest, "0.2.0")

    assert get_current_manifest_version(test_manifest) == "0.2.0"
    updated_data = json.loads(test_manifest.read_text(encoding="utf-8"))
    assert updated_data["version"] == "0.2.0"
    assert updated_data["domain"] == "four_noks"


def test_get_commits_since_filtering(tmp_path: Path):
    """Test commit retrieval skips release and skip-ci commits."""
    # We can test against actual repo root
    repo_root = Path.cwd()
    commits = get_commits_since(repo_root, None)
    assert len(commits) > 0
    # None of the parsed commits should contain [skip ci] or chore(release)
    for c in commits:
        assert "[skip ci]" not in c.subject
        assert not c.subject.startswith("chore(release):")
