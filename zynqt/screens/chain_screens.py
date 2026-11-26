"""Engine, MIDI channel, bank and preset selection (as zynthian_gui_engine, _midi_chan, _bank,
_preset)"""

import copy
import logging
import os

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


def has_bank_dirs(proc):
    """The processor's engine finds its banks in directories (soundfonts, sample libraries, preset
    files), so an empty bank list means nothing is installed there yet"""
    return bool(proc is not None and getattr(proc.engine, "root_bank_dirs", None))


def empty_list_hint(proc, what="bank"):
    """Rows shown instead of an empty bank (what="bank") or preset list: what is missing and how to
    add some (copy files to my-data, install a content package). Selecting one scans again."""
    engine = proc.engine
    dirs = getattr(engine, "root_bank_dirs", None) or []
    user = next((d for label, d in dirs if label.startswith("User")), None)
    fexts = [e for e in (getattr(engine, "preset_fexts", None) or []) if e]
    if what == "bank" and user:
        my_data = getattr(engine, "my_data_dir", "") or ""
        if my_data and user.startswith(my_data.rstrip("/") + "/"):
            where = os.path.basename(my_data.rstrip("/")) + user[len(my_data.rstrip("/")):]
        else:
            where = user
        # Content packages (zynthian-packages) bring soundfonts
        soundfonts = "/soundfonts/" in user
        noun = "soundfonts" if soundfonts else "audio files" if "/files/" in user else "banks"
        files = " / ".join("." + e for e in fexts) + " files" if fexts else "files"
        title = f"No {noun} found"
        info = f"Copy {files} to {where} (network share, USB or webconf)"
        rows = [title, f"Copy {files} to", where]
        if soundfonts:
            info += " or install a soundfont package"
            rows.append("or install a soundfont package.")
        info += ".\nSelect to scan again."
    elif what == "bank":
        title = "No banks found"
        info = f"{proc.get_name()} has no banks or presets.\nSelect to scan again."
        rows = [title]
    else:
        title = "No presets found"
        banks = [b for b in (proc.bank_list or []) if b and b[0]]
        info = "This bank has no presets." if banks else f"{proc.get_name()} has no presets."
        if callable(getattr(engine, "save_preset", None)):
            info += "\nBold to show options: save a new preset."
        rows = [title]
    entries = [entry(rows[0], info=info, icon="presets_bank.png" if what == "bank" else "preset.png")]
    entries += [entry(r, info=info) for r in rows[1:]]
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

    def _set_path_title(self):
        """Tk's breadcrumb (zynthian_gui_engine.set_select_path), e.g. MIDI Instrument/Synth"""
        proc_type = self.ui.chain_edit.status.get("type", "")
        if self.show_all:
            self.set_title(f"Enable engines ({proc_type})")
            return
        from zyngine import zynthian_lv2
        path = zynthian_lv2.engine_type_title.get(proc_type, proc_type)
        if self.categories:
            path += "/" + self.categories[self.categoryIndex]
        self.set_title(path)

    def fill(self):
        proc_type = self.ui.chain_edit.status.get("type", "")
        self.chain_manager.get_engine_info()
        self.engines_by_cat = self.chain_manager.filtered_engines_by_cat(proc_type, all=self.show_all)
        for exclude in ("MI", "MR", "MX"):
            self.engines_by_cat.get("Other", {}).pop(exclude, None)
        cats = list(self.engines_by_cat.keys())
        self.set_categories(cats, self.category_by_type.get(proc_type, 0))
        self._set_path_title()
        self._fill_category()

    def category_changed(self):
        self.category_by_type[self.ui.chain_edit.status.get("type", "")] = self.categoryIndex
        self._set_path_title()
        self._fill_category()

    def _fill_category(self):
        proc_type = self.ui.chain_edit.status.get("type", "")
        entries = []
        if proc_type in ("MIDI Tool", "Audio Effect") and not self.show_all:
            entries.append(entry("None", info="No processor (empty chain)", data="None"))
        cats = self.categories
        if cats:
            for code, info in self.engines_by_cat[cats[self.categoryIndex]].items():
                # zynthian_gui_engine.update_info: quality stars, complexity gears (the info
                # pane draws them: currentQuality, currentComplexity), the description
                title = info["TITLE"]
                if self.show_all:
                    title = ("☒ " if info["ENABLED"] else "☐ ") + title
                e = entry(title, data=code, info=info.get("DESCR", "") or "")
                e["quality"] = int(info.get("QUALITY", 0) or 0)
                e["complexity"] = int(info.get("COMPLEX", 0) or 0)
                entries.append(e)
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
    default_icon = "midi_logo.png"   # Tk's selector_info default

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
    selcap = "Bank"
    zsel_hidden = False
    default_icon = "presets_bank.png"

    def fill(self):
        proc = self.ui.current_processor
        if not proc:
            self.set_entries([])
            return
        self.set_title(proc.get_basepath_subdir())   # zynthian_gui_bank.set_select_path
        proc.preset_subdir_info = None
        index = proc.get_bank_index()
        if proc.get_show_fav_presets():
            if proc.get_preset_favs():
                index = 0
            else:
                proc.set_show_fav_presets(False)
        banks = proc.get_bank_list()
        if not banks:
            # Nothing installed: say so and how to add some (Tk doesn't show an empty list)
            self.set_entries(empty_list_hint(proc, "bank"), 0)
            return
        self.set_entries(list_data_entries(banks, "Bold to show options."), index)

    def select_action(self, index, t):
        if t == "B":
            self.show_bank_options()
            return
        if t != "S":
            return
        proc = self.ui.current_processor
        row = self.entries[index]["data"]
        if row is None:
            self.fill()   # the empty list's hint: scan again
            return
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

    # Bank options (zynthian_gui_bank.show_bank_options): rename / delete a user bank

    def show_menu(self):
        self.show_bank_options()

    def show_bank_options(self):
        proc = self.ui.current_processor
        if proc is None or not 0 <= self._index < len(self.entries):
            return
        engine = proc.engine
        bank = copy.deepcopy(self.entries[self._index]["data"])
        if bank is None:
            return   # the empty list's hint
        options = []
        user = False
        if bank and engine.is_preset_user(bank):
            if hasattr(engine, "rename_user_bank"):
                options.append(("Rename", lambda: self.ui.show_keyboard(
                    lambda name: self._rename_bank(bank, name), bank[2], "Rename bank"), "Rename bank", "rename.png"))
                user = True
            if hasattr(engine, "delete_user_bank"):
                options.append(("Delete", lambda: self.ui.confirm(
                    f"Do you really want to remove bank '{bank[2]}' and delete all of its presets?",
                    lambda: self._delete_bank(bank)), "Delete bank", "folder_delete.png"))
                user = True
        if not options:
            options.append(("No bank options!", None, None, None))
        self.ui.show_options(f"Bank options: {bank[2]}" if user else "Bank options", options)

    def _rename_bank(self, bank, name):
        self.ui.current_processor.engine.rename_user_bank(bank, name)
        self.fill()

    def _delete_bank(self, bank):
        self.ui.current_processor.engine.delete_user_bank(bank)
        self.fill()

    def enters(self, index):
        """A bank (or the favourites, a sub-folder) opens the presets; not the empty list's hint"""
        e = self._entry_at(index)
        return bool(e and e["data"] is not None)

    def switch(self, i, t):
        """Switch 2 short: the favourite presets (zynthian_gui_bank.switch)"""
        if i == 2 and t == "S":
            self.ui.cuia_preset_fav()
            return True
        return False

    def back(self):
        """Up one bank sub-folder (zynthian_gui_bank.browse_back): the parent's (bank_subdir_info
        [3]), the folder left selected (its index, [1])"""
        proc = self.ui.current_processor
        sdi = proc.bank_subdir_info if proc else None
        if sdi:
            proc.bank_subdir_info = sdi[3]
            proc.preset_subdir_info = None
            self.fill()
            self.setIndex(sdi[1])
            return True
        return False


