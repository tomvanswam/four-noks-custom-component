#!/usr/bin/env python3
"""Release script for 4-noks Home Assistant integration.

Analyzes Conventional Commits since the previous release tag,
determines the next semantic version, updates manifest.json,
and generates structured release notes.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import NamedTuple

# Ensure UTF-8 output on all platforms (especially Windows terminals)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

COMMIT_PATTERN = re.compile(
    r"^(?P<type>[a-zA-Z]+)(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?:\s*(?P<subject>.+)$"
)
BREAKING_PATTERN = re.compile(r"BREAKING[ -]CHANGE:\s*(.+)", re.IGNORECASE)


class CommitInfo(NamedTuple):
    """Parsed commit metadata."""

    hash: str
    short_hash: str
    author: str
    subject: str
    body: str
    commit_type: str
    scope: str | None
    is_breaking: bool
    description: str


def run_cmd(args: list[str], cwd: Path | None = None) -> str:
    """Run a shell command and return trimmed stdout."""
    result = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def parse_semver(version_str: str) -> tuple[int, int, int]:
    """Parse a semantic version string (e.g. '0.1.0' or 'v0.1.0') into a 3-tuple."""
    clean = version_str.strip().removeprefix("v").strip()
    parts = clean.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid semver string: '{version_str}'")
    return int(parts[0]), int(parts[1]), int(parts[2])


def format_semver(parts: tuple[int, int, int]) -> str:
    """Format a 3-tuple into a semantic version string."""
    return f"{parts[0]}.{parts[1]}.{parts[2]}"


def get_latest_tag(repo_root: Path) -> str | None:
    """Return the most recent git tag matching 'v*' or None if no tags exist."""
    try:
        raw = run_cmd(["git", "tag", "-l", "v*"], cwd=repo_root)
        if not raw:
            return None
        tags = [t.strip() for t in raw.splitlines() if t.strip()]
        if not tags:
            return None

        # Sort tags by semver
        parsed_tags: list[tuple[tuple[int, int, int], str]] = []
        for tag in tags:
            try:
                parsed_tags.append((parse_semver(tag), tag))
            except ValueError:
                continue

        if not parsed_tags:
            return None

        parsed_tags.sort(key=lambda x: x[0])
        return parsed_tags[-1][1]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_current_manifest_version(manifest_path: Path) -> str:
    """Read the version string from manifest.json."""
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return str(data.get("version", "0.1.0"))


def get_commits_since(repo_root: Path, tag: str | None) -> list[CommitInfo]:
    """Retrieve commits since the given tag (or all commits if tag is None)."""
    delimiter = "---COMMIT_DELIMITER---"
    field_delimiter = "---FIELD_DELIMITER---"

    format_str = (
        f"%H{field_delimiter}"
        f"%h{field_delimiter}"
        f"%an{field_delimiter}"
        f"%s{field_delimiter}"
        f"%b{delimiter}"
    )

    git_args = ["git", "log", f"--pretty=format:{format_str}"]
    if tag:
        git_args.append(f"{tag}..HEAD")
    else:
        git_args.append("HEAD")

    try:
        raw_log = run_cmd(git_args, cwd=repo_root)
    except subprocess.CalledProcessError:
        return []

    if not raw_log:
        return []

    commits: list[CommitInfo] = []
    raw_commits = raw_log.split(delimiter)
    for raw in raw_commits:
        raw = raw.strip()
        if not raw:
            continue
        fields = raw.split(field_delimiter)
        if len(fields) < 5:
            continue

        full_hash, short_hash, author, subject, body = (
            fields[0].strip(),
            fields[1].strip(),
            fields[2].strip(),
            fields[3].strip(),
            fields[4].strip(),
        )

        # Skip release commits and skip-ci commits
        if "[skip ci]" in subject or subject.startswith("chore(release):"):
            continue

        commit_type = "other"
        scope = None
        is_breaking = False
        description = subject

        match = COMMIT_PATTERN.match(subject)
        if match:
            commit_type = match.group("type").lower()
            scope = match.group("scope")
            if match.group("breaking") == "!":
                is_breaking = True
            description = match.group("subject").strip()

        if not is_breaking and BREAKING_PATTERN.search(body):
            is_breaking = True

        commits.append(
            CommitInfo(
                hash=full_hash,
                short_hash=short_hash,
                author=author,
                subject=subject,
                body=body,
                commit_type=commit_type,
                scope=scope,
                is_breaking=is_breaking,
                description=description,
            )
        )

    return commits


def calculate_next_version(
    current_version: str, commits: list[CommitInfo]
) -> tuple[str, str]:
    """Calculate next semver based on conventional commits.

    Returns (next_version, bump_type) where bump_type is 'major', 'minor', or 'patch'.
    """
    major, minor, patch = parse_semver(current_version)

    has_breaking = any(c.is_breaking for c in commits)
    has_features = any(c.commit_type == "feat" for c in commits)

    if has_breaking:
        bump_type = "major"
        next_semver = (1, 0, 0) if major == 0 else (major + 1, 0, 0)
    elif has_features:
        bump_type = "minor"
        next_semver = (major, minor + 1, 0)
    else:
        bump_type = "patch"
        next_semver = (major, minor, patch + 1)

    return format_semver(next_semver), bump_type


def generate_changelog(
    version: str,
    commits: list[CommitInfo],
    previous_tag: str | None = None,
    repo_url: str | None = None,
) -> str:
    """Format conventional commits into a structured Markdown changelog."""
    breaking: list[str] = []
    features: list[str] = []
    fixes: list[str] = []
    maintenance: list[str] = []
    others: list[str] = []

    maint_types = {"chore", "docs", "style", "refactor", "perf", "test", "ci"}

    for c in commits:
        scope_prefix = f"**{c.scope}**: " if c.scope else ""
        entry = f"- {scope_prefix}{c.description} ({c.short_hash} by @{c.author})"

        if c.is_breaking:
            breaking.append(entry)
        elif c.commit_type == "feat":
            features.append(entry)
        elif c.commit_type in ("fix", "bug"):
            fixes.append(entry)
        elif c.commit_type in maint_types:
            maintenance.append(entry)
        else:
            others.append(entry)

    lines: list[str] = [f"## Changes in v{version}", ""]

    if breaking:
        lines.append("### 💥 Breaking Changes")
        lines.extend(breaking)
        lines.append("")

    if features:
        lines.append("### ✨ Features")
        lines.extend(features)
        lines.append("")

    if fixes:
        lines.append("### 🐛 Bug Fixes")
        lines.extend(fixes)
        lines.append("")

    if maintenance:
        lines.append("### 🧰 Maintenance & Improvements")
        lines.extend(maintenance)
        lines.append("")

    if others:
        lines.append("### 🔄 Other Changes")
        lines.extend(others)
        lines.append("")

    if repo_url:
        tag_name = f"v{version}"
        if previous_tag:
            compare_url = f"{repo_url}/compare/{previous_tag}...{tag_name}"
            lines.append(f"**Full Changelog**: {compare_url}")
        else:
            commits_url = f"{repo_url}/commits/{tag_name}"
            lines.append(f"**Commits**: {commits_url}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def update_manifest_version(manifest_path: Path, new_version: str) -> None:
    """Update version field in manifest.json preserving key order and formatting."""
    content = json.loads(manifest_path.read_text(encoding="utf-8"))
    content["version"] = new_version
    manifest_path.write_text(
        json.dumps(content, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    """Orchestrate the release process."""
    parser = argparse.ArgumentParser(description="Prepare a new release.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("custom_components/four_noks/manifest.json"),
        help="Path to manifest.json",
    )
    parser.add_argument(
        "--notes-output",
        type=Path,
        default=Path("release_notes.md"),
        help="Path to write release_notes.md",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Calculate version and changelog without modifying files",
    )
    parser.add_argument(
        "--repo-url",
        type=str,
        default="https://github.com/tomvanswam/four-noks-custom-component",
        help="GitHub repository URL for changelog links",
    )
    args = parser.parse_args()

    repo_root = Path.cwd()
    manifest_path = args.manifest
    if not manifest_path.is_absolute():
        manifest_path = repo_root / manifest_path

    if not manifest_path.exists():
        print(f"Error: manifest file not found at {manifest_path}", file=sys.stderr)
        return 1

    current_version = get_current_manifest_version(manifest_path)
    latest_tag = get_latest_tag(repo_root)

    print(f"Current manifest version: {current_version}")
    print(f"Latest git tag: {latest_tag or 'None (initial release)'}")

    commits = get_commits_since(repo_root, latest_tag)
    if not commits:
        print("No new commits to release.")
        github_output = os.getenv("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a", encoding="utf-8") as f:
                f.write("has_release=false\n")
        return 0

    print(f"Found {len(commits)} commit(s) since {latest_tag or 'beginning'}:")
    for c in commits:
        print(f"  - [{c.commit_type}] {c.subject}")

    next_version, bump_type = calculate_next_version(current_version, commits)
    tag_name = f"v{next_version}"
    print(
        f"Calculated next version: {next_version} ({bump_type} bump) -> Tag: {tag_name}"
    )

    changelog = generate_changelog(
        next_version, commits, previous_tag=latest_tag, repo_url=args.repo_url
    )

    if args.dry_run:
        print("\n--- DRY RUN: Generated Release Notes ---")
        print(changelog)
        print("--- END DRY RUN ---")
        return 0

    # Update manifest.json
    update_manifest_version(manifest_path, next_version)
    print(f"Updated {manifest_path} with version '{next_version}'")

    # Write release notes
    notes_path = args.notes_output
    if not notes_path.is_absolute():
        notes_path = repo_root / notes_path
    notes_path.write_text(changelog, encoding="utf-8")
    print(f"Wrote release notes to {notes_path}")

    # Set GitHub Actions outputs if running in CI
    github_output = os.getenv("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write("has_release=true\n")
            f.write(f"version={next_version}\n")
            f.write(f"tag_name={tag_name}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
