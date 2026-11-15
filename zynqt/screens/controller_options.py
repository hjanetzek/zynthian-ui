"""Options of a controller in the chain control screen (zynthian_gui_control.controller_options, a
long press on a controller): chain controller, MIDI learn (chain or global), the learned binding's
CC mode and value range, momentary/debounce for toggles, the step sequencer's automation, the
input devices of the learned binding, unlearn.

"""

import logging

import zynautoconnect
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
            chain.toggle_zctrl(zctrl)
            cc.rebuild()
            again(0)()
        opts.append((f"{'☒' if zctrl in chain.zctrls else '☐'} Chain Controller", toggle_chain_ctrl, None, None))

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
