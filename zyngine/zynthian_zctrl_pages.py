# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian Engine
#
# A chain's controller pages: the Chain Controllers with positions and named pages (pages of 4
# slots, each a reference to any controller of the chain's processors).
# docs/chain-controller-pages.md
#
# Copyright (C) 2026 Hannes Janetzek
#
# ******************************************************************************
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ******************************************************************************

"""A chain's controller pages, the model of its Chain Controllers: user-curated, named pages of
SLOTS (4) controllers, shown first in chain control. No UI, no Qt.

- A slot is a reference (processor id, symbol) or None. References are resolved when used
  (resolve / zctrls / flat): a reference whose processor or symbol is missing is kept and shows
  as an empty slot until the controller is back (a preset that changes the controllers).
- The flat slot n is slot n % SLOTS of page n // SLOTS: chain.zctrls (flat()) is this view,
  so the controller drivers' knob n is flat slot n.
- toggle (the controller options' "Chain Controller"): adds to the first free slot from page 1
  (a new page when all are full), removes from all pages (the gap stays; an empty default-named
  last page goes).
- current: the page quick assignments go to (the last selected page, default 0); shown: the
  page the screen shows, None when it shows another page.
- Changed in the GUI thread only; readers on other threads see whole pages (a page's slots are
  replaced as a whole tuple).
"""

import logging

SLOTS = 4
DEFAULT_NAME = "Controllers"


class ZctrlPage:
    """A page: its name and SLOTS references ((processor id, symbol) or None)"""

    def __init__(self, name, slots=()):
        self.name = str(name)
        slots = list(slots)[:SLOTS]
        self.slots = tuple(slots + [None] * (SLOTS - len(slots)))

    def set_slot(self, slot, ref):
        slots = list(self.slots)
        slots[slot] = ref
        self.slots = tuple(slots)

    def is_empty(self):
        return all(r is None for r in self.slots)

    def __repr__(self):
        return f"ZctrlPage({self.name!r}, {self.slots})"


def zctrl_ref(zctrl):
    """A controller's reference (processor id, symbol), None if it has no processor"""
    proc = getattr(zctrl, "processor", None)
    if zctrl is None or proc is None or getattr(proc, "id", None) is None:
        return None
    return (proc.id, zctrl.symbol)


def default_page_name(index):
    """The name of page `index` (0-based) that wasn't named: "Controllers n" (upstream's label)"""
    return f"{DEFAULT_NAME} {index + 1}"


