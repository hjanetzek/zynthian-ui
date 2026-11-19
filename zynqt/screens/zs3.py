"""ZS3 (sub-snapshots: zynthian_gui_zs3, zynthian_gui_zs3_options): save, load, overwrite, rename,
clone, delete, note, move, restore options, program change number / channel; MIDI learn: a
program change saves a ZS3 for it (while learning: from the ZS3 CUIA or TOGGLE_MIDI_LEARN). The
stage (performance) view of ALT is not ported."""

from zynqt.screens.base import SelectorScreen, entry, separator


class ZS3(SelectorScreen):
    name = "zs3"
    default_icon = "zs3.png"   # Tk's selector_info default

    def __init__(self, ui, parent=None):
        super().__init__(ui, parent)
        self.moving_zs3 = None      # the ZS3 being moved (zs3 options: Move)
        ui.bridge.zs3Saved.connect(self._saved)

    # Program change learning (zynthian_gui_zs3): the state manager saves the ZS3

    def enable_midi_learn(self):
        self.state_manager.enable_learn_pc()
        self.fill()

    def disable_midi_learn(self):
        if self.state_manager.midi_learn_pc is not None:
            self.state_manager.disable_learn_pc()
            if self.ui.current_screen == self.name:
                self.fill()

    def toggle_midi_learn(self):
        if self.state_manager.midi_learn_pc is not None:
            self.disable_midi_learn()
        else:
            self.enable_midi_learn()

    def switch(self, i, t):
        """Switch 2 short: program change learning on / off (zynthian_gui_zs3.switch)"""
        if i == 2 and t == "S":
            self.toggle_midi_learn()
            return True
        return False

    def cuia_v5_zynpot_switch(self, params):
        try:
            i, t = int(params[0]), str(params[1]).upper()
        except (TypeError, ValueError, IndexError):
            return False
        if i == 2 and t == "S":
            self.toggle_midi_learn()
            return True
        return False

    def hide(self):
        self.moving_zs3 = None
        self.disable_midi_learn()

    def _saved(self):
        if self.ui.current_screen == self.name:
            self.state_manager.disable_learn_pc()
            self.fill()

    def build(self):
        """Shown: the cursor on the last loaded ZS3 (else the first row), as Tk's build_view,
        which resets the cursor before filling the list since upstream 7d445b81"""
        self._index = 0   # set_entries() emits the change
        self.fill()

    def fill(self):
        sm = self.state_manager
        self.set_title("ZS3 (SubSnapShots)")
        zs3_ids = sm.get_zs3_ids()
        entries = [entry("Save as new ZS3", data="SAVE_ZS3", icon="zs3_new.png",
                         info="Save current state as a new ZS3.")]
        # Tk: a status label under the list while learning
        self.set_status_line("Waiting for MIDI Program Change..." if sm.midi_learn_pc is not None else "")
        index = None
        if "zs3-0" in sm.zs3:
            entries.append(entry("Default state", data="zs3-0", icon="zs3_default.png",
                                 info="Load default ZS3 state.\n\nBold select for options."))
        if len(sm.zs3) > 1:
            entries.append(separator("> SAVED ZS3s"))
        for zs3_id, state in sm.zs3.items():
            if zs3_id == "zs3-0":
                continue
            if zs3_id.startswith("zs3"):
                title = f"{state['title']}"
            else:
                parts = zs3_id.split('/')
                if len(parts) > 1:
                    if parts[0] == "*":
                        title = f"{state['title']} -> PRG#{parts[1]}"
                    else:
                        title = f"{state['title']} -> CH#{int(parts[0]) + 1}:PRG#{parts[1]}"
                else:
                    title = f"{state['title']} ({zs3_id})"
            info = "Restore ZS3.\n\nBold select for options."
            if zs3_id == self.moving_zs3:
                # Same marks as a phrase being moved in the launcher
                mark = "\u21d3" if zs3_id == zs3_ids[0] else ("\u21d1" if zs3_id == zs3_ids[-1] else "\u21d5")
                title = f"{mark} {title}"
                info = "Use knob, arrows or touch-drag to move.\n\nSelect or back to finish."
                index = len(entries)
            elif zs3_id == sm.last_zs3_id and not self.moving_zs3 and self._index == 0:
                # Tk's fill_list: only from the first row
                index = len(entries)
            entries.append(entry(title, data=zs3_id, info=info))
        self.set_entries(entries, index)

    def show_menu(self):
        """MENU: the selected entry's options (Tk's show_menu: bold select)"""
        self.activate(self._index, "B")

    # Moving a ZS3 (zynthian_gui_zs3.nudge_zs3): knob, arrows; select or back ends it

    def move(self, step):
        if self.moving_zs3:
            self.nudge_zs3(step)
        else:
            super().move(step)

    def nudge_zs3(self, d):
        sm = self.state_manager
        ids = sm.get_zs3_ids()
        if self.moving_zs3 not in ids:
            self.end_moving_zs3()
            return
        sm.move_zs3(self.moving_zs3, ids.index(self.moving_zs3) + d)
        self.fill()

    def end_moving_zs3(self):
        self.moving_zs3 = None
        self.fill()

    def back(self):
        self.state_manager.disable_learn_pc()
        if self.moving_zs3:
            self.end_moving_zs3()
            return True
        return False

    def select_action(self, index, t):
        sm = self.state_manager
        if self.moving_zs3:
            self.end_moving_zs3()
            return
        zs3_id = self.entries[index]["data"]
        if t == "S":
            sm.disable_learn_pc()
            if zs3_id == "SAVE_ZS3":
                sm.save_zs3()
                self.fill()
            else:
                sm.load_zs3(zs3_id)
                self.ui.back()
        elif zs3_id != "SAVE_ZS3":
            # Tk's show_menu: learning stays on for "Save as new ZS3"
            sm.disable_learn_pc()
            self.show_options(zs3_id)

    # ZS3 options (zynthian_gui_zs3_options)

    def show_options(self, zs3_id, selected=0):
        sm = self.state_manager
        title = sm.get_zs3_title(zs3_id)

        def done():
            self.fill()

        def opt(label, action, info, icon):
            return (label, action, info, icon)

        overwrite = opt("Overwrite", lambda: (sm.save_zs3(zs3_id), done()),
                        "Save current state, overwritting this ZS3.", "zs3_overwrite.png")
        if zs3_id == "zs3-0":
            options = [overwrite]
        else:
            options = [
                opt("Restore options...", lambda: self.show_restore_options(zs3_id),
                    "Select which elements will be restored from this ZS3.", "zs3_settings.png"),
                overwrite,
                opt("Rename", lambda: self.ui.show_keyboard(lambda t: (sm.set_zs3_title(zs3_id, t), done()),
                                                         title, "Rename ZS3"), "Rename this ZS3.", "zs3_rename.png"),
                opt("Note", lambda: self.ui.show_keyboard(lambda n: (sm.set_zs3_note(zs3_id, n), done()),
                                                       sm.get_zs3_note(zs3_id) or "", "ZS3 note"),
                    "Add a note to this ZS3, shown by the ZS3 performance view.", "zs3_rename.png"),
                opt("Clone", lambda: self.ui.show_keyboard(lambda t: (sm.clone_zs3(zs3_id, t), done()),
                                                        title, "Name of the copy"),
                    "Copy this ZS3 to a new one, placed just after it.", "zs3_new.png"),
            ]
            if len(sm.get_zs3_ids()) > 1:
                options.append(opt("Move", lambda: self.start_moving_zs3(zs3_id),
                                   "Move this ZS3 up/down in the list.", "zs3_settings.png"))
            options.append(opt("Delete", lambda: self.ui.confirm(f"Do you really want to delete ZS3: {zs3_id}?",
                                                                 lambda: (sm.delete_zs3(zs3_id), done())),
                               "Delete this ZS3.", "zs3_delete.png"))
            prog_chan, prog_num = self._prog(zs3_id)
            if "/" in zs3_id:
                options.append(opt(f"Program Change Number [{prog_num - 1 if prog_num else 'None'}]",
                                   lambda: self.pick_prog_num(zs3_id), "Assign MIDI Program Change number to this ZS3.",
                                   "zs3_overwrite.png"))
                options.append(opt(f"Program Change Channel [{prog_chan if prog_chan else 'Any'}]",
                                   lambda: self.pick_prog_chan(zs3_id),
                                   "Assign MIDI Program Change channel to this ZS3.", "zs3_overwrite.png"))
            else:
                options.append(opt("Program Change Number [None]", lambda: self.pick_prog_num(zs3_id),
                                   "Assign MIDI Program Change number to this ZS3.", "zs3_overwrite.png"))
        self.ui.show_options(f"ZS3 Options: {title}", options, selected)

    def start_moving_zs3(self, zs3_id):
        self.moving_zs3 = zs3_id
        self.fill()

    @staticmethod
    def _prog(zs3_id):
        """(channel 1-16 or 0 any, program 1-128 or 0 none) of a ZS3 id"""
        if not zs3_id.startswith("zs3"):
            parts = zs3_id.split("/")
            if len(parts) > 1:
                if parts[0] == "*":
                    return 0, int(parts[1]) + 1
                return int(parts[0]) + 1, int(parts[1]) + 1
        return 0, 0

    def show_restore_options(self, zs3_id, selected=0):
        """Which chains, processors and the MIDI learn the ZS3 restores (zs3_restoring_options_cb);
        each entry toggles (Tk: bold toggles all)"""
        sm = self.state_manager
        cm = self.ui.chain_manager
        state = sm.zs3.get(zs3_id)
        if state is None:
            return
        options = []
        mixer_ids = []

        def toggle(kind, ident, index):
            def run():
                sm.toggle_zs3_restore_flag(zs3_id, kind, ident)
                self.show_restore_options(zs3_id, index)
            return run

        def toggle_mixer(index):
            def run():
                for pid in mixer_ids:
                    sm.toggle_zs3_restore_flag(zs3_id, "processors", pid)
                self.show_restore_options(zs3_id, index)
            return run

        options.append(("Toggle All Mixer", toggle_mixer(0),
                        "Toggle the selection of all audio mixer parameters that will be restored.", None))
        for idx, chain_id in enumerate(cm.chains):
            chain = cm.get_chain(chain_id)
            if chain is None:
                continue
            label = f"{idx + 1} {chain.get_name()}" if chain_id else chain.get_name()
            if "chains" in state and chain_id in state["chains"]:
                restore = state["chains"][chain_id].get("restore", True)
                options.append((("\u2612 " if restore else "\u2610 ") + label,
                                toggle("chains", chain_id, len(options)),
                                "Toggle whether chain parameters will be restored.", None))
            else:
                options.append((label, None, None, None))
            for proc in chain.get_processors():
                if proc.id in state.get("processors", {}):
                    restore = state["processors"][proc.id].get("restore", True)
                    if proc.eng_code in ("MI", "MR"):
                        plabel = proc.name
                        mixer_ids.append(str(proc.id))
                    else:
                        plabel = f"{proc.name} ({proc.id})"
                    options.append((("\u2612" if restore else "\u2610") + f"   \u2937{plabel}",
                                    toggle("processors", proc.id, len(options)),
                                    "Toggle whether processor parameters will be restored.", None))
        prefix = "\u2612" if state.get("restore_midi_learn", False) else "\u2610"
        options.append((f"{prefix} MIDI learn", toggle("midi_learn", None, len(options)),
                        "Toggle whether MIDI learn (CC binding) is restored.", None))
        self.ui.show_options(f"ZS3 Restore: {sm.get_zs3_title(zs3_id)}", options, selected)

    def pick_prog_num(self, zs3_id):
        chan, prog = self._prog(zs3_id)
        choices = [("None", 0)] + [(str(i), i + 1) for i in range(128)]
        self.ui.show_options("Program Change Number",
                             [(label, lambda v=v: self.update_prog(zs3_id, chan, v), None, None) for label, v in choices],
                             prog)

    def pick_prog_chan(self, zs3_id):
        chan, prog = self._prog(zs3_id)
        choices = [("Any", 0)] + [(str(i), i) for i in range(1, 17)]
        self.ui.show_options("Program Change Channel",
                             [(label, lambda v=v: self.update_prog(zs3_id, v, prog), None, None) for label, v in choices],
                             chan)

    def update_prog(self, zs3_id, chan, prog):
        """zynthian_gui_zs3_options.update_prog: the ZS3's id encodes channel and program"""
        sm = self.state_manager
        if prog == 0:
            title = sm.zs3[zs3_id]["title"]
            try:
                index = int(title.split("-")[1]) if title.startswith("ZS3-") else sm.get_next_zs3_index()
            except (IndexError, ValueError):
                index = sm.get_next_zs3_index()
            new_id = f"zs3-{index}"
        else:
            new_id = f"*/{prog - 1}" if chan == 0 else f"{chan - 1}/{prog - 1}"
        if new_id == zs3_id:
            return

        def do():
            ids = sm.get_zs3_ids()
            position = ids.index(zs3_id) if zs3_id in ids else -1
            zs3 = sm.zs3.pop(zs3_id)
            sm.zs3[new_id] = zs3
            if position >= 0:
                sm.move_zs3(new_id, position)
            self.fill()
        if new_id in sm.zs3:
            self.ui.confirm(f"Overwrite existing ZS3: {sm.zs3[new_id]['title']}?", do)
        else:
            do()
