"""Options of a controller in the chain control screen (zynthian_gui_control.controller_options, a
long press on a controller): chain controller, MIDI learn (chain or global), the learned binding's
CC mode and value range, momentary/debounce for toggles, the step sequencer's CC, unlearn.

Not ported: the X-Y touchpad axes (no touchpad screen in the Qt UI yet).
"""

from zyngui.zynthian_midi_learn_data import (CC_MODES, MIDI_LEARNING_CHAIN, MIDI_LEARNING_GLOBAL, cc_mode_label,
                                             set_cc_mode, unlearn_label, zynstep_cc)


def show_controller_options(cc, i, selected=0):
    """cc: the ChainControl; i: controller slot"""
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

    ml = cm.get_midi_learn_from_zctrl(zctrl, abs=True, chain=True, zynstep=False)
    opts.append(("MIDI learn", None, None, None))
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

    step_cc = zynstep_cc(cm, zctrl)
    step_index = len(opts)

    def pick_step_cc():
        def choose(num):
            cm.add_zynstep_midi_learn(num, zctrl)
            again(step_index)()
        ui.show_options("ZynStep CC", [(str(n), lambda n=n: choose(n), None, None) for n in range(1, 128)],
                        step_cc - 1 if step_cc else 0)
    opts.append((f"ZynStep CC [{'NONE' if step_cc is None else step_cc}]", pick_step_cc, None, None))

    if ml and (label := unlearn_label(ml)):
        def unlearn():
            cm.clean_midi_learn(zctrl)
            cc.refresh_bindings()
        opts.append((label, unlearn, None, None))
    opts.append(("Unlearn all controls", cc.midi_unlearn_action, None, None))
    ui.show_options(f"Control options: {zctrl.name}", opts, selected)


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
