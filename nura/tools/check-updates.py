#!/usr/bin/env python3
"""Check the packages in nura/ for upstream updates (GitHub sources only).

For every APKBUILD under nura/ (or the given directories), takes the first source and, when it is a
GitHub archive or release download:

- pinned at a commit: how many commits the default branch (or `_branch=` in the APKBUILD) is ahead,
  and the newest tag;
- pinned at a tag/version: the latest release (or the newest tag if there are no releases).

Other sources (Debian, SourceForge, project websites) are listed as skipped. Submodules are not
checked. Not exact: tag naming differs between projects, so compare by eye.

    GITHUB_TOKEN=$(gh auth token) nura/tools/check-updates.py [--all] [DIR...]

--all also lists packages that look current. Without a token the GitHub API allows 60 requests
per hour, which isn't enough for all packages.
"""

import argparse
import glob
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
NURA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def get(path):
    req = urllib.request.Request(API + path, headers={"Accept": "application/vnd.github+json",
                                                      "User-Agent": "nura-check-updates"})
    if os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", "Bearer " + os.environ["GITHUB_TOKEN"])
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def apkbuild_vars(path):
    """pkgname, pkgver and the expanded source list, by sourcing the APKBUILD in a shell."""
    script = ('srcdir=/srcdir; builddir=; . ./APKBUILD >/dev/null 2>&1; '
              'printf "%s\\n" "$pkgname" "$pkgver" "$_branch"; printf "%s\\n" $source')
    out = subprocess.run(["sh", "-c", script], cwd=os.path.dirname(path),
                         capture_output=True, text=True).stdout.splitlines()
    if len(out) < 3:
        return None
    sources = [s.split("::", 1)[-1] for s in out[3:] if "://" in s]
    return out[0], out[1], out[2], sources


GH = re.compile(r"https://github\.com/([^/]+/[^/]+)/(?:archive/(?:refs/tags/)?(.+?)\.tar\.gz"
                r"|releases/download/([^/]+)/)")


def norm(tag):
    return re.sub(r"^(v|version|release[-_]?|rel[-_]?)", "", tag.strip(), flags=re.I).replace("_", ".")


def latest_tags(repo):
    """The latest release's tag and the newest tag (either may be None; nightlies ignored)."""
    rel = get(f"/repos/{repo}/releases/latest")
    rel = rel.get("tag_name") if rel else None
    if rel and re.search(r"nightly", rel, re.I):
        rel = None
    tags = get(f"/repos/{repo}/tags?per_page=10") or []
    tags = [t["name"] for t in tags if not re.search(r"nightly", t["name"], re.I)]
    return rel, (tags[0] if tags else None)


def check(path, show_all):
    v = apkbuild_vars(path)
    if not v:
        return f"?  {path}: could not read"
    name, ver, pinned_branch, sources = v
    m = next((GH.match(s) for s in sources[:1] if GH.match(s)), None)
    if not m:
        host = re.sub(r"^https?://([^/]+).*", r"\1", sources[0]) if sources else "no source"
        return f"-  {name} {ver}: skipped ({host})" if show_all else None
    repo, ref = m.group(1), m.group(2) or m.group(3)
    ref = re.sub(r"^.*/", "", ref)
    info = get(f"/repos/{repo}")
    if info is None:
        return f"?  {name} {ver}: {repo} not found"
    if info.get("archived"):
        note = " (archived upstream)"
    else:
        note = ""
    repo = info["full_name"]
    branch = pinned_branch or info["default_branch"]
    release, tag = latest_tags(repo)
    newest = release or tag
    if re.fullmatch(r"[0-9a-f]{40}", ref):
        cmp = get(f"/repos/{repo}/compare/{ref}...{branch}")
        ahead = cmp.get("ahead_by", "?") if cmp else "?"
        date = (cmp or {}).get("commits", [{}])[-1].get("commit", {}).get("committer", {}).get(
            "date", "")[:10] if cmp and cmp.get("commits") else ""
        if ahead == 0 and not show_all:
            return None
        mark = "*" if ahead not in (0, "?") else " "
        return (f"{mark}  {name} {ver}: commit {ref[:8]}, {branch} is {ahead} commits ahead"
                + (f" (latest {date})" if date else "") + (f", newest tag {newest}" if newest else "")
                + note)
    if newest and norm(ref) not in {norm(t) for t in (release, tag) if t}:
        both = f"latest release {release}, newest tag {tag}" if release and tag and release != tag \
            else f"newest {newest}"
        return f"*  {name} {ver}: tag {ref}, {both}{note}"
    return f"   {name} {ver}: tag {ref}, current{note}" if show_all else None


def main():
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--all", action="store_true", help="also list current and skipped packages")
    ap.add_argument("dirs", nargs="*", default=[os.path.join(NURA, d) for d in ("lv2", "pd", "engines")])
    args = ap.parse_args()
    if not os.environ.get("GITHUB_TOKEN"):
        print("note: no GITHUB_TOKEN, the API allows only 60 requests per hour", file=sys.stderr)
    for d in args.dirs:
        for path in sorted(glob.glob(os.path.join(d, "*", "APKBUILD"))):
            try:
                line = check(path, args.all)
            except urllib.error.HTTPError as e:
                line = f"?  {path}: GitHub API error {e.code} {e.reason}"
            if line:
                print(line, flush=True)


if __name__ == "__main__":
    main()
