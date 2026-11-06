"""Engine, MIDI channel, bank and preset selection (as zynthian_gui_engine, _midi_chan, _bank,
_preset)"""

import logging

import zynautoconnect

from zyngui import zynthian_gui_config
from zynqt.screens.base import SelectorScreen, entry, separator


def list_data_entries(list_data, default_info=""):
    """Rows of a Tk selector's list_data ([value, index, title, (info, icon)...]) as entries:
    rows whose value is None are section titles"""
    entries = []
    for row in list_data or []:
        title = row[2] if len(row) > 2 else str(row[0])
        info, icon = default_info, ""
        if len(row) > 3 and isinstance(row[-1], (list, tuple)) and len(row[-1]) >= 2:
            info, icon = row[-1][0] or default_info, row[-1][1] or ""
        if row[0] is None:
            entries.append(separator(title))
        else:
            entries.append(entry(title, info=info, icon=icon, data=row))
    return entries


class Engine(SelectorScreen):
    name = "engine"

    def __init__(self, ui, parent=None):
        super().__init__(ui, parent)
        self.engines_by_cat = {}
        self.category_by_type = {}
        self.show_all = False      # long press: all engines, to enable or disable them
        self.engine_info_dirty = False

    def build(self):
        self.show_all = False
        super().build()

    def fill(self):
        proc_type = self.ui.chain_edit.status.get("type", "")
        self.set_title(f"Enable engines ({proc_type})" if self.show_all else f"Engine ({proc_type})")
        self.chain_manager.get_engine_info()
        self.engines_by_cat = self.chain_manager.filtered_engines_by_cat(proc_type, all=self.show_all)
        for exclude in ("MI", "MR", "MX"):
            self.engines_by_cat.get("Other", {}).pop(exclude, None)
        cats = list(self.engines_by_cat.keys())
        self.set_categories(cats, self.category_by_type.get(proc_type, 0))
        self._fill_category()

    def category_changed(self):
        self.category_by_type[self.ui.chain_edit.status.get("type", "")] = self.categoryIndex
        self._fill_category()

    def _fill_category(self):
        proc_type = self.ui.chain_edit.status.get("type", "")
        entries = []
        if proc_type in ("MIDI Tool", "Audio Effect") and not self.show_all:
            entries.append(entry("None", info="No processor (empty chain)", data="None"))
        cats = self.categories
        if cats:
            for code, info in self.engines_by_cat[cats[self.categoryIndex]].items():
                stars = "★" * int(info.get("QUALITY", 0) or 0)
                title = info["TITLE"]
                if self.show_all:
                    title = ("☒ " if info["ENABLED"] else "☐ ") + title
                entries.append(entry(title, data=code,
                                     info=f"{info['NAME']}\n{stars}\n\n{info.get('DESCR', '')}"))
        if not entries:
            entries.append(entry("No engines available", enabled=False,
                                 info="No engine of this type is installed or enabled.\n"
                                      "Long press to enable some engines."))
        self.set_entries(entries, self.index if self.show_all else 0)

    def activate(self, index, t="S"):
        # Long press (also on "No engines available"): enable or disable engines
        if t == "B" and not self.show_all:
            self.show_all = True
            self.fill()
            return
        super().activate(index, t)

    def back(self):
        if self.show_all:
            if self.engine_info_dirty:
                self.chain_manager.save_engine_info()
                self.engine_info_dirty = False
            self.show_all = False
            self.fill()
            return True
        return False

    def select_action(self, index, t):
        if t != "S":
            return
        code = self.entries[index]["data"]
        if code is None:
            return
        if self.show_all:
            info = self.chain_manager.engine_info[code]
            info["ENABLED"] = not info["ENABLED"]
            if info.get("EDIT", 0) == 0:
                info["EDIT"] = 1
            self.engine_info_dirty = True
            self.fill()
            return
        status = self.ui.chain_edit.status
        status["engine"] = code
        if "chain_id" not in status:
            if code == "AP":
                status["audio_thru"] = False
            if status["type"] in ("Audio Effect", "Audio Generator") and not status.get("midi_thru"):
                status["midi_chan"] = None
        self.ui.modify_chain()


