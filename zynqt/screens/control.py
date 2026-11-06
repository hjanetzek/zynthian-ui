"""Chain control (zynthian_gui_chain_control + zynthian_gui_control): the chain's processors, the
controller pages of the chain and its processors, and the four controllers of the selected page.

Controller values change through the controllers (set_value/nudge), so MIDI learn, feedback and
snapshots work as in the Tk UI. Changes from MIDI or the engine set zctrl.is_dirty, which a timer
checks while the screen is shown (as zynthian_gui's plot_zctrls).
"""

import logging

from PySide6.QtCore import QObject, QTimer, Property, Signal, Slot

from zyngui import zynthian_audio_file_data as afd
from zyngui import zynthian_widget_data as wd
from zyngui import zynthian_sooperlooper_data as sld
from zyngui.zynthian_midi_learn_data import (MIDI_LEARNING_CHAIN, MIDI_LEARNING_DISABLED, MIDI_LEARNING_GLOBAL,
                                             binding, note_range_learn)
from zynqt.models.audio_file import AudioFileView
from zynqt.models.organelle import OrganelleView
from zynqt.models.widgets import EnvelopeView, FilterView, PluginView, EuclidSeqView, SooperLooperView
from zynqt.screens.base import EntryModel, entry, separator
from zynqt.screens.controller_options import show_controller_options


class ControllerProxy(QObject):
    """One of the four controller slots"""

    changed = Signal()

    def __init__(self, index, control):
        super().__init__(control)
        self.index = index
        self.control = control      # the ChainControl (MIDI learn state)
        self.zctrl = None

    def set_zctrl(self, zctrl):
        self.zctrl = zctrl
        self.changed.emit()

    def refresh(self, force=False):
        if self.zctrl is not None and (self.zctrl.is_dirty or force):
            self.zctrl.is_dirty = False
            self.changed.emit()

    @Property(bool, notify=changed)
    def active(self):
        return self.zctrl is not None

    @Property(str, notify=changed)
    def name(self):
        return (self.zctrl.short_name or self.zctrl.name) if self.zctrl else ""

    @Property(str, notify=changed)
    def valueText(self):
        if self.zctrl is None:
            return ""
        try:
            label = self.zctrl.get_value2label()
        except Exception:
            label = self.zctrl.value
        if isinstance(label, float):
            return f"{label:.3g}" if abs(label) < 1000 else f"{label:.0f}"
        return str(label)

    @Property(float, notify=changed)
    def fraction(self):
        """Position 0..1 for the display (log scale as MIDI mapping)"""
        z = self.zctrl
        if z is None:
            return 0.0
        if isinstance(z.value, str):
            # Text values (paths, names): the position of the value in the labels, if any
            labels = getattr(z, "labels", None) or []
            if z.value in labels and len(labels) > 1:
                return labels.index(z.value) / (len(labels) - 1)
            return 0.0
        try:
            return max(0.0, min(1.0, z.get_ctrl_midi_val() / 127))
        except Exception:
            rng = z.value_range or 1
            return max(0.0, min(1.0, (z.value - z.value_min) / rng))

    @Property(bool, notify=changed)
    def isToggle(self):
        return bool(self.zctrl and self.zctrl.is_toggle)

    def _binding(self):
        """(text, kind) shown for the MIDI binding (zynthian_gui_controller.set_midi_bind): kind
        "learn" / "learnGlobal" (learning it, or any while learning without one chosen), "xy"
        (an X-Y touchpad axis), "abs", "chain", "zynstep" or "" (none)"""
        z = self.zctrl
        if z is None or z.is_path:
            return "", ""
        c = self.control
        sm = c.ui.state_manager
        if c.midi_learning and (c.learn_preselect or z == sm.get_midi_learn_zctrl()):
            return "??#??", "learnGlobal" if c.midi_learning == MIDI_LEARNING_GLOBAL else "learn"
        if z == sm.zctrl_x:
            return "X", "xy"
        if z == sm.zctrl_y:
            return "Y", "xy"
        return binding(c.chain_manager, z) or ("", "")

    @Property(str, notify=changed)
    def bindText(self):
        return self._binding()[0]

    @Property(str, notify=changed)
    def bindKind(self):
        return self._binding()[1]

    @Slot()
    def options(self):
        """Long press: the controller's options (MIDI learn, ...)"""
        if self.zctrl is not None:
            show_controller_options(self.control, self.index)

    @Slot()
    def touched(self):
        """Touched while MIDI learning: learn this one (zynthian_gui_control.zctrl_touch)"""
        c = self.control
        if c.midi_learning and self.zctrl is not None and self.zctrl != c.ui.state_manager.get_midi_learn_zctrl():
            c.midi_learn(self.index, c.midi_learning)

    @Slot(int)
    def nudge(self, steps):
        if self.zctrl is not None and steps:
            self.zctrl.nudge(steps)
            self.zctrl.is_dirty = False
            self.changed.emit()

    @Slot()
    def toggle(self):
        if self.zctrl is not None:
            self.zctrl.toggle()
            self.zctrl.is_dirty = False
            self.changed.emit()


