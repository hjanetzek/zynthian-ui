"""Engine, MIDI channel, bank and preset selection (as zynthian_gui_engine, _midi_chan, _bank,
_preset)"""

import logging

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

    def fill(self):
        proc_type = self.ui.chain_edit.status.get("type", "")
        self.set_title(f"Engine ({proc_type})")
        self.chain_manager.get_engine_info()
        self.engines_by_cat = self.chain_manager.filtered_engines_by_cat(proc_type)
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
        if proc_type in ("MIDI Tool", "Audio Effect"):
            entries.append(entry("None", info="No processor (empty chain)", data="None"))
        cats = self.categories
        if cats:
            for code, info in self.engines_by_cat[cats[self.categoryIndex]].items():
                stars = "★" * int(info.get("QUALITY", 0) or 0)
                entries.append(entry(info["TITLE"], data=code,
                                     info=f"{info['NAME']}\n{stars}\n\n{info.get('DESCR', '')}"))
        if not entries:
            entries.append(entry("No engines available", enabled=False,
                                 info="No engine of this type is installed or enabled."))
        self.set_entries(entries, 0)

    def select_action(self, index, t):
        if t != "S":
            return
        code = self.entries[index]["data"]
        status = self.ui.chain_edit.status
        status["engine"] = code
        if "chain_id" not in status:
            if code == "AP":
                status["audio_thru"] = False
            if status["type"] in ("Audio Effect", "Audio Generator") and not status.get("midi_thru"):
                status["midi_chan"] = None
        self.ui.modify_chain()


class MidiChannel(SelectorScreen):
    name = "midi_chan"

    def fill(self):
        self.set_title("MIDI Channel")
        cm = self.chain_manager
        try:
            current = cm.get_next_free_midi_chan(0)
        except Exception as e:
            logging.warning(e)
            current = 0
        entries = [entry("ALL MIDI CHANNELS", data=0xffff,
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
        if t == "S":
            self.ui.chain_edit.status["midi_chan"] = self.entries[index]["data"]
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
            self.ui.replace_screen("chain_control")

    def back(self):
        proc = self.ui.current_processor
        if proc and proc.preset_subdir_info:
            proc.preset_subdir_info = None
            self.fill()
            return True
        return False
