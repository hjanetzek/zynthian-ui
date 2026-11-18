# Rebasing onto upstream (origin/tomita)

How to rebase `main` (the Qt port's branch) onto upstream zynthian-ui, and the checks after it. The
notes of each rebase go into their own file (`docs/rebase-onto-tomita-<date>.md`, with
`docs/upstream-tomita-changes-<date>.md` for what upstream changed).

## Procedure

1. `git fetch origin`; note the old base (`git merge-base main origin/tomita`) and the new one
   (`origin/tomita`). Check that every earlier rebase attempt's resolutions are in `main`. Work on a new branch in its own worktree, never on `main` directly; keep the
   pre-rebase state as a backup branch.
2. `git rebase origin/tomita` (the repository has `rerere.enabled=true` and
   `merge.conflictStyle=zdiff3`). Record every conflict and its resolution in the dated notes.
3. **Check for upstream changes lost in moved code** (below). Git's conflicts don't cover this case.
4. Run the test suite in the test VM (`tools/test_vm.sh sync && tools/test_vm.sh run all`,
   docs/test-vm.md), never on the host. Then the Qt UI in a compare VM and this repository's Tk UI in
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