class ChainControl(QObject):
    name = "chain_control"

    processorsChanged = Signal()
    pageChanged = Signal()
    learnChanged = Signal()

    def __init__(self, ui, parent=None):
        super().__init__(parent)
        self.ui = ui
        self.chain_manager = ui.chain_manager
        self.pages = EntryModel(self)
        self._page = 0
        self._processors = []
        self.controllers = [ControllerProxy(i, self) for i in range(4)]
        self._shown = False
        # A processor without chain (tempo, ALSA mixer), shown instead of the active chain
        self.special_processor = None
        self._timer = QTimer(self, interval=50)
        self._timer.timeout.connect(self._refresh)
        ui.bridge.processorControllersChanged.connect(self._rebuild_if_shown)
        # Waveform of an audio file processor (audio player, clippy, samplv1), as Tk's widget
        self.audio_view = AudioFileView(ui, self)
        self.envelope_view = EnvelopeView(self)
        self.filter_view = FilterView(self)
        self.plugin_view = PluginView(self)
        self.euclid_view = EuclidSeqView(self)
        self.organelle_view = OrganelleView(self)
        self.sl_view = SooperLooperView(ui, self)
        self._widget_type = ""      # "audio_file", "envelope", "filter" or "" (none)
        ui.bridge.chainsChanged.connect(self._rebuild_if_shown)
        # MIDI learn (zynthian_gui_control): MIDI_LEARNING_*; learn_preselect: learning without a
        # controller chosen (all show "??#??", touching one chooses it); note_learn: the key range
        # page learning its notes (zynthian_gui_midi_key_range: -1, then the first note)
        self.midi_learning = MIDI_LEARNING_DISABLED
        self.learn_preselect = False
        self.note_learn = 0
        ui.bridge.midiCc.connect(self._midi_cc)
        ui.bridge.midiNoteOn.connect(self._midi_note_on)

    # Shown / hidden (ZynUI)

    def build(self):
        self._build()
        self._shown = True
        self._timer.start()
        if self._widget_type == "audio_file":
            self.audio_view.start()

    def hide(self):
        self._shown = False
        self._timer.stop()
        self.audio_view.stop()
        self.exit_midi_learn()

    def rebuild(self):
        self._build()

    def _rebuild_if_shown(self):
        if self._shown:
            self._build()

    def _refresh(self):
        for c in self.controllers:
            c.refresh()
        if self._widget_type == "envelope":
            self.envelope_view.refresh()
        elif self._widget_type == "filter":
            self.filter_view.refresh()
        elif self._widget_type == "plugin":
            self.plugin_view.refresh()
        elif self._widget_type == "sooperlooper":
            self.sl_view.refresh()

    # Contents

    def _build(self):
        if self.special_processor:
            chain = None
            processors = [self.special_processor]
            curproc = self.special_processor
        else:
            chain = self.chain_manager.get_active_chain()
            processors = chain.get_processors() if chain else []
            curproc = self.ui.current_processor
            if curproc not in processors:
                curproc = chain.current_processor if chain else None
                self.ui.set_current_processor(curproc)
        self._processors = processors
        self.processorsChanged.emit()

        # Pages as zynthian_gui_control.fill_list: chain controllers, then each processor's
        entries = []
        page = None
        if chain and chain.zctrls:
            entries.append(separator("CHAIN"))
            zctrls = list(chain.zctrls)
            for j in range(0, len(zctrls), 4):
                entries.append(entry(f"Controllers {j // 4 + 1}", data=("chain", None, zctrls[j:j + 4])))
        for proc in processors:
            screens = proc.get_ctrl_screens()
            if not screens:
                continue
            entries.append(separator(proc.engine.name.split("/")[-1]))
            for j, title in enumerate(screens):
                if proc == curproc and j == proc.get_current_screen_index():
                    page = len(entries)
                entries.append(entry(title, data=("proc", proc, j)))
        self.pages.set_entries(entries)
        if page is None:
            page = next((i for i, e in enumerate(entries) if not e["separator"]), None)
        self._page = -1
        if page is None:
            # No controller page (e.g. no audio levels on this device): empty slots
            for c in self.controllers:
                c.set_zctrl(None)
            self._set_widget(None)
            self.pageChanged.emit()
        else:
            self.setPage(page)

    @Property(bool, notify=processorsChanged)
    def isChain(self):
        return self.special_processor is None

    @Property(bool, notify=processorsChanged)
    def isMidi(self):
        chain = self.chain_manager.get_active_chain()
        return bool(self.special_processor is None and chain and chain.is_midi())

    @Property(bool, notify=processorsChanged)
    def hasAudioIn(self):
        """Audio input routing (as the Tk sidebar: chains with audio thru, not the main chain)"""
        chain = self.chain_manager.get_active_chain()
        return bool(self.special_processor is None and chain and chain.audio_thru and chain.zynmixer_proc
                    and chain.zynmixer_proc.eng_code != "MR")

    @Property(bool, notify=processorsChanged)
    def isAudio(self):
        chain = self.chain_manager.get_active_chain()
        return bool(self.special_processor is None and chain and chain.is_audio())

    @Property("QVariantList", notify=processorsChanged)
    def processors(self):
        current = self.ui.current_processor
        return [{"name": p.get_name() if hasattr(p, "get_name") else p.name,
                 "type": p.type or "", "current": p == current} for p in self._processors]

    @Property(QObject, constant=True)
    def pageModel(self):
        return self.pages

    @Property(int, notify=pageChanged)
    def page(self):
        return self._page

    @Property(QObject, constant=True)
    def c0(self):
        return self.controllers[0]

    @Property(QObject, constant=True)
    def c1(self):
        return self.controllers[1]

    @Property(QObject, constant=True)
    def c2(self):
        return self.controllers[2]

    @Property(QObject, constant=True)
    def c3(self):
        return self.controllers[3]

    @Slot(int)
    def setPage(self, index):
        entries = self.pages.entries
        if not 0 <= index < len(entries) or entries[index]["separator"] or index == self._page:
            return
        self._page = index
        kind, proc, arg = entries[index]["data"]
        if kind == "chain":
            zctrls = arg
        else:
            if proc != self.ui.current_processor and not self.special_processor:
                self.ui.set_current_processor(proc)
                self.processorsChanged.emit()
            proc.set_current_screen_index(arg)
            title = entries[index]["title"]
            try:
                zctrls = proc.get_ctrl_screen(title)
            except Exception as e:
                logging.error(f"controller page '{title}': {e}")
                zctrls = []
        for i, c in enumerate(self.controllers):
            c.set_zctrl(zctrls[i] if i < len(zctrls) else None)
        self._set_widget(proc if kind != "chain" else None, zctrls)
        self.pageChanged.emit()

    def _set_widget(self, proc, zctrls=()):
        """The page's widget, as zynthian_gui_control: from the page's controllers (envelope,
        filter, audio file path), else the engine's own (audio player, clippy)"""
        wtype, file_zctrl = wd.screen_type(zctrls) if proc else (None, None)
        plugin = wd.plugin_widget(proc) if wtype is None else None
        if plugin == "euclidseq":
            wtype = "euclid"
            self.euclid_view.set_processor(proc)
        elif plugin == "organelle":
            wtype = "organelle"
            self.organelle_view.set_processor(proc)
        elif plugin == "sooperlooper":
            wtype = "sooperlooper"
            if self.sl_view.processor is not proc:
                self.sl_view.set_processor(proc)
        elif plugin:
            wtype = "plugin"
            if self.plugin_view.processor is not proc:
                self.plugin_view.set_processor(proc, plugin)
        if wtype is None and proc is not None:
            gui = getattr(proc.engine, "custom_gui_fpath", None)
            if afd.engine_type(proc) != afd.ENG_NONE or (gui and gui.endswith("zynthian_widget_audio_file.py")):
                wtype = "audio_file"
        if wtype in ("envelope", "filter"):
            group = proc.get_group_zctrls(zctrls[0].group_symbol) if zctrls and zctrls[0] else list(zctrls)
            (self.envelope_view if wtype == "envelope" else self.filter_view).set_group(group)
        if wtype == "audio_file":
            self.audio_view.set_processor(proc, file_zctrl)
            if self._shown:
                self.audio_view.start()
        else:
            self.audio_view.stop()
        self._widget_type = wtype or ""

    @Property(str, notify=pageChanged)
    def widgetType(self):
        return self._widget_type

    @Property(QObject, constant=True)
    def waveform(self):
        return self.audio_view

    @Property(QObject, constant=True)
    def envelope(self):
        return self.envelope_view

    @Property(QObject, constant=True)
    def filterView(self):
        return self.filter_view

    @Property(QObject, constant=True)
    def pluginView(self):
        return self.plugin_view

    @Property(QObject, constant=True)
    def euclidView(self):
        return self.euclid_view

    @Property(QObject, constant=True)
    def organelleView(self):
        return self.organelle_view

    @Property(QObject, constant=True)
    def sooperLooperView(self):
        return self.sl_view

    @Slot(int)
    def selectProcessor(self, i):
        if 0 <= i < len(self._processors):
            proc = self._processors[i]
            for row, e in enumerate(self.pages.entries):
                if not e["separator"] and e["data"][0] == "proc" and e["data"][1] == proc:
                    self.setPage(row + proc.get_current_screen_index())
                    return

    def move_page(self, step):
        entries = self.pages.entries
        i = self._page + step
        while 0 <= i < len(entries) and entries[i]["separator"]:
            i += step
        if 0 <= i < len(entries):
            self.setPage(i)

    def navigate(self, what):
        if what == "up":
            self.move_page(-1)
        elif what == "down":
            self.move_page(1)
        elif what == "select_bold":
            self.ui.cuia_bank_preset()

    def back(self):
        if self.midi_learning or self.note_learn:
            self.exit_midi_learn()
            return True
        return False

    # Transport keys (zynthian_gui_control passes them to its widget): the audio player / clippy
    # widget plays its file or clip; SooperLooper in ALT mode. Else the global transport.

    def _transport(self, action):
        if self._widget_type == "audio_file" and self.audio_view.processor is not None:
            v = self.audio_view
            return afd.transport(action, v.processor, v.eng_type, v.clip_info, self.ui.state_manager)
        if self._widget_type == "sooperlooper" and self.ui.alt_mode and self.sl_view.processor is not None:
            proc = self.sl_view.processor
            return sld.alt_transport(action, proc, proc.engine.get_monitors_dict() or {})
        return False

    def cuia_toggle_record(self, params=None):
        return self._transport("record")

    def cuia_stop(self, params=None):
        return self._transport("stop")

    def cuia_play(self, params=None):
        return self._transport("play")

    def cuia_toggle_play(self, params=None):
        return self._transport("toggle_play")

    # MIDI learn (zynthian_gui_control; the learning itself is in the state / chain managers)

    def refresh_bindings(self):
        for c in self.controllers:
            c.changed.emit()

    def _is_key_range(self):
        return getattr(self.special_processor, "zmop_index", None) is not None and \
            hasattr(self.special_processor, "low")

    @Property(str, notify=learnChanged)
    def learnText(self):
        if self.note_learn:
            return "Learning the note range: play the lowest and the highest note"
        if not self.midi_learning:
            return ""
        how = "Global" if self.midi_learning == MIDI_LEARNING_GLOBAL else "Chain"
        if self.learn_preselect or self.ui.state_manager.get_midi_learn_zctrl() is None:
            return f"{how} MIDI learn: touch a control"
        return f"{how} MIDI learn: move a control on your MIDI device"

    def _set_learning(self, mode, preselect):
        self.midi_learning = mode
        self.learn_preselect = preselect
        self.refresh_bindings()
        self.learnChanged.emit()

    def enter_midi_learn(self, mode=MIDI_LEARNING_CHAIN, preselect=True):
        if mode > MIDI_LEARNING_DISABLED:
            self._set_learning(mode, preselect)

    @Slot()
    def stopLearn(self):
        self.exit_midi_learn()

    @Slot()
    def toggleLearn(self):
        self.toggle_midi_learn()

    def exit_midi_learn(self):
        if self.note_learn:
            self.note_learn = 0
            self.ui.state_manager.set_midi_learn(False)
            self.learnChanged.emit()
        if self.midi_learning:
            self.ui.state_manager.disable_learn_cc()
            self._set_learning(MIDI_LEARNING_DISABLED, False)

    def toggle_midi_learn(self, i=None):
        """CUIA TOGGLE_MIDI_LEARN: off -> chain -> global -> off (the ALSA mixer starts global);
        with a controller slot, learn that one. On the key range page: learn the note range"""
        if self._is_key_range():
            if self.note_learn:
                self.exit_midi_learn()
            else:
                self.note_learn = -1
                self.ui.state_manager.set_midi_learn(True)
                self.learnChanged.emit()
            return
        default = MIDI_LEARNING_GLOBAL if getattr(self.special_processor, "eng_code", None) == "MX" \
            else MIDI_LEARNING_CHAIN
        if i is not None:
            zctrl = self.controllers[i].zctrl if 0 <= i < 4 else None
            if zctrl is None:
                self.exit_midi_learn()
                return
            if zctrl != self.ui.state_manager.get_midi_learn_zctrl():
                self.midi_learn(i, self.midi_learning or default)
                return
        if self.midi_learning == MIDI_LEARNING_CHAIN:
            self._set_learning(MIDI_LEARNING_GLOBAL, i is None and self.learn_preselect)
        elif self.midi_learning == MIDI_LEARNING_GLOBAL:
            self.exit_midi_learn()
        else:
            self.enter_midi_learn(default, i is None)

    def midi_learn(self, i, mode=MIDI_LEARNING_CHAIN):
        zctrl = self.controllers[i].zctrl if 0 <= i < 4 else None
        if zctrl is not None and mode > MIDI_LEARNING_DISABLED:
            self.ui.state_manager.enable_learn_cc(zctrl)
            self.enter_midi_learn(mode, False)

    def _midi_cc(self, izmip, chan, num, val):
        """A CC while learning a controller: bind it (zynthian_gui_control.midi_learn_bind)"""
        zctrl = self.ui.state_manager.get_midi_learn_zctrl()
        if not self.midi_learning or zctrl is None or num >= 120:
            return
        if self.midi_learning == MIDI_LEARNING_GLOBAL:
            self.chain_manager.add_midi_learn(chan, num, zctrl, izmip)
        else:
            self.chain_manager.add_midi_learn(chan, num, zctrl)
        self.exit_midi_learn()

    def _midi_note_on(self, izmip, chan, note, vel):
        """A note while learning the key range page's note range"""
        if not self.note_learn or not self._is_key_range():
            return
        p = self.special_processor
        self.note_learn, low, high, done = note_range_learn(self.note_learn, note, p.low.value, p.high.value)
        if low != p.low.value:
            p.low.set_value(low)
        if high != p.high.value:
            p.high.set_value(high)
        for c in self.controllers:
            c.refresh(True)
        if done:
            self.exit_midi_learn()

    def midi_unlearn_action(self):
        """Clean the MIDI learn of all controllers of the current processor (confirmed)"""
        proc = self.ui.current_processor
        if proc is None:
            return
        question = f"Do you want to clean MIDI-learn for ALL controls in {proc.get_name()}"
        if proc.midi_chan is not None and 0 <= proc.midi_chan < 16:
            question += f" on MIDI channel {proc.midi_chan + 1}"

        def clean():
            self.chain_manager.clean_midi_learn(proc)
            self.refresh_bindings()
        self.ui.confirm(question + "?", clean)
