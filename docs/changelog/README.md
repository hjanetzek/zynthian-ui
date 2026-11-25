# Strand changelogs

`main` is one linear series on origin/tomita, ordered in feature strands, each marked by a local
branch `strand/NN-name` ([rebasing-onto-upstream.md](../rebasing-onto-upstream.md), "Strands").
Each strand has a changelog here: what the strand changes for a reader, user-visible and
developer-visible, as dated entries, newest first.

| File | Strand |
|---|---|
| [01-upstream.md](01-upstream.md) | fixes for upstream (pull request zynthian/zynthian-ui#617) |
| [02-tkfix.md](02-tkfix.md) | Tk UI improvements |
| [03-port.md](03-port.md) | zynthian outside ZynthianOS: paths, desktop mode, PipeWire |
| [04-ctrldev.md](04-ctrldev.md) | controller drivers, incl. the DrivenByMoss drivers |
| [05-tkabs.md](05-tkabs.md) | toolkit-independent UI logic |
| [06-loadopt.md](06-loadopt.md) | load and start-up time |
| [07-qt.md](07-qt.md) | the Qt Quick UI |
| [08-dbm.md](08-dbm.md) | the DrivenByMoss drivers' grid and Qt parts |
| [09-devtools.md](09-devtools.md) | developer tools |
| [10-docs.md](10-docs.md) | shared docs and plans |

## One living commit per file

Each file is changed by exactly one commit, the strand's **changelog commit** (subject
`changelog: NN-name`). It is the strand's last commit, so the marker points at it, and it touches
only its file: it never conflicts with code, and a rebase with `--update-refs` keeps it last.
New entries are added by amending that commit, not by new commits.

Exception: strand 01 is offered upstream as it is, so its changelog commit isn't in strand 01: it
sits in strand 10, right below 10's own changelog commit (the pull request's description is the
upstream-facing summary). New commits for strand 10 go below both.

## Entries

```
## 2026-11-21: what changed, in a few words

- `0123abcd9` the commit's subject
- notes, and where relevant the doc to read: [qt-theming.md](../qt-theming.md)
```

- A heading per entry, `## YYYY-MM-DD: title`, newest first; several entries per day are fine.
- Commits as hashes **in backticks** (9 characters): the tools remap only those. Group by topic;
  a summary entry names the key commits, not every one.
- Entries reference commits of their own strand or below, never above (the remap runs at the
  changelog commit, when everything below it is final).
- Upstream commits (ancestors of origin/tomita) may be named too; they are never remapped.

## Tools

In zynthian-stuff `tools/history-reorder/` (not in this repository):

- `strand-place.sh [-m TITLE | -n] STRAND COMMIT...` moves commits from the top of main to the end
  of the strand, before its changelog commit, and adds an entry (today, TITLE or the first
  subject, one line per commit) to the strand's changelog. It remaps the hashes in every
  living commit it rewrites (the changelog commits and "docs: upstream candidates"), and checks
  that the tree changed only in `docs/changelog/` and `docs/upstream-candidates.md`.
  Edit the entry later by amending the changelog commit (`git rebase -i`, `edit` it, or a fixup).
- `strand-changelog.sh [-e STRAND=TITLE [-c COMMIT...]]...` after any other rewrite of main (an
  upstream rebase, a fixup, a reword): remaps the hashes in all changelog files and in
  `docs/upstream-candidates.md`, and adds entries.
- `changelog.py rehash [-v] FILE...` remaps the hashes in a working-tree file (e.g. while editing
  a changelog by hand); `changelog.py list` lists the changelog commits, `living` also the
  upstream-candidates commit.
- `strand-check.sh` checks that every strand except 01 ends with its changelog commit, that
  changelog commits touch only their file and that each file has exactly one commit.

The remap maps an old commit to the current one with the same author date, author email and
subject (rebases keep them), so it works for placements and upstream rebases alike.

`docs/upstream-candidates.md` (strand 10's "docs: upstream candidates", one living commit like a
changelog) gets the same remap, but for bare hex tokens: commit links (text and target),
backticked hashes and hashes in prose. It leaves alone upstream commits, links to other
repositories (zyncoder, jalv, nura-builds, ...), hashes that aren't commits of zynthian-ui, and
in prose hex without both a digit and a letter. This replaced the one-off `uc-rehash.py` (a CSV
map from the strand reorder), which is gone.
