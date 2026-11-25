"""Options of a controller in the chain control screen (zynthian_gui_control.controller_options, a
long press on a controller): chain controller (the toggle: the next free slot; the slot picker:
a page's slot, remove, the page manager: docs/chain-controller-pages.md), MIDI learn (chain or global), the learned
binding's CC mode and value range, momentary/debounce for toggles, the step sequencer's
automation, the input devices of the learned binding, unlearn.

"""

import logging

import zynautoconnect
from zyngine.zynthian_zctrl_pages import SLOTS, zctrl_ref
from zyngui import zynthian_control_grid_data as gd
from zyngui.zynthian_midi_learn_data import (CC_MODES, MIDI_LEARNING_CHAIN, MIDI_LEARNING_GLOBAL, automate_cc,
                                             cc_mode_label, set_cc_mode, unlearn_label)


def show_controller_options(cc, i, selected=0, select_text=None):
    """cc: the ChainControl; i: controller slot; selected: the entry selected first, or the first
    one containing select_text"""
    zctrl = cc.controllers[i].zctrl
    if zctrl is None:
        return
    ui = cc.ui
    cm = cc.chain_manager
    cc.exit_midi_learn()
    if cc._is_key_range():
        # Note range page (zynthian_gui_midi_key_range): its values are learned from notes
        ui.show_options("Note Range & Transpose", [
            ("Learn note range: play the lowest and the highest note", cc.toggle_midi_learn, None, None)])
        return

    def again(index):
        return lambda: show_controller_options(cc, i, index)

    opts = []
    chain = None if cc.special_processor else cm.get_active_chain()
    if chain is not None:
        def toggle_chain_ctrl():
            # The first free slot from page 1 (a new page when all are full), or off everywhere
            chain.toggle_zctrl(zctrl)
            cc.rebuild()
            gd.zctrl_pages_changed(chain)
            again(0)()
        zpages = gd.chain_zctrl_pages(chain)
        on = zpages.contains(zctrl) if zpages is not None else zctrl in chain.zctrls
        opts.append((f"{'☒' if on else '☐'} Chain Controller", toggle_chain_ctrl, None, None))
        if zpages is not None and zctrl.processor is not None:
            opts.append((zctrl_slot_label(zpages, zctrl), lambda: show_zctrl_slot_options(cc, chain, zctrl), None, None))

    if zctrl.is_path:
        def clear():
            zctrl.set_value("")
            cc.controllers[i].refresh(True)
        opts.append(("Clear", clear, None, None))
        ui.show_options(f"Control options: {zctrl.name}", opts, selected)
        return

    if not zctrl.is_toggle:
        # X-Y touchpad axes (state_manager.zctrl_x / zctrl_y; an axis takes one controller)
        sm = ui.state_manager
        if sm.zctrl_x and sm.zctrl_y:
            opts.append(("Show touchpad", lambda: ui.show_screen("control_xy"), None, None))
        for axis in ("x", "y"):
            current = getattr(sm, f"zctrl_{axis}")
            other = "y" if axis == "x" else "x"

            def toggle_axis(axis=axis, other=other):
                setattr(sm, f"zctrl_{axis}", None if getattr(sm, f"zctrl_{axis}") == zctrl else zctrl)
                if getattr(sm, f"zctrl_{other}") == zctrl:
                    setattr(sm, f"zctrl_{other}", None)
                cc.refresh_bindings()
                show_controller_options(cc, i, select_text=f"{axis.upper()}-axis")
            info = f" => {current.name}" if current else ""
            opts.append((f"{'☒' if current == zctrl else '☐'} {axis.upper()}-axis{info}", toggle_axis, None, None))

    ml = cm.get_midi_binding_from_zctrl(zctrl, filter_automate=False)
    opts.append(("MIDI learn", None, None, None))
    automate_index = len(opts)
    opts.append((f"{'☒' if automate_cc(cm, zctrl) is not None else '☐'} Automate",
                 lambda: _toggle_automate(cc, zctrl, again(automate_index)), None, None))
    if zctrl.is_toggle:
        def flip(attr, index):
            def run():
                setattr(zctrl, attr, 0 if getattr(zctrl, attr) else 1)
                again(index)()
            return run
        opts.append((f"{'☒' if zctrl.midi_cc_momentary_switch else '☐'} Momentary => Latch",
                     flip("midi_cc_momentary_switch", len(opts)), None, None))
        opts.append((f"{'☒' if zctrl.midi_cc_debounce else '☐'} Debounce",
                     flip("midi_cc_debounce", len(opts)), None, None))
    elif ml:
        index = len(opts)

        def pick_mode():
            def choose(mode, reverse):
                set_cc_mode(zctrl, mode, reverse)
                again(index)()
            current = next((k for k, (label, _, _, _) in enumerate(CC_MODES) if label == cc_mode_label(zctrl)), 0)
            ui.show_options("CC mode", [(label, lambda m=mode, r=rev: choose(m, r), info, None)
                                        for label, mode, rev, info in CC_MODES], current)
        opts.append((cc_mode_label(zctrl), pick_mode, None, None))
        if zctrl.midi_cc_mode <= 0:
            opts.append(("CC Value Range", lambda: _edit_cc_range(cc, i, zctrl, again(index + 1)), None, None))
    if zctrl.processor:
        opts.append(("Chain learn...", lambda: cc.midi_learn(i, MIDI_LEARNING_CHAIN), None, None))
    opts.append(("Global learn...", lambda: cc.midi_learn(i, MIDI_LEARNING_GLOBAL), None, None))

    if ml:
        inputs_index = len(opts)
        opts.append(("Learned MIDI Inputs", lambda: _learned_inputs(cc, zctrl, again(inputs_index)), None, None))

    if ml:
        def unlearn():
            if zctrl.processor is not None:
                cm.clear_midi_binding(zctrl.processor, zctrl.symbol)
            cc.refresh_bindings()
        opts.append((unlearn_label(cm, ml), unlearn, None, None))
    opts.append(("Unlearn all controls", cc.midi_unlearn_action, None, None))
    if select_text:
        selected = next((k for k, o in enumerate(opts) if select_text in o[0]), selected)
    ui.show_options(f"Control options: {zctrl.name}", opts, selected)


