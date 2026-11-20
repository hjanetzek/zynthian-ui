"""zyngui.screens for controller drivers in the Qt UI.

Some drivers (zyngine/ctrldev) reach into the Tk UI's screen objects, from their MIDI thread:
screens["mixer"].launcher_mode / edit_pad() (APC40 mk2, Launchpad Pro mk2),
screens["launcher"].edit_pattern() / refresh_launchers() (base_ui mode handlers, APC Key 25 mk2),
screens["pattern_editor"].undo_pattern() / redo_pattern() / load_pattern() /
refresh_sequence_info() (APC40 mk2, APC Key 25 mk2), screens["arranger"] (base_ui, disabled
there). The Qt UI has no such objects; these stand-ins do the same with the Qt screens, in the GUI
thread (reads are plain values). Other attributes raise AttributeError and other keys KeyError, as
before.
"""

import logging


class _Shim:
    def __init__(self, ui):
        self._ui = ui

    def _gui(self, fn):
        self._ui._gui.run(fn)


class MixerShim(_Shim):
    """Tk's zynthian_gui_mixer (screens "mixer", "launcher", "root")"""

    @property
    def launcher_mode(self):
        return self._ui.current_screen == "launcher"

    def set_launcher_mode(self, mode=None):
        if mode is None:
            mode = not self.launcher_mode
        self._ui.show_screen("launcher" if mode else "mixer")

    def edit_pad(self):
        self._gui(self._ui.launcher.edit_pad)

    def edit_pattern(self):
        """The selected pad's pattern (zynthian_gui_mixer.edit_pattern)"""
        self._ui.show_screen("pattern_editor")

    def refresh_launchers(self, force=False):
        self._ui.launcher.padsChanged.emit()


class PatternEditorShim(_Shim):
    """Tk's zynthian_gui_pated_notes (screen "pattern_editor")"""

    @property
    def _pe(self):
        return self._ui.pattern_editor

    def __getattr__(self, name):
        # Read-only state the drivers look at (pattern, phrase, sequence, keymap, ...)
        if name in ("pattern", "phrase", "sequence", "channel", "keymap", "bank"):
            return getattr(self._pe, name, None)
        if name == "selected_cell":
            return list(self._pe.cursor)
        raise AttributeError(name)

    def undo_pattern(self):
        self._gui(self._pe.undo)

    def redo_pattern(self):
        self._gui(self._pe.redo)

    def undo_pattern_all(self):
        self._gui(self._pe.undo_all)

    def redo_pattern_all(self):
        self._gui(self._pe.redo_all)

    def refresh_sequence_info(self):
        self._gui(self._reload)

    def load_pattern(self, index):
        self._gui(self._reload)

    def _reload(self):
        # The Qt editor follows zynseq's selected phrase and the active chain (load)
        pe = self._pe
        if pe._shown:
            pe.load()
            pe._reload_events()
            pe.patternChanged.emit()


class ArrangerShim(_Shim):
    """Tk's arranger is gone (tomita); base_ui's calls to it are disabled: ignore them"""

    def __getattr__(self, name):
        def ignored(*args, **kwargs):
            logging.debug(f"Qt UI: no arranger, {name}() ignored")
        return ignored


class TkScreens(dict):
    """The keys drivers use, with the shims"""

    def __init__(self, ui):
        mixer = MixerShim(ui)
        super().__init__(mixer=mixer, launcher=mixer, root=mixer,
                         pattern_editor=PatternEditorShim(ui), arranger=ArrangerShim(ui))
