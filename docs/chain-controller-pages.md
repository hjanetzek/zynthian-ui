# Chain controllers: positions and named pages

Status: 2026-11-25. The remote-control pages planned first (Bitwig-like
pages per chain) and upstream's **Chain Controllers** are one feature now: the chain
controllers are **named pages of 4 slots**, a slot any controller of the chain's processors or
empty.

## 1. Where it comes from

- **Upstream's Chain Controllers** (jofemodo, Vangelis, 2025-10-22, forum topic 10691): the
  "controller favorites" of a chain, toggled in the controller options ("☐/☒ Chain Controller"),
  shown first in chain control as "> CHAIN" / "Controllers n" pages of 4, saved in snapshots,
  used by controller drivers (APC40 user mode, Launchkey Mini mk3, APC Key25). A dense list in
  the order of adding; his TODO: reordering and page titles.
- **Bitwig's remote controls** (Track Remotes: pages of 8 controls, any parameter of the
  track): named pages, fixed positions, controllers step through them.

The result keeps upstream's API, snapshot key and page size (4, a zynthian page and v5's four
encoders) and adds Bitwig's positions and names.

## 2. The model

`zyngine/zynthian_zctrl_pages.py` (`ZctrlPages`, `ZctrlPage`; no UI), `chain.zctrl_pages`:

- **Pages**: a list of pages, each a `name` and **4 slots**; a slot is a reference
  `(processor id, symbol)` or empty. The mixer strip is a processor (`MI` / `MR`), so its
  controllers are slots like any other.
- **References are resolved when used** (`processor.controllers_dict[symbol]` of the chain's
  processor with that id). A reference whose processor or symbol is missing (yet) shows as an
  empty slot and is **kept**: it comes back with the controller (a Pure Data patch or LV2 preset
  that changes the controller set).
- **The flat view** `chain.zctrls` (a tuple): flat slot *n* is slot *n* % 4 of page *n* // 4,
  `None` for an empty slot, the trailing empty slots left out. Upstream's API on top:
  `toggle_zctrl`, `purge_zctrls`, `clean_zctrls`, `set_zctrls_state`, `get_zctrls_state`; the
  setter `chain.zctrls = [...]` makes pages of 4 in order.
- **`current`**: the target of quick assignments from a controller (the JAM), the page last
  selected on the screen or by a controller, by default the first. **`shown`**: the page the
  screen shows (None: another page); chain control's page list selects it when it is rebuilt.
- **Default names**: "Controllers *n*" (*n* its number), upstream's label; renamed pages keep
  their name.

### The toggle ("☐/☒ Chain Controller")

- **On**: the **first free slot from page 1** (not the current page); a slot with a missing
  reference isn't free; **all full** (or no pages): a **new page** "Controllers *n*" at the end,
  slot 1. No limit. A user who never touches pages gets upstream's behaviour: added in order.
- **Off**: removed from **all** pages, leaving a gap (the others keep their places, so a
  driver's knobs don't shift). An **empty last page that still has its default name** is deleted
  (repeatedly), so adding and removing one doesn't leave an empty page behind. Renamed or inner
  empty pages stay.
- ☒ shows when the controller is in any slot.

### Processors removed or replaced, reloads

- **Removed / replaced** (`remove_processor`): its references are cleared (`purge_zctrls`: a
  processor id may later be another processor's); the pages stay.
- **All processors removed** (`remove_all_processors`): the pages are cleared.
- **Reload** (`reload_processor`: removed and added with the same id): the pages are saved and
  restored around it.
- **Moved** within the chain: references are by id, nothing changes. **Chain removed**: its pages
  go with it.

## 3. Persistence

- **Snapshots** (and the last state): the chain state keeps upstream's
  `"zctrls": [[proc_id, "symbol"], ...]`, now the **filled, resolvable slots in page and slot
  order** (what an older zynthian reads: its Chain Controllers, without gaps and names), and adds
  `"zctrl_pages": [{"name": "Perform", "slots": [[proc_id, "symbol"], null, null, null]}, ...]`
  and `"zctrl_pages_current"` when there are pages (`zynthian_state_schema.py`).
- **Loading** (`chain_manager.set_state`): `zctrl_pages` when present, else `zctrls` as pages of
  4 in order ("Controllers 1", ...): an old snapshot's chain controllers look as before.
- **Round trip through stock zynthian**: it reads `zctrls`, ignores `zctrl_pages` and drops it
  when it saves; loaded here again, that snapshot's `zctrls` become pages again (names and gaps
  lost). The two can't disagree: whenever `zctrl_pages` is present it was written together with
  a matching `zctrls`.