class MidiChannel(SelectorScreen):
    """MIDI channel of a new chain (mode "ADD") or of the active chain ("SET")"""

    name = "midi_chan"

    def __init__(self, ui, parent=None):
        super().__init__(ui, parent)
        self.mode = "ADD"

    def fill(self):
        self.set_title("MIDI Channel")
        cm = self.chain_manager
        if self.mode == "SET":
            current = cm.get_active_chain().midi_chan
        else:
            try:
                current = cm.get_next_free_midi_chan(0)
            except Exception as e:
                logging.warning(e)
                current = 0
        entries = [entry(("\u2612 " if current == 0xffff else "") + "ALL MIDI CHANNELS", data=0xffff,
                         info="Multitimbral or unfiltered control of the engine.")]
        index = 0
        for chan in range(16):
            if chan == zynthian_gui_config.master_midi_channel:
                continue
            used = cm.get_num_chains_midi_chan(chan)
            suffix = f"  ({used} chain{'s' if used > 1 else ''})" if used else ""
            if chan == current:
                index = len(entries)
            entries.append(entry(f"MIDI CH#{chan + 1}{suffix}", data=chan,
                                 info=f"Chains on this channel: {used}" if used else "Free channel"))
        self.set_entries(entries, index)

    def select_action(self, index, t):
        if t != "S":
            return
        chan = self.entries[index]["data"]
        if self.mode == "SET":
            self.chain_manager.set_midi_chan(self.chain_manager.active_chain.chain_id, chan)
            zynautoconnect.request_midi_connect(True)
            self.ui.back()
        else:
            self.ui.chain_edit.status["midi_chan"] = chan
            self.ui.modify_chain()


class Bank(SelectorScreen):
    name = "bank"

    def fill(self):
        proc = self.ui.current_processor
        if not proc:
            self.set_entries([])
            return
        self.set_title(f"{proc.get_name()}: Bank")
        proc.preset_subdir_info = None
        index = proc.get_bank_index()
        if proc.get_show_fav_presets():
            if proc.get_preset_favs():
                index = 0
            else:
                proc.set_show_fav_presets(False)
        self.set_entries(list_data_entries(proc.get_bank_list()), index)

    def select_action(self, index, t):
        if t != "S":
            return
        proc = self.ui.current_processor
        row = self.entries[index]["data"]
        if row and row[0] == "*FAVS*":
            proc.set_show_fav_presets(True)
        else:
            if proc.set_bank(index) is None:
                self.fill()   # more bank levels (sub-folders)
                return
            proc.set_show_fav_presets(False)
            proc.load_preset_list()
            if not proc.preset_list:
                # Nothing to choose: the "bank" was the preset (the audio player's files are
                # listed with the folders); back to the processor (zynthian_gui_preset doesn't
                # show an empty list either)
                self.ui.purge_history("bank")
                self.ui.replace_screen("audio_player" if proc is self.state_manager.audio_player
                                       else "chain_control")
                return
        if len(self.entries) <= 1:
            self.ui.replace_screen("preset")
        else:
            self.ui.showScreen("preset")

    def back(self):
        proc = self.ui.current_processor
        if proc and proc.bank_subdir_info:
            proc.bank_subdir_info = None
            proc.preset_subdir_info = None
            self.fill()
            return True
        return False


class Preset(SelectorScreen):
    name = "preset"

    def fill(self):
        proc = self.ui.current_processor
        if not proc:
            self.set_entries([])
            return
        proc.load_preset_list()
        title = f"{proc.get_basepath()} > Favorites" if proc.show_fav_presets else proc.get_bankpath()
        self.set_title(title)
        self.set_entries(list_data_entries(proc.preset_list), proc.get_preset_index())

    def select_action(self, index, t):
        if t != "S":
            return
        proc = self.ui.current_processor
        self.state_manager.start_busy("set preset")
        try:
            result = proc.set_preset(index)
        finally:
            self.state_manager.end_busy("set preset")
        if result is None:
            self.fill()   # still browsing (sub-folders)
        else:
            self.ui.purge_history("bank")
            # Back to what shows the processor: the audio player's own screen, else chain control
            self.ui.replace_screen("audio_player" if proc is self.state_manager.audio_player
                                   else "chain_control")

    def cuia_toggle_play(self, params=None):
        """PLAY in an audio player's file list (zynthian_gui_preset): load the selected file, then
        play it: the chain's player here, the global one by the global PLAY"""
        proc = self.ui.current_processor
        if proc is None or getattr(proc.engine, "nickname", None) != "AP":
            return False
        self.activate(self._index)
        if proc is not self.state_manager.audio_player:
            proc.controllers_dict["transport"].set_value(127)
            return True
        return False

    def back(self):
        proc = self.ui.current_processor
        if proc and proc.preset_subdir_info:
            proc.preset_subdir_info = None
            self.fill()
            return True
        return False
