# Changelog: 02-tkfix, Tk UI improvements

What strand 02 of `main` changes, newest entry first: improvements of the Tk UI that aren't the
toolkit abstraction; the strand applies directly on origin/tomita. Marker `strand/02-tkfix`; this
file is the strand's last commit (see [README.md](README.md)).

## 2026-11-28: rebased onto tomita 046817e4: one conflict in the mixer commit (upstream's try/except toggle guard 85cbbf2f; our has_mixer_widgets() guard kept); see rebase-onto-tomita-2026-11-28.md

## 2026-11-26: rebased onto tomita e2f423d33: no conflicts; see rebase-onto-tomita-2026-11-26.md

## 2026-11-20: rebased onto tomita 88635347: no conflicts; upstream 88635347 adds its own fader_horizontal check beside our has_mixer_widgets() guards in the Tk mixer, see rebase-onto-tomita-2026-11-20b.md

## 2026-11-20: the strand when the changelog started

18 commits on strand 01, written 2026-11-03 to 2026-11-05.

- **Fewer redraws:** the mixer skips strips without mixer widgets and doesn't rebuild unchanged
  layouts, the grid selector caches its icons, the title scroll timer runs only while shown, the
  touch keypad LEDs skip unchanged colours and update right after a screen change
  (`f0a2ed9c1`, `d7877fbdb`, `4c4e7830f`, `4208b8520`, `7341c9a0d`, `4451f94f7`, `15c06cfdf`,
  `ba90cc800`).
- **No flashing:** the panel colour behind screens, the main frame's gaps as divider lines, info
  icons blended onto their background (`a298768ef`, `a29be5246`, `adfabf722`).
- **Chain control and screens:** no rebuild on CTRL for the shown screen, subscreens kept in the
  grid, chain options and routing in the control screen's list, no re-grid per selection
  (`b195a9bba`, `1e862afd7`, `9507a903b`, `79d8fafee`).
- **Fixes:** the engine selector with a type without engines, the chain manager when a chain can't
  move, the top bar with a CPU load above 100 % (`5a89ef160`, `27ecd10db`, `8cd0b4b45`).