- **Merge** ("Load Merge Chains"): both keys follow the new processor ids (`proc_map`);
  references to processors not in the snapshot are dropped. (The `zctrls` mapping is also an
  upstream fix: upstream left the old ids.)
- **ZS3**: not stored (structure, as upstream's chain controllers).
- **The 8-slot format** of the development versions is not migrated: slots 5-8 are dropped.

## 4. Chain control

The page list's first section is **CHAIN** (`zynthian_control_grid_data.chain_page_items`,
shared by the Qt screen, the grid and DrivenByMoss's adapter): one page list entry and one grid
page per chain controller page, its name the title, data `("chain", None, (page, zctrls))`.

- **v5**: an entry per page; the four encoders turn it. **grid4x6**: a page a row.
  **grid8x6**: two pages a row.
- **Colour**: the CHAIN section has a fixed colour of its own (`GridPage.kind` "chain",
  `color_index` -1; the theme token `controlGridChainColor`, `ThemeBase` `#d8d8d8`, the tk
  theme its text colour); the processors' sections count their colours from 0 without it, so a
  processor keeps its colour whether the chain has chain controllers or not.
- **Opening**: chain control opens on the first chain controller page when it shows another
  chain than before (a chain switch, after a special processor's screen). Coming back to the
  same chain it stays where it was (the page shown is kept on rebuilds).
- **Selection**: selecting a chain controller page changes no processor and sets `current` and
  `shown`; no widget on these pages. A controller on a chain page and on its processor's page
  shows in both cells.
- **Side chain**: one node "Chain Controllers" (Qt and Tk), selected on a chain page; a tap shows
  the first chain page.
- **Tk** (`zynthian_gui_control.fill_list`): "> CHAIN" with the pages by name (an empty slot is a
  blank controller); the toggle in the controller options. The slot picker and page manager are
  Qt-only so far.

## 5. Controller options and chain options (Qt)

`zynqt/screens/controller_options.py` (a long press on a controller or a grid cell, the bold push
of an encoder):

- **☐/☒ Chain Controller**: the toggle (§2).
- **Chain Controller slot...** ("Chain Controller slot: <page>, <n>" when placed) opens:
  - one entry per page: the **slot picker** (four entries "1 Cutoff", "2 –", ...): choosing a
    slot puts the controller there (on that page already: the two swap, a move);
  - **New page...**: a new page "Controllers *n*" and its slot picker;
  - **Remove from <page>, slot <n>** per place (an emptied default-named last page goes);
  - **Add page '<title>'**: a new page named after the processor page the long press was on,
    with its 4 controllers;
  - **Manage pages...**: the page manager.
- **The page manager**: one entry per page; each opens Rename (the on-screen keyboard), Move up,
  Move down, Clear, Delete (confirmed). Also in the **chain options** ("Chain controller
  pages...", `zynqt/screens/chain_options.py`) when the chain has pages.
- After a change chain control rebuilds its pages and `SS_GUI_CONTROL_GRID_ZCTRL_PAGES` (chain)
  tells consumers.

## 6. Controller drivers

- **Upstream's drivers** index `chain.zctrls`: knob *n* is flat slot *n* (page *n* // 4, slot
  *n* % 4). Launchkey Mini mk3 (pots 1-8, 9-16 with Shift: pages 1-2, 3-4), APC Key25 mk1 / mk2
  (knobs + scroll 0 / 8), APC40 mk2 user mode (`zctrls[user]` of each track's chain, user 0-7:
  pages 1-2). An empty slot does nothing (the Launchkey / Key25 let the CC through for MIDI
  learn; the APC40 binds nothing).
- **DrivenByMoss** (drivenbymoss-rust `zynthian-host-pages`, HOST_PAGE_PLAN §12.4): the host
  pages are `chain_pages`, so the CHAIN section is section 0 on the JAM, its colour through the
  existing colour fields (section, set, cell: `page_color`); nothing new on the wire.
  - **`HostPageCellAssign`** (0x8C0A, `hostpage cell/{cell}/assign/{epoch}`, int slot, agreed
    pending): the JAM's hold a pad of a cell row + touch strip *n*. Slot 0-7 is mapped onto pages
    of 4: **slot n -> slot n % 4 of page `current` + n // 4** (strips 1-4 the current page, 5-8
    the next one), the pages up to it created ("Controllers *n*"); an empty cell clears the slot
    (creates nothing); a controller already on that page moves (swaps). Slot -1 removes the
    cell's controller from all pages (an emptied default-named last page goes).
    `zctrl_assign(chain, zctrl, slot, page=None)` / `shared_selection.request_zctrl_assign`
    (applied in the GUI thread: `ChainControl.grid_zctrl_request`).
  - **Device pages** (`DeviceParameterPage`, the JAM's `<` `>` in CONTROL: pages of 8 = two
    controller screens): the adapter selects the processor's screen 2*p* as before and, while
    chain control is shown (`shared_selection.owner_shown()`), requests chain control's page of
    that screen (`request_page`, counting the chain controller pages before it), so the
    screen's selection follows.

## 7. Threads

Pages are changed in the GUI thread only; a driver asks through
`shared_selection.request_zctrl_assign`, which the screen posts to the GUI thread (applied, then
its pages rebuilt); without a screen (the Tk UI) it is applied at once. Readers (the adapter's
`chain_pages`, `chain.zctrls` from a driver's MIDI thread) read the lists without a lock: a page's
slots are replaced as a whole tuple, so a read during a change sees the old or the new page.

## 8. Tests

- `tests/unit/test_zctrl_pages.py`: the model (assign, move, flat assign, toggle, pruning, flat
  view, dense list, state).
- `tests/integration/test_state_manager.py`: snapshot round trip, merge (both keys), an old
  snapshot's `zctrls` as pages, `chain.zctrls` on a real chain.
- `tests/unit/test_control_grid_data.py`: the page list, colours, `zctrl_assign`'s row of 8.
- `tests/unit/test_qt_zctrl_pages.py`, `test_qt_control_grid_selection.py`: the Qt screen (the
  CHAIN section, opening, the toggle, the slot picker, the page manager, the chain options,
  driver requests).
- `tests/dbm/test_host_page.py` (the DrivenByMoss adapter): colours, assign, device pages.
- **Checked in the QEMU VM** (2026-11-25, 1280x800, tk theme, Noize Mak3r; the Tk VM stock
  zynthian-ui-tomita): an upstream-style snapshot (`zctrls` only, 5 controllers) loads as
  "Controllers 1" (4) and "Controllers 2" (1) and chain control opens on it; the Qt toggle fills
  the first free slot (page 2, slot 2); the page manager from the chain options moves a page;
  grid4x6, grid8x6 and v5 show the CHAIN section (its own colour in the grids); the snapshot
  saved again has both keys and stock tomita shows its 6 chain controllers ("Controllers 1",
  "Controllers 2"); "Load Merge Chains" gives the merged chain its chain controllers (new
  processor ids resolved); this repository's Tk UI lists the pages by name and its toggle fills
  the first free slot.

## 9. Names

The model was first named "remote-control pages"; since 2026-11-25 its names are the chain
controllers': `zyngine/zynthian_zctrl_pages.py` (`ZctrlPages`, `ZctrlPage`), `chain.zctrl_pages`,
the snapshot keys `"zctrl_pages"` and `"zctrl_pages_current"`, `zctrl_assign`,
`shared_selection.request_zctrl_assign`, `SS_GUI_CONTROL_GRID_ZCTRL_PAGES`. The earlier
`"remote_pages"` key is not read (it only existed in test snapshots of the development versions).

## 10. Open

- Tk: the slot picker and the page manager.
- "Opens on the first chain controller page" only on another chain; opening chain control again
  for the same chain keeps its page.
- ZS3 switching pages (Bitwig doesn't): not planned.
- "Default-named" is by position ("Controllers *n*" on page *n*): a default-named page moved to
  another place counts as named (the toggle doesn't delete it when it becomes empty).
