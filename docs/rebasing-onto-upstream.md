# Rebasing onto upstream (origin/tomita)

How to rebase `main` (the Qt port's branch) onto upstream zynthian-ui, and the checks after it. The
notes of each rebase go into their own file (`docs/rebase-onto-tomita-<date>.md`, with
`docs/upstream-tomita-changes-<date>.md` for what upstream changed).

## Procedure

1. `git fetch origin`; note the old base (`git merge-base main origin/tomita`) and the new one
   (`origin/tomita`). Check that every earlier rebase attempt's resolutions are in `main`. Work on a new branch in its own worktree, never on `main` directly; keep the
   pre-rebase state as a backup **tag** (`git tag backup/main-<date> main`): a backup *branch*
   at a commit of the rebased range would be moved along by `--update-refs` (see [Strands](#strands)).
2. `git rebase --update-refs origin/tomita` (the repository has `rerere.enabled=true` and
   `merge.conflictStyle=zdiff3`): the strand markers move along. Record every conflict and its
   resolution in the dated notes, by strand. Then check the stack with `strand-check.sh`.
   The changelog commits stay at the strands' ends (they touch only their files, a rebase keeps
   the order); their hashes are now stale. Bring them up to date and add an entry to each strand
   the rebase affected (conflicts, commits dropped because upstream took them):
   `strand-changelog.sh -e "strand/05-tkabs=rebased onto tomita <hash>: conflicts in …, see
   rebase-onto-tomita-<date>.md" -e …` (see [Changelogs](#changelogs)). Unmapped hashes it
   reports are commits that were dropped: say so in the entry.
3. **Check for upstream changes lost in moved code** (below). Git's conflicts don't cover this case.
4. Run the test suite in the test VM (`tools/test_vm.sh sync && tools/test_vm.sh run all`,
   docs/test-vm.md), never on the host; also at the top of each strand that had conflicts. Then the Qt UI in a compare VM and this repository's Tk UI in
   the Tk VM (docs/qemu-testing.md).
5. The user decides about replacing `main` (force push); no push while CI runs.

## Upstream changes lost in moved code

Many of our commits move logic out of a Tk screen or widget (`zyngui/zynthian_gui_*.py`,
`zyngui/zynthian_widget_*.py`) into a toolkit-independent module that both UIs use. If upstream changes
the Tk code that such a commit moves, the rebase usually applies cleanly: our commit deletes the code
from the Tk file, upstream's change goes with it, and the module keeps the old version. Nothing
conflicts, the upstream change is just gone, in both UIs.

This happened in the rebase of about 2026-11-07 that main came from (recorded in
`docs/rebase-onto-tomita-2026-11-15.md`, "Upstream changes lost in moved code"): upstream's envelope
curves (efb40f48) and the routing to all-channel MIDI chains (be13d828) were lost that way. An
earlier attempt had ported both, but main was rebased separately. So also: when there are several
rebase attempts, carry the resolutions over (or build main from the documented one).

The check, after every rebase:

1. List the upstream commits in `OLD_BASE..NEW_BASE` that touch files our series changes:
   `git log --oneline OLD_BASE..NEW_BASE -- $(git diff --name-only NEW_BASE main)`.
2. For each one, check whether our series deletes or moves the lines it added or changed. The report
   tool does this: `refactor_report.py --lost-upstream OLD_BASE NEW_BASE main` (zynthian-stuff
   `tools/refactor-report/`) lists, for each upstream hunk in code that our commits remove, whether its
   added lines (normalised) reappear anywhere in the rebased tree.
3. Port each lost change into the module that now holds the code, with a regression test, and note
   it in the dated rebase notes.

## Strands

`main` is one linear series on top of `origin/tomita`, ordered in feature strands (since
2026-11-19). Each strand's last commit is its changelog commit (since 2026-11-20, see
[Changelogs](#changelogs)) and is marked by a local branch:

| Marker | What |
|---|---|
| `strand/01-upstream` | self-contained fixes for upstream (zynmixer, zynseq, snapshots, engines, xfail drops); applies directly on tomita |
| `strand/02-tkfix` | Tk UI improvements that aren't abstraction; applies directly on tomita |
| `strand/03-port` | the non-ZynthianOS port: `zynthian_paths`, desktop mode, `desktop/`, PipeWire, read-only data, OSC status query |
| `strand/04-ctrldev` | controller drivers: user driver folders, `ZYNTHIAN_CTRLDEV_PATH`, HID drivers |
| `strand/05-tkabs` | the toolkit-independent UI-logic modules (`zyngui/zynthian_*_data.py`, …) and the Tk screens using them |
| `strand/06-loadopt` | load and start-up time: jalv -B, lazy imports and lilv, LV2 caches, stop timeouts, engine output drain |
| `strand/07-qt` | the Qt Quick UI: `zynqt/`, `zynthian_qt_main.py`, Qt tests, the Qt docs (`qt-*.md`, `qt-port-plan.md`) |
| (`strand/08-nura`) | no marker: the Nura packaging (the `nura/` recipes, deploy, seed, `docs/nura-display.md`) moved to nura-builds with its history; the number stays free |
| `strand/09-devtools` | `tools/` (test VM, QEMU, sync, profiling, screenshots) and its docs (qemu-testing, test-vm, performance-measurement) |
| `strand/10-docs` | the shared logs and plans: upstream-candidates, rebase notes, architecture, plans |

Which strand a commit belongs to: by file first (`zynqt/` → qt, `tools/` → devtools, `desktop/` →
port, strand-specific docs with their strand, other `docs/` → docs); code by what it does. A commit
touching several strands' files is split by file. Nura packaging (recipes, sessions, `deploy.sh`)
goes to nura-builds, not here. Dependencies run upwards only: tkabs needs port, loadopt needs port
and tkabs, qt needs everything below it.

Rules:

- The markers stay local (or are pushed only for review links) and are **never checked out** in a
  worktree: `git rebase --update-refs` doesn't move branches that are checked out elsewhere.
- Keep **exactly one set** of markers and no other branch at a commit inside `origin/tomita..main`:
  `--update-refs` moves every local branch that points into the rebased range (backup branches,
  copies of the markers). Use tags for backups.
- New work is committed on top of `main` as usual and moved into its strand when a topic is done
  (batch it, e.g. before a push), not per commit. Moving rewrites main: the force-push rules apply
  (no push while CI runs; other worktrees on main rebase afterwards).

The helper scripts are in zynthian-stuff `tools/history-reorder/` (not in this repository):

- `strand-place.sh [-m TITLE | -n] STRAND COMMIT...`, run on `main`: moves the commits (above
  STRAND) to the end of the strand, before its changelog commit, with a scripted `git rebase -i
  --update-refs` (no editor), and adds an entry for them to the strand's changelog (`-m`: its
  title, default the first commit's subject; `-n`: none). Every changelog commit the rebase
  rewrites gets its hashes remapped. It checks that the tree is unchanged outside
  `docs/changelog/` afterwards (a pure reorder: main's CI result stays the same). Conflicts show
  up at the moved commit as in any rebase. Example:
  `strand-place.sh -m "jalv: faster preset loads" strand/06-loadopt HEAD~1 HEAD`.
- `strand-changelog.sh [-e STRAND=TITLE [-c COMMIT...]]...`: remaps the changelog hashes after
  any other rewrite (upstream rebase, fixup, reword) and adds entries.
- `strand-check.sh BASE TOP STRAND...`: no merge commits, no empty commits, every marker an
  ancestor of the next, every strand but 01 ending with its changelog commit, changelog commits
  touching only their file, commits per strand:
  `strand-check.sh origin/tomita main $(git for-each-ref --format='%(refname:short)' 'refs/heads/strand/*' | sort)`.

Without the scripts: `git rebase -i --update-refs strand/06-loadopt~1` and move the `pick` lines
of the new commits up before the strand's changelog commit (`changelog: 06-loadopt`), then amend
the changelog commit with an entry (`edit` it in the same todo), and update hashes in the
changelog commits above (`changelog.py rehash`).

### Changelogs

Each strand has a living changelog, `docs/changelog/<NN-name>.md` ([README](changelog/README.md)):
dated entries, newest first, with the commits as hashes in backticks and the docs to read. It is
one commit, the strand's last, touching only its file; entries are added by amending it. Strand
01 (offered upstream as is) has no changelog commit of its own: `01-upstream.md`'s commit sits in
strand 10, below 10's own changelog commit.

- Placing commits: `strand-place.sh` adds the entry; reword it later by amending the changelog
  commit (e.g. `git commit --fixup=amend:<changelog commit>` on top and `git rebase -i
  --autosquash --update-refs <changelog commit>~1`, then `strand-changelog.sh` for the hashes).
- Hashes go stale whenever main is rewritten below a changelog commit; `strand-place.sh` and
  `strand-changelog.sh` remap them (an old commit maps to the one with the same author date,
  author email and subject). Entries name commits of their strand or below only.
- After an upstream rebase: `strand-changelog.sh` with an entry per affected strand (step 2 of
  the procedure).

Other tasks:

- **Test a strand:** `git worktree add --detach ../zr-06 strand/06-loadopt`, then
  `tools/test_vm.sh sync ../zr-06 && (cd ../zr-06 && <main>/tools/test_vm.sh run default)`
  (the VM keys trees by directory name; the worktree must sit next to `zyncoder` and
  `zynthian-data`). Test the tops of the strands that changed.
- **Offer a strand upstream:** upstream, tkfix and port apply directly on tomita:
  `git format-patch origin/tomita..strand/01-upstream`, or for one strand alone on a copy:
  `git switch -c offer/tkfix strand/02-tkfix~1 && git rebase --onto origin/tomita strand/01-upstream`
  (`~1`: without the strand's changelog commit; never rebase a marker itself; the copy leaves
  main's range with the rebase). The curated
  `tk-ui-abstraction` branch stays the upstream offer of tkabs.
- **When upstream takes a commit:** the next `git rebase --update-refs origin/tomita` drops it
  (already upstream) or conflicts at the bottom; a strand upstream took whole keeps only its
  changelog commit: give it a last entry, then drop the commit and delete the marker (or keep the
  file, moved into 10-docs' changelog block like 01's).