class ZctrlPages:
    """The controller pages of one chain (chain.zctrl_pages)"""

    def __init__(self, chain=None):
        self.chain = chain
        self.pages = []
        self.current = 0
        self.shown = None

    # Resolving references

    def _processors(self):
        chain = self.chain
        if chain is None:
            return {}
        try:
            return {p.id: p for p in chain.get_processors()}
        except Exception:
            return {}

    def resolve(self, ref, procs=None):
        """The controller of a reference, None if it isn't there"""
        if ref is None:
            return None
        procs = self._processors() if procs is None else procs
        proc = procs.get(ref[0])
        if proc is None:
            return None
        try:
            return proc.controllers_dict.get(ref[1])
        except Exception:
            return None

    def zctrls(self, page):
        """The SLOTS controllers of a page (None: empty or missing)"""
        if not 0 <= page < len(self.pages):
            return [None] * SLOTS
        procs = self._processors()
        return [self.resolve(ref, procs) for ref in self.pages[page].slots]

    def flat(self):
        """The controllers of all pages in order, flat slot n = slot n % SLOTS of page
        n // SLOTS (None: empty or missing), without the trailing empty ones: chain.zctrls"""
        procs = self._processors()
        out = [self.resolve(ref, procs) for page in list(self.pages) for ref in page.slots]
        while out and out[-1] is None:
            out.pop()
        return tuple(out)

    def find(self, zctrl):
        """The places (page, slot) of a controller"""
        ref = zctrl_ref(zctrl)
        if ref is None:
            return []
        return [(p, s) for p, page in enumerate(self.pages) for s, r in enumerate(page.slots) if r == ref]

    def contains(self, zctrl):
        return bool(self.find(zctrl))

    # Pages

    def default_name(self):
        """The name of a new page: "Controllers n" (n: its number), the next one not taken"""
        names = {p.name for p in self.pages}
        n = len(self.pages)
        while default_page_name(n) in names:
            n += 1
        return default_page_name(n)

    def add_page(self, name=None, slots=()):
        """A new page at the end; its index"""
        self.pages.append(ZctrlPage(name or self.default_name(), slots))
        return len(self.pages) - 1

    def rename_page(self, page, name):
        if 0 <= page < len(self.pages) and name:
            self.pages[page].name = str(name)
            return True
        return False

    def delete_page(self, page):
        if not 0 <= page < len(self.pages):
            return False
        self.pages.pop(page)
        if self.current > page or self.current >= len(self.pages):
            self.current = max(0, self.current - 1)
        self.shown = None
        return True

    def move_page(self, page, step):
        """Move a page by step places (clamped); its new index"""
        if not 0 <= page < len(self.pages):
            return page
        to = max(0, min(len(self.pages) - 1, page + step))
        if to != page:
            moved = self.pages.pop(page)
            self.pages.insert(to, moved)
            if self.current == page:
                self.current = to
            elif page < self.current <= to:
                self.current -= 1
            elif to <= self.current < page:
                self.current += 1
            self.shown = None
        return to

    def clear_page(self, page):
        if 0 <= page < len(self.pages):
            self.pages[page].slots = (None,) * SLOTS
            return True
        return False

    def clear(self):
        """No pages (the chain's processors all removed)"""
        self.pages = []
        self.current = 0
        self.shown = None

    def prune(self):
        """Delete the empty last pages that still have their default name (pages the toggle
        created, emptied again); True if one went"""
        pruned = False
        while self.pages and self.pages[-1].is_empty() \
                and self.pages[-1].name == default_page_name(len(self.pages) - 1):
            self.delete_page(len(self.pages) - 1)
            pruned = True
        return pruned

    # Slots

    def assign(self, zctrl, page, slot):
        """Put a controller (None: clear) into a slot of a page; page == len(pages) (or no pages):
        a new page. A controller already on that page swaps with the slot's (a move). Returns the
        page's index, -1 if nothing was done"""
        if not 0 <= slot < SLOTS:
            return -1
        ref = zctrl_ref(zctrl)
        if zctrl is not None and ref is None:
            return -1
        if page == len(self.pages) or page < 0 and not self.pages:
            page = self.add_page()
        if not 0 <= page < len(self.pages):
            return -1
        p = self.pages[page]
        slots = list(p.slots)
        if ref is not None and ref in slots:
            old = slots.index(ref)
            slots[old] = slots[slot]
        slots[slot] = ref
        p.slots = tuple(slots)
        return page

    def assign_flat(self, zctrl, n, base=0):
        """Put a controller (None: clear) into flat slot n counted from page `base`: slot
        n % SLOTS of page base + n // SLOTS, the pages up to it created (not for a clear). The
        JAM's row of 8 strips: slots 0-3 the current page, 4-7 the next one. Returns the page's
        index, -1 if nothing was done"""
        if n < 0 or base < 0:
            return -1
        page, slot = base + n // SLOTS, n % SLOTS
        if page >= len(self.pages):
            if zctrl is None or zctrl_ref(zctrl) is None:
                return -1
            while len(self.pages) < page:
                self.add_page()
        return self.assign(zctrl, page, slot)

    def add_next(self, zctrl):
        """Add a controller to the first free slot from page 1 (a slot holding a missing
        reference isn't free); all full: a new page at the end. (page, slot), or its first place
        if it already is on a page; None if it has no processor"""
        ref = zctrl_ref(zctrl)
        if ref is None:
            return None
        places = self.find(zctrl)
        if places:
            return places[0]
        for p, page in enumerate(self.pages):
            for s, r in enumerate(page.slots):
                if r is None:
                    page.set_slot(s, ref)
                    return p, s
        p = self.add_page(slots=[ref])
        return p, 0

    def remove(self, zctrl, page=None, prune=False):
        """Remove a controller from a page (None: from all); prune: then delete the empty
        default-named last pages. True if it was there"""
        ref = zctrl_ref(zctrl)
        found = False
        for i, p in enumerate(self.pages):
            if ref is None or page is not None and i != page or ref not in p.slots:
                continue
            p.slots = tuple(None if r == ref else r for r in p.slots)
            found = True
        if found and prune:
            self.prune()
        return found

    def toggle(self, zctrl):
        """The controller options' "Chain Controller": on a page, removed from all (pruned);
        else added to the next free slot. True if it was added"""
        if self.contains(zctrl):
            self.remove(zctrl, prune=True)
            return False
        return self.add_next(zctrl) is not None

    def purge(self):
        """Clear the references to processors that aren't in the chain any more (a processor
        removed or replaced: its id may be another processor's later)"""
        procs = self._processors()
        for p in self.pages:
            if any(r is not None and r[0] not in procs for r in p.slots):
                p.slots = tuple(r if r is None or r[0] in procs else None for r in p.slots)

    def current_page(self):
        """The index of the current page (quick assignments), -1 without pages"""
        if not self.pages:
            return -1
        return self.current if 0 <= self.current < len(self.pages) else 0

    def set_shown(self, page):
        """The screen shows a page (None: another page)"""
        if page is None or not 0 <= page < len(self.pages):
            self.shown = None
            return
        self.shown = page
        self.current = page

    # Upstream's chain controllers (the chain state's "zctrls": a dense list)

    def dense_refs(self):
        """The references of the filled slots that resolve, in page and slot order, as lists:
        upstream's "zctrls" (what an older zynthian reads)"""
        procs = self._processors()
        return [list(r) for page in self.pages for r in page.slots
                if r is not None and self.resolve(r, procs) is not None]

    def from_dense(self, refs):
        """Pages of SLOTS from a dense list of references ((processor id, symbol)), named
        "Controllers n": upstream's chain controllers"""
        self.clear()
        slots = []
        for r in refs or []:
            try:
                slots.append((int(r[0]), str(r[1])))
            except Exception:
                logging.error(f"Can't restore chain zctrl from state => {r}")
        for i in range(0, len(slots), SLOTS):
            self.add_page(slots=slots[i:i + SLOTS])

    # State (snapshots: the chain's state)

    def get_state(self):
        return [{"name": p.name, "slots": [list(r) if r is not None else None for r in p.slots]}
                for p in self.pages]

    def set_state(self, state, current=0):
        self.pages = []
        self.shown = None
        for page in state or []:
            try:
                slots = [tuple(r) if r else None for r in page.get("slots", [])]
                slots = [(int(r[0]), str(r[1])) if r is not None else None for r in slots]
                self.pages.append(ZctrlPage(page.get("name") or self.default_name(), slots))
            except Exception as e:
                logging.error(f"Can't restore chain controller page from state => {page}: {e}")
        self.current = current if isinstance(current, int) and 0 <= current < len(self.pages) else 0
