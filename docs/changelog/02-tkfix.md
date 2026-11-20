# Changelog: 02-tkfix, Tk UI improvements

What strand 02 of `main` changes, newest entry first: improvements of the Tk UI that aren't the
toolkit abstraction; the strand applies directly on origin/tomita. Marker `strand/02-tkfix`; this
file is the strand's last commit (see [README.md](README.md)).

## 2026-11-20: rebased onto tomita 88635347: no conflicts; upstream 88635347 adds its own fader_horizontal check beside our has_mixer_widgets() guards in the Tk mixer, see rebase-onto-tomita-2026-11-20b.md

## 2026-11-20: the strand when the changelog started

18 commits on strand 01, written 2026-11-03 to 2026-11-05.

- **Fewer redraws:** the mixer skips strips without mixer widgets and doesn't rebuild unchanged
  layouts, the grid selector caches its icons, the title scroll timer runs only while shown, the
  touch keypad LEDs skip unchanged colours and update right after a screen change
  (`62f31620b`, `1b0bee3fc`, `1f1b0ad0f`, `aae2a9d3e`, `97ee57077`, `df36e7543`, `4fcdbaed8`,
  `d4ce65539`).
- **No flashing:** the panel colour behind screens, the main frame's gaps as divider lines, info
  icons blended onto their background (`33f3002bb`, `198056f35`, `ece832e2b`).
- **Chain control and screens:** no rebuild on CTRL for the shown screen, subscreens kept in the
  grid, chain options and routing in the control screen's list, no re-grid per selection
  (`3fdfd44eb`, `807939147`, `c2b7f00c8`, `657a0246e`).
- **Fixes:** the engine selector with a type without engines, the chain manager when a chain can't
  move, the top bar with a CPU load above 100 % (`204c4b350`, `17cfcc984`, `e0f5e5975`).