def _toggle_automate(cc, zctrl, done):
    """Toggle the step sequencer's automation of the controller, confirming the removal of the
    automation from the patterns that have it (zynthian_gui_control.controller_options_cb)"""
    cm = cc.chain_manager
    chan = zctrl.processor.midi_chan if zctrl.processor else None
    acc = automate_cc(cm, zctrl)
    if acc is not None and chan is not None and chan < 16:
        zynseq = cc.ui.state_manager.zynseq
        patterns = zynseq.get_automated_patterns(acc, chan)
        if patterns:
            def disable():
                cm.toggle_automate_zctrl(zctrl)
                for pattern in patterns:
                    zynseq.libseq.selectPattern(pattern)
                    zynseq.libseq.clearControl(acc)
                cc.refresh_bindings()
                done()
            cc.ui.confirm(f"Disable and remove automation from {len(patterns)} patterns?", disable)
            return
    cm.toggle_automate_zctrl(zctrl)
    cc.refresh_bindings()
    done()


def _learned_inputs(cc, zctrl, done):
    """The MIDI input devices of the controller's learned binding, each one toggled
    (zynthian_gui_control "Learned MIDI Inputs")"""
    cm = cc.chain_manager
    result = cm.get_midi_binding_from_zctrl(zctrl, filter_automate=False)
    if not result:
        done()
        return
    bound_devices = []
    for key, kind in result:
        midi_cc, chan, zmip, chain_id = cm.unpack_midi_bind_key(key)
        bound_devices.append(zmip)
    opts = []
    for izmip, port in enumerate(zynautoconnect.devices_in):
        try:
            if port and port.name not in ("zynseq:output", "CV/Gate"):
                def toggle(izmip=izmip):
                    cm.toggle_midi_binding(zctrl, midi_cc, chan, izmip, chain_id)
                    cc.refresh_bindings()
                    _learned_inputs(cc, zctrl, done)
                opts.append((f"{'☒' if izmip in bound_devices else '☐'} {port.aliases[1]}", toggle, None, None))
        except Exception as e:
            logging.warning(e)
    cc.ui.show_options(f"MIDI devices bound to CC {midi_cc}", opts, 0)


