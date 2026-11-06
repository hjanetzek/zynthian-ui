#!/usr/bin/env python3
"""APKBUILD sources for a GitHub project with git submodules.

GitHub's archives don't contain submodules. This resolves a ref of a GitHub repository and its
submodules (recursively, GitHub-hosted only) to commits, and prints the variables, `source`
entries and `prepare()` lines that put each submodule archive in place:

    nura/tools/gh-submodule-sources.py jatinchowdhury18/KlonCentaur v1.4.0

Uses the GitHub API without a token (60 requests per hour); set GITHUB_TOKEN for more.
"""

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"


def get(path):
    req = urllib.request.Request(API + path, headers={"Accept": "application/vnd.github+json",
                                                      "User-Agent": "gh-submodule-sources"})
    if os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", "Bearer " + os.environ["GITHUB_TOKEN"])
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def gitmodules(repo, sha):
    try:
        data = get(f"/repos/{repo}/contents/.gitmodules?ref={sha}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []
        raise
    text = base64.b64decode(data["content"]).decode()
    mods, cur = [], None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("[submodule"):
            cur = {}
            mods.append(cur)
        elif cur is not None and "=" in line:
            k, v = (s.strip() for s in line.split("=", 1))
            cur[k] = v
    return mods


def gh_repo(url):
    m = re.match(r"(?:https?://|git@)github\.com[/:]([^/]+/[^/]+?)(?:\.git)?/?$", url)
    return m.group(1) if m else None


def walk(repo, sha, prefix, out, depth=0):
    for mod in gitmodules(repo, sha):
        path = mod["path"]
        sub = gh_repo(mod.get("url", ""))
        try:
            entry = get(f"/repos/{repo}/contents/{path}?ref={sha}")
        except urllib.error.HTTPError:
            print(f"# WARNING: {prefix}{path}: not found at {sha}", file=sys.stderr)
            continue
        subsha = entry.get("sha") if entry.get("type") == "submodule" else None
        if not sub or not subsha:
            print(f"# WARNING: {prefix}{path}: not a GitHub submodule ({mod.get('url')})",
                  file=sys.stderr)
            continue
        out.append((prefix + path, sub, subsha, depth))
        walk(sub, subsha, prefix + path + "/", out, depth + 1)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    repo, ref = sys.argv[1:]
    sha = get(f"/repos/{repo}/commits/{ref}")["sha"]
    mods = []
    walk(repo, sha, "", mods)
    name = repo.split("/")[1]
    print(f"_commit={sha}")
    for path, sub, subsha, _ in mods:
        print(f"_{var(path)}={subsha}")
    print(f'source="$pkgname-$_commit.tar.gz::https://github.com/{repo}/archive/$_commit.tar.gz')
    for path, sub, subsha, _ in mods:
        print(f'\t{var(path)}-${{_{var(path)}}}.tar.gz::https://github.com/{sub}/archive/${{_{var(path)}}}.tar.gz')
    print('\t"')
    print(f'builddir="$srcdir/{name}-$_commit"')
    print()
    print("prepare() {")
    print("\t# git submodules (outer ones first)")
    for path, sub, subsha, _ in mods:
        print(f'\trm -rf {path} && mv "$srcdir"/{sub.split("/")[1]}-${{_{var(path)}}} {path}')
    print("\tdefault_prepare")
    print("}")


def var(path):
    return re.sub(r"[^A-Za-z0-9]", "_", path.split("/")[-1]).lower() if path.count("/") == 0 \
        else re.sub(r"[^A-Za-z0-9]", "_", path).lower()


if __name__ == "__main__":
    main()