# The flat preset list (theme token flatPresetList, docs/qt-theming.md): engines whose preset lists
# are cheap to read for every bank. sfizz scans the bank's directory (a few ms per bank); LV2
# plugins (JV/...) have their presets in memory (zynthian_lv2's cache). Not FluidSynth: its
# preset list loads the bank's SoundFont into the synth.
FLAT_PRESET_ENGINES = ("SF", "JV/")
# Knob turning from group to group (section title to section title) in the flat list: the BACK
# knob (Tk's knob 1; V4: bottom left), unused in Tk's lists
GROUP_KNOB = 1


def flat_preset_engine(proc):
    code = getattr(proc, "eng_code", "") or ""
    return any(code == e or (e.endswith("/") and code.startswith(e)) for e in FLAT_PRESET_ENGINES)


class Preset(SelectorScreen):
    name = "preset"
    selcap = "Preset"
    zsel_hidden = False
    default_icon = "preset.png"
    section_titles_in_view = True   # only the flat list has section titles

    def __init__(self, ui, parent=None):
        super().__init__(ui, parent)
        self.flat = False   # the list shown is the flat one (all banks)
        # The flat list's presets of directory banks (sfizz: ~30 us per preset to scan):
        # {(engine class, bank path): (the directory's mtime, presets)}; the current bank is
        # always read again
        self._preset_cache = {}
        self._from_options = False

    def is_flat(self, proc=None):
        """The flat list (all banks under section titles) applies to the processor: the theme
        wants it, the engine reads its presets cheaply, there is more than one bank and no
        favourites view or sub-folder browsing"""
        proc = proc or self.ui.current_processor
        return bool(self.flat_preset_list and proc is not None and flat_preset_engine(proc)
                    and not proc.show_fav_presets and not proc.bank_subdir_info
                    and not proc.preset_subdir_info and len(self._real_banks(proc.get_bank_list())) > 1)

    @staticmethod
    def _real_banks(banks):
        return [b for b in banks or [] if b and b[0] is not None and b[0] != "*FAVS*"]

    def theme_options_changed(self):
        if self.ui.current_screen == self.name:
            self.fill()

    def _flat_entries(self, proc, info):
        """All banks with presets: a section title per bank (not selectable), its presets under
        it (data: (bank, preset)); the selection: the current preset (whichever bank is set),
        else the first preset of the current bank. Returns (entries, index)"""
        engine = proc.engine
        cur_bank = proc.bank_info[0] if proc.bank_info else None
        cur_preset = proc.preset_info[0] if proc.preset_info else None
        entries, index, bank_first = [], None, None
        for bank in self._real_banks(proc.bank_list):
            try:
                presets = self._bank_presets(proc, bank, bank[0] == cur_bank)
            except Exception as e:
                logging.error(f"presets of bank {bank[2]}: {e}")
                continue
            if not presets:
                continue
            entries.append(separator(str(bank[2]).replace("> ", "")))
            this_bank = bank[0] == cur_bank
            if this_bank:
                bank_first = len(entries)
            for preset in presets:
                if engine.is_preset_fav(preset):
                    preset = list(preset)
                    preset[2] = "\u2764 " + preset[2]
                if index is None and cur_preset is not None and preset[0] == cur_preset:
                    index = len(entries)
                entries.append(entry(preset[2], info=info, data=(bank, preset)))
        if index is None:
            index = bank_first if bank_first is not None else 1
        return entries, index

    def _bank_presets(self, proc, bank, fresh=False):
        """The bank's presets (engine.get_preset_list); a directory bank's from the cache while
        the directory's mtime is the same (an instrument added or removed changes it)"""
        engine = proc.engine
        path = bank[0]
        try:
            mtime = os.stat(path).st_mtime if isinstance(path, str) and path.startswith("/") else None
        except OSError:
            mtime = None
        key = (type(engine).__name__, path)
        if mtime is not None and not fresh:
            cached = self._preset_cache.get(key)
            if cached and cached[0] == mtime:
                return cached[1]
        presets = [p for p in engine.get_preset_list(bank, proc) or [] if p and p[0] and len(p) > 2 and p[2]]
        if mtime is not None:
            self._preset_cache[key] = (mtime, presets)
        return presets

    def _entry_bank(self, index):
        """The bank of entry index: its own in the flat list, else the processor's"""
        if self.flat and 0 <= index < len(self.entries) and self.entries[index]["data"]:
            return self.entries[index]["data"][0]
        return self.ui.current_processor.bank_info

    def _entry_preset(self, index):
        """The preset row of entry index (list_data row), or None"""
        if not 0 <= index < len(self.entries) or not self.entries[index]["data"]:
            return None
        data = self.entries[index]["data"]
        return data[1] if self.flat else data

    def selection_changed(self):
        # The flat list's title follows the selection: the processor and the selected preset's bank
        if self.flat:
            proc = self.ui.current_processor
            bank = self._entry_bank(self._index)
            if proc is not None and bank:
                self.set_title(f"{proc.get_basepath()} > {str(bank[2]).replace('> ', '')}")

    def _group_starts(self):
        """Indexes of the first entry under each section title (flat list)"""
        entries = self.entries
        return [i + 1 for i, e in enumerate(entries[:-1]) if e["separator"] and not entries[i + 1]["separator"]]

    def move_group(self, steps):
        """To the first preset of the group steps groups on (the current one's first preset
        first when moving back from inside a group)"""
        starts = self._group_starts()
        if not starts:
            return
        cur = max([n for n, i in enumerate(starts) if i <= self._index], default=0)
        if steps < 0 and self._index > starts[cur]:
            steps += 1   # back to this group's first preset first
        target = starts[max(0, min(len(starts) - 1, cur + steps))]
        self.set_index(target)
        self.showSection.emit(target - 1)   # the group from its title at the top

    def zynpot(self, i, d):
        """The group knob moves from group to group in the flat list"""
        if self.flat and i == GROUP_KNOB and d:
            self.move_group(d)
            return True
        return False

    def fill(self, keep=False):
        """keep: the flat list keeps the selected preset (filled again after a preset option)"""
        proc = self.ui.current_processor
        # Back from the preset options: the selection stays
        keep = keep or self._from_options
        self._from_options = False
        kept = self._entry_preset(self._index) if keep and self.flat else None
        if not proc:
            self.flat = False
            self.set_knob_hints([])
            self.set_entries([])
            return
        # zynthian_gui_preset.fill_list's default info (its "if self.allow_preset_preload:" tests the
        # method, always true: never "Preload disabled.")
        try:
            preload = "Preload enabled." if proc.engine.allow_timer_preload(None) else "Preload on note."
        except Exception:
            preload = "Preload enabled."
        self.flat = self.is_flat(proc)
        self.set_knob_hints(["", "group", "", "preset"] if self.flat else [])
        if self.flat:
            self.set_title(proc.get_basepath())
            entries, index = self._flat_entries(proc, preload + "\nBold to show options.")
            if kept:
                index = next((i for i, e in enumerate(entries)
                              if e["data"] and e["data"][1][0] == kept[0]), index)
            self.set_entries(entries, index)
            self.selection_changed()
            return
        proc.load_preset_list()
        title = f"{proc.get_basepath()} > Favorites" if proc.show_fav_presets else proc.get_bankpath()
        self.set_title(title)
        if not proc.preset_list:
            self.set_entries(empty_list_hint(proc, "preset"), 0)
            return
        self.set_entries(list_data_entries(proc.preset_list, preload + "\nBold to show options."),
                         proc.get_preset_index())

    def select_action(self, index, t):
        if t == "B":
            self.show_preset_options()
            return
        if t != "S" or self.entries[index]["data"] is None:
            return
        proc = self.ui.current_processor
        self.state_manager.start_busy("set preset")
        try:
            if self.flat:
                result = self._set_flat_preset(proc, *self.entries[index]["data"])
            else:
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

    @staticmethod
    def _set_flat_preset(proc, bank, preset):
        """A preset of the flat list: its bank first if it isn't the current one (as the bank
        list does), then the preset, as the preset list does"""
        if not proc.bank_info or proc.bank_info[0] != bank[0]:
            proc.get_bank_list()
            if not proc.set_bank_by_id(bank[0]):
                logging.error(f"Can't set bank {bank[2]}")
                return False
            proc.set_show_fav_presets(False)
        proc.load_preset_list()
        index = proc.find_preset_index_by_id(preset[0])
        if index is None:
            logging.error(f"Preset {preset[2]} not in bank {bank[2]}")
            return False
        return proc.set_preset(index)

    def cuia_toggle_play(self, params=None):
        """PLAY in an audio player's file list (zynthian_gui_preset): load the selected file, then
        play it: the chain's player here, the global one by the global PLAY"""
        proc = self.ui.current_processor
        if proc is None or getattr(proc.engine, "nickname", None) != "AP":
            return False
        if not 0 <= self._index < len(self.entries) or self.entries[self._index]["data"] is None:
            return True   # the empty list's hint
        self.activate(self._index)
        if proc is not self.state_manager.audio_player:
            proc.controllers_dict["transport"].set_value(127)
            return True
        return False

    # Preset options (zynthian_gui_preset.show_preset_options): favourite, save, rename, delete;
    # save as new preset (zynthian_gui_save_preset), rescan; the engine's own options

    def show_menu(self):
        self.show_preset_options()

    def show_preset_options(self):
        proc = self.ui.current_processor
        if proc is None:
            return
        engine = proc.engine
        preset = None
        title = "Preset Options"
        bank = self._entry_bank(self._index)
        if self._entry_preset(self._index):
            preset = list(copy.deepcopy(self._entry_preset(self._index)))
            if preset[2] and preset[2][0] == "\u2764":
                preset[2] = preset[2][2:]
            title = f"Preset: {preset[2]}"
        options = []
        if preset:
            fav = engine.is_preset_fav(preset)
            options.append(("\u2612 Favourite" if fav else "\u2610 Favourite", lambda: self._toggle_fav(preset, bank),
                            "Remove from favorites list" if fav else "Add to favorites list",
                            "favorite_remove.png" if fav else "favorite_add.png"))
            if engine.is_preset_user(preset):
                if hasattr(engine, "save_preset"):
                    options.append(("Save", lambda: self._save_overwrite(preset[2], bank), "Save overwriting", "file_save.png"))
                if hasattr(engine, "rename_preset"):
                    options.append(("Rename", lambda: self.ui.show_keyboard(
                        lambda name: self._rename_preset(preset, name, bank), preset[2], "Rename preset"),
                        "Rename", "rename.png"))
                if hasattr(engine, "delete_preset"):
                    options.append(("Delete", lambda: self.ui.confirm(
                        f"Do you really want to delete '{preset[2]}'?", lambda: self._delete_preset(preset, bank)),
                        "Delete", "file_delete.png"))
        global_options = []
        if hasattr(engine, "save_preset"):
            global_options.append(("Save new preset", self._save_new, "Save as new preset", "file_save.png"))
        if proc.eng_code.startswith("JV/"):
            global_options.append(("Scan for new presets", self._scan, "Scan new presets, e.g. added via webconf",
                                   "reload.png"))
        if global_options:
            options.append(("Global", None, None, None))
            options += global_options
        proc_options = engine.get_preset_options(preset) if callable(getattr(engine, "get_preset_options", None)) else {}
        if proc_options:
            options.append(("Processor", None, None, None))
            for label, param in proc_options.items():
                info = param[1] if isinstance(param, list) and len(param) > 1 and isinstance(param[1], list) else None
                options.append((label, lambda label=label, param=param: self._engine_option(label, param),
                                info[0] if info else None, info[1] if info else None))
        if options:
            self._from_options = True
            self.ui.show_options(title, options)

    def _engine_option(self, label, param):
        cb = getattr(self.ui.current_processor.engine, "preset_options_cb", None)
        if callable(cb):
            cb(label, param[0] if isinstance(param, list) else param)

    def _toggle_fav(self, preset, bank=None):
        proc = self.ui.current_processor
        # The engine records the processor's bank with the favourite: the preset's own (flat list)
        saved = proc.bank_info
        if bank:
            proc.bank_info = bank
        try:
            proc.toggle_preset_fav(preset)
        finally:
            proc.bank_info = saved
        proc.load_preset_list()
        self.fill(keep=True)
        self.show_preset_options()

    def _rename_preset(self, preset, new_name, bank=None):
        proc = self.ui.current_processor
        self._preset_cache.clear()
        new_name = new_name.strip()
        if new_name and new_name != preset[2]:
            try:
                proc.engine.rename_preset(bank or proc.bank_info, preset, new_name)
                if proc.preset_info and preset[0] == proc.preset_info[0]:
                    self.state_manager.start_busy("set preset")
                    try:
                        proc.set_preset_by_id(preset[0])
                    finally:
                        self.state_manager.end_busy("set preset")
            except Exception as e:
                logging.error(f"Failed to rename preset => {e}")
        self.fill(keep=True)

    def _delete_preset(self, preset, bank=None):
        proc = self.ui.current_processor
        self._preset_cache.clear()
        try:
            count = proc.engine.delete_preset(bank or proc.bank_info, preset)
            proc.remove_preset_fav(preset)
            self.fill(keep=True)
            if count == 0 and not self.flat:
                self.ui.back()
        except Exception as e:
            logging.error(f"Failed to delete preset => {e}")

    def _scan(self):
        proc = self.ui.current_processor
        self._preset_cache.clear()
        self.ui.chain_manager.reload_engine_preset_info(proc.eng_code)
        self.ui.cuia_bank_preset()

    # Saving (zynthian_gui_save_preset): the bank (or a new one), then the name

    def _save_new(self):
        proc = self.ui.current_processor
        self._save_bank_info = None
        self._save_create_bank = None
        bank_list = proc.get_bank_list()
        if not bank_list or proc.auto_save_bank:
            self._save_ask_name()
            return
        options = []
        index = proc.get_bank_index()
        if callable(getattr(proc.engine, "create_user_bank", None)):
            options.append(("***New bank***", lambda: self.ui.show_keyboard(self._save_new_bank, "NewBank",
                                                                           "New bank name"), None, None))
            index += 1
        for bank in bank_list:
            if bank[0] == "*FAVS*":
                index -= 1
            elif bank[0]:
                options.append((bank[2], lambda bank=bank: self._save_in_bank(bank), None, None))
            else:
                options.append(("None", lambda: self._save_in_bank(["", None, "None", None]), None, None))
        if options:
            self.ui.show_options("Select bank...", options, max(0, index))
        else:
            self._save_ask_name()

    def _save_new_bank(self, name):
        self._save_bank_info = "NEW_BANK"
        self._save_create_bank = name.strip()
        self._save_ask_name()

    def _save_in_bank(self, bank):
        self._save_bank_info = bank
        self._save_ask_name()

    def _save_ask_name(self):
        proc = self.ui.current_processor
        name = f"{proc.preset_name} COPY" if proc.preset_name else "New Preset"
        self.ui.show_keyboard(self._save_named, name, "Preset name")

    def _save_named(self, name):
        proc = self.ui.current_processor
        name = name.strip()
        if not name:
            return
        if self._save_create_bank:
            urid = proc.engine.get_user_bank_urid(self._save_create_bank)
            self._save_bank_info = (urid, None, self._save_create_bank, None)
        if proc.engine.preset_exists(self._save_bank_info, name):
            self.ui.confirm(f"Do you want to overwrite preset '{name}'?", lambda: self._do_save(name))
        else:
            self._do_save(name)

    def _save_overwrite(self, name, bank=None):
        proc = self.ui.current_processor
        self._save_create_bank = None
        self._save_bank_info = bank or proc.bank_info
        self.ui.confirm(f"Do you want to overwrite preset '{name.strip()}'?", lambda: self._do_save(name.strip()))

    def _do_save(self, name):
        proc = self.ui.current_processor
        self._preset_cache.clear()
        sm = self.state_manager
        sm.start_busy("Save Preset", f"Saving preset {name}")
        try:
            if self._save_create_bank:
                proc.engine.create_user_bank(self._save_create_bank)
            uri = proc.engine.save_preset(self._save_bank_info, name)
            if uri:
                if self._save_bank_info:
                    proc.set_bank_by_id(self._save_bank_info[0])
                proc.load_preset_list()
                proc.set_preset_by_id(uri)
            else:
                logging.error(f"Can't save preset '{name}'")
        except Exception as e:
            logging.error(e)
        finally:
            self._save_create_bank = None
            sm.end_busy("Save Preset")
        self.fill()

    def enters(self, index):
        """Only a preset sub-folder (the audio player's folders) is a level: a preset is loaded
        (ARROW_RIGHT does nothing there)"""
        e = self._entry_at(index)
        row = e["data"] if e and not self.flat else None
        return bool(row) and isinstance(row[0], str) and os.path.isdir(row[0])

    def switch(self, i, t):
        """Switch 1 short (BACK on the kits, the keyboard's Escape): the banks (more than one);
        2 short: favourites on / off (zynthian_gui_preset.switch). The BACK CUIA (the V5's BACK
        key) goes back, as in Tk."""
        proc = self.ui.current_processor
        if proc is None:
            return False
        # Also from the flat list: it is the only way to the bank list without a BANK_PRESET
        # key (a V4 kit), as BANK_PRESET and chain control open the flat list directly
        if i == 1 and t == "S" and len(proc.get_bank_list()) > 1:
            self.ui.replace_screen("bank")
            return True
        if i == 2 and t == "S":
            proc.toggle_show_fav_presets()
            self.fill()
            return True
        return False

    def back(self):
        """Up one preset sub-folder (zynthian_gui_preset.browse_back; the audio player's folders):
        the parent's (preset_subdir_info[3]), the folder left selected (its index, [1])"""
        proc = self.ui.current_processor
        sdi = proc.preset_subdir_info if proc else None
        if sdi:
            proc.preset_subdir_info = sdi[3]
            self.fill()
            self.setIndex(sdi[1])
            return True
        return False