def _edit_cc_range(cc, i, zctrl, done):
    """The controller values at CC 0 and CC 127 (zynthian_gui_midi_cc_range)"""
    integer = zctrl.is_integer
    step = 1 if integer else (zctrl.value_range or 1) / 100
    decimals = 0 if integer else 2

    def set_val2(v):
        zctrl.midi_cc_val2 = int(v) if integer else float(v)
        zctrl._configure()
        done()

    def set_val1(v):
        zctrl.midi_cc_val1 = int(v) if integer else float(v)
        zctrl._configure()
        cc.ui.edit_value(f"{zctrl.name}: value at CC 127", zctrl.midi_cc_val2, zctrl.value_min, zctrl.value_max,
                         set_val2, step=step, decimals=decimals)

    cc.ui.edit_value(f"{zctrl.name}: value at CC 0", zctrl.midi_cc_val1, zctrl.value_min, zctrl.value_max,
                     set_val1, step=step, decimals=decimals)


# The chain controllers' pages (docs/chain-controller-pages.md): a chain's named pages of 4 slots

def zctrl_slot_label(zpages, zctrl):
    """The controller options' entry: "Chain Controller slot..." and where the controller is"""
    places = zpages.find(zctrl)
    if not places:
        return "Chain Controller slot..."
    page, slot = places[0]
    more = f" (+{len(places) - 1})" if len(places) > 1 else ""
    return f"Chain Controller slot: {zpages.pages[page].name}, {slot + 1}{more}"


def _zctrl_pages_done(cc, chain):
    """After a change of the chain controller pages: chain control's pages again, consumers told"""
    cc.rebuild()
    gd.zctrl_pages_changed(chain)


def show_zctrl_slot_options(cc, chain, zctrl, selected=0):
    """Put the controller into a chain controller slot (a page, then its slot; New page), remove
    it, a new page of the shown processor page's controllers, the page manager"""
    zpages = chain.zctrl_pages
    ui = cc.ui
    again = lambda index: (lambda: show_zctrl_slot_options(cc, chain, zctrl, index))  # noqa: E731
    opts = []
    for page, slot in zpages.find(zctrl):
        def remove(page=page):
            zpages.remove(zctrl, page, prune=True)
            _zctrl_pages_done(cc, chain)
            show_zctrl_slot_options(cc, chain, zctrl)
        opts.append((f"Remove from {zpages.pages[page].name}, slot {slot + 1}", remove, None, None))
    places = {p for p, _ in zpages.find(zctrl)}
    for page, rpage in enumerate(zpages.pages):
        index = len(opts)
        opts.append((f"{'☒' if page in places else '☐'} {rpage.name}...",
                     lambda page=page, index=index: _zctrl_slots(cc, chain, zctrl, page, again(index)), None, None))
    index = len(opts)
    opts.append(("New page...", lambda: _zctrl_slots(cc, chain, zctrl, len(zpages.pages), again(index)), None, None))
    shown = _shown_page(cc)
    if shown is not None:
        title, zctrls = shown

        def add_this_page():
            page = zpages.add_page(title, [zctrl_ref(z) for z in zctrls])
            zpages.current = page
            _zctrl_pages_done(cc, chain)
            show_zctrl_slot_options(cc, chain, zctrl)
        opts.append((f"Add page '{title}'", add_this_page, None, None))
    if zpages.pages:
        opts.append(("Manage pages...", lambda: show_zctrl_pages(cc, chain), None, None))
    ui.show_options(f"Chain Controller slot: {zctrl.name}", opts, min(selected, len(opts) - 1))


def _shown_page(cc):
    """(title, controllers) of chain control's selected page if it is a processor's page (not a
    chain controller page), else None"""
    entries = cc.pages.entries
    if not 0 <= cc._page < len(entries) or not entries[cc._page]["data"]:
        return None
    kind = entries[cc._page]["data"][0]
    zctrls = list(cc._page_zctrls[:gd.CELLS_PER_PAGE])
    if kind != "proc" or not any(z is not None for z in zctrls):
        return None
    return entries[cc._page]["title"], zctrls


def _zctrl_slots(cc, chain, zctrl, page, done):
    """The slot picker of a page (page == the page count: a new page): what each slot holds; a
    choice puts the controller there (on its page already: the two swap)"""
    zpages = chain.zctrl_pages
    new = page >= len(zpages.pages)
    name = zpages.default_name() if new else zpages.pages[page].name
    zctrls = [None] * SLOTS if new else zpages.zctrls(page)
    refs = [None] * SLOTS if new else zpages.pages[page].slots
    ref = zctrl_ref(zctrl)
    opts = []
    for slot in range(SLOTS):
        held = gd.cell_name(zctrls[slot]) if zctrls[slot] is not None else ("(missing)" if refs[slot] else "–")
        mark = "☒" if ref is not None and refs[slot] == ref else "☐"

        def choose(slot=slot):
            if gd.zctrl_assign(chain, zctrl, slot, page) >= 0:
                zpages.current = min(page, len(zpages.pages) - 1)
                cc.rebuild()
            done()
        opts.append((f"{mark} {slot + 1}  {held}", choose, None, None))
    selected = next((k for k in range(SLOTS) if refs[k] == ref), next((k for k in range(SLOTS) if refs[k] is None), 0))
    cc.ui.show_options(f"{name}: slot for {zctrl.name}", opts, selected)


def show_zctrl_pages(cc, chain, selected=0):
    """The page manager: one entry per page, each opens rename / move / clear / delete"""
    zpages = chain.zctrl_pages
    opts = [(f"{page.name}  ({sum(r is not None for r in page.slots)})", lambda p=p: _zctrl_page(cc, chain, p), None, None)
            for p, page in enumerate(zpages.pages)]
    if not opts:
        return
    cc.ui.show_options("Chain controller pages", opts, min(selected, len(opts) - 1))


def _zctrl_page(cc, chain, page):
    zpages = chain.zctrl_pages
    if not 0 <= page < len(zpages.pages):
        return
    ui = cc.ui
    name = zpages.pages[page].name

    def rename():
        def set_name(text):
            if zpages.rename_page(page, text):
                _zctrl_pages_done(cc, chain)
            _zctrl_page(cc, chain, page)
        ui.show_keyboard(set_name, name, "Page name")

    def move(step):
        def run():
            to = zpages.move_page(page, step)
            _zctrl_pages_done(cc, chain)
            _zctrl_page(cc, chain, to)
        return run

    def clear():
        zpages.clear_page(page)
        _zctrl_pages_done(cc, chain)
        _zctrl_page(cc, chain, page)

    def delete():
        def run():
            zpages.delete_page(page)
            _zctrl_pages_done(cc, chain)
            show_zctrl_pages(cc, chain, page)
        ui.confirm(f"Delete chain controller page '{name}'?", run)

    opts = [("Rename...", rename, None, None)]
    if page > 0:
        opts.append(("Move up", move(-1), None, None))
    if page < len(zpages.pages) - 1:
        opts.append(("Move down", move(1), None, None))
    opts += [("Clear", clear, None, None), ("Delete", delete, None, None)]
    ui.show_options(f"Chain controller page: {name}", opts)
