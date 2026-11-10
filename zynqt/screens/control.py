"""Chain control (zynthian_gui_chain_control + zynthian_gui_control): the chain's processors, the
controller pages of the chain and its processors, and the four controllers of the selected page.

Controller values change through the controllers (set_value/nudge), so MIDI learn, feedback and
snapshots work as in the Tk UI. Changes from MIDI or the engine set zctrl.is_dirty, which a timer
checks while the screen is shown (as zynthian_gui's plot_zctrls).
"""

import logging

from PySide6.QtCore import QObject, QTimer, Property, Signal, Slot

from zyngine.zynthian_signal_manager import zynsigman
from zyngui import zynthian_gui_config
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


def tk_plot(z):
    """The value as zynthian_gui_controller draws it (calculate_plot_values, plot_value_arc):
    (value text, arc start, arc sweep, sample text for the font size). Angles in QML's sense
    (degrees clockwise from 3 o'clock); the arc spans 300 degrees from the bottom left."""
    import math
    import os
    import re
    fmt = None
    if z.is_path:
        fmt = "{}"
    elif not isinstance(z.ticks, list) and not z.is_integer and not z.is_logarithmic:
        nf = getattr(z, "nudge_factor_fine", 0.1)
        fmt = "{:.3f}" if nf < 0.01 else "{:.2f}" if nf < 0.1 else "{:.1f}"
    labels = z.labels if isinstance(z.labels, list) else None
    plot = 0.0
    if z.ticks:
        n = len(z.ticks)
        try:
            i = z.get_value2index()
            text = str(z.labels[i])
            plot = (i + 1) / n if n > 2 else i
        except Exception:
            text = "ERR"
    elif z.is_path:
        text = os.path.split(z.value)[1] if z.value else "None"
    else:
        rng = z.value_range
        val = z.value
        try:
            if rng == 0:
                plot = 0.0
            elif z.is_logarithmic:
                if z.value_min < 0:
                    plot = math.log10((9 * val - (10 * z.value_min)) / rng)
                else:
                    plot = math.log10((9 * val - (10 * z.value_min - z.value_max)) / rng)
            elif z.value_min < 0:
                plot = val / rng
            else:
                plot = (val - z.value_min) / rng
        except (ValueError, TypeError, ZeroDivisionError):
            plot = 0.0
        if z.is_logarithmic:
            a = abs(val)
            fmt = "{:.3f}" if a < 10 else "{:.2f}" if a < 100 else "{:.1f}" if a < 1000 else "{:.0f}"
            text = fmt.format(val)
        elif fmt and -1000 < val < 1000:
            text = fmt.format(val)
        else:
            text = str(int(val))
    # Arc (Tk: counter-clockwise degrees)
    degmax = 300
    degd = -degmax * plot
    deg0 = 90 + degmax / 2
    if labels:
        n = len(labels)
        if n > 2:
            arc_len = max(5, degmax // n)
            deg0 += degd + arc_len
            degd = -arc_len
    elif z.value_range and z.value_min <= 0 <= z.value_max:
        deg0 += degmax * z.value_min / z.value_range
    # Sample text (calculate_value_font_size)
    if z.is_path or labels:
        # plot_value: labels and paths fit their own text (long labels: the longest word)
        sample = text
        words = text.split()
        if labels and len(text) > 10 and len(words) > 1:
            sample = max(words, key=len) + "..."
    elif fmt:
        sample = max([fmt.format(z.value_min), fmt.format(z.value_max)], key=len)
        sample = re.sub(r"[1-9]", "0", sample)
    elif z.is_logarithmic:
        sample = "00000" if z.value_max > 1000 else "000.0"
    else:
        sample = "0" * max(len(str(z.value_min)), len(str(z.value_max)))
    return text, -deg0, -degd, sample


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

    # Tk's look (the tk theme's Controller): value text, arc and font sample as
    # zynthian_gui_controller

    def _tk(self):
        try:
            return tk_plot(self.zctrl)
        except Exception as e:
            logging.debug(f"tk_plot: {e}")
            return "", 0.0, 0.0, "0"

    @Property(str, notify=changed)
    def tkValueText(self):
        return self._tk()[0] if self.zctrl is not None else ""

    @Property(float, notify=changed)
    def tkArcStart(self):
        return self._tk()[1] if self.zctrl is not None else 0.0

    @Property(float, notify=changed)
    def tkArcSweep(self):
        return self._tk()[2] if self.zctrl is not None else 0.0

    @Property(str, notify=changed)
    def tkValueSample(self):
        return self._tk()[3] if self.zctrl is not None else ""

    @Property(bool, notify=changed)
    def isPath(self):
        return bool(self.zctrl is not None and self.zctrl.is_path)

    @Property(bool, notify=changed)
    def readonly(self):
        return bool(self.zctrl is not None and getattr(self.zctrl, "readonly", False))

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
        self.nudge_fine(steps, False)

    def nudge_fine(self, steps, fine):
        if self.zctrl is not None and steps:
            self.zctrl.nudge(steps, fine=fine)
            self.zctrl.is_dirty = False
            self.changed.emit()

    def set_abs(self, val):
        """Set to a part of the range (val 0..1): ZYNPOT_ABS, as zynthian_gui_controller.zynpot_abs
        without pick-up"""
        z = self.zctrl
        if z is not None:
            z.set_value(z.value_min + val * z.value_range)
            z.is_dirty = False
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
    sidebarChanged = Signal()
    modeChanged = Signal()
    selectPathChanged = Signal()

    def __init__(self, ui, parent=None):
        super().__init__(parent)
        self.ui = ui
        self.chain_manager = ui.chain_manager
        self.pages = EntryModel(self)
        self._page = 0
        self._processors = []
        self.controllers = [ControllerProxy(i, self) for i in range(4)]
        self._shown = False
        self._sidebar_shown = True   # the processor list (Tk's chain sidebar)
        # Tk's modes (zynthian_gui_control / chain_control): "control" (the knobs turn the
        # controllers) or "select" (the chain is shown: knob 3 the page, knob 2 the processor)
        self._mode = "control"
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
        # Another chain selected while shown (arrows, switch 0): show it (Tk's cb_set_active_chain)
        ui.bridge.activeChainChanged.connect(self._active_chain_changed)
        # MIDI learn (zynthian_gui_control): MIDI_LEARNING_*; learn_preselect: learning without a
        # controller chosen (all show "??#??", touching one chooses it); note_learn: the key range
        # page learning its notes (zynthian_gui_midi_key_range: -1, then the first note)
        self.midi_learning = MIDI_LEARNING_DISABLED
        self.learn_preselect = False
        self.note_learn = 0
        ui.bridge.midiCc.connect(self._midi_cc)
        ui.bridge.midiNoteOn.connect(self._midi_note_on)
        self.pageChanged.connect(self.selectPathChanged)
        self.learnChanged.connect(self.selectPathChanged)
        self.modeChanged.connect(self.selectPathChanged)

    # The processor list on the left (zynthian_gui_chain_control's sidebar): SHOW_SIDEBAR,
    # HIDE_SIDEBAR, TOGGLE_SIDEBAR

    @Property(bool, notify=sidebarChanged)
    def sidebarShown(self):
        return self._sidebar_shown

    def show_sidebar(self, show):
        if show != self._sidebar_shown:
            self._sidebar_shown = show
            self.sidebarChanged.emit()
        zynsigman.send_queued(zynsigman.S_GUI, zynsigman.SS_GUI_SHOW_SIDEBAR, shown=show)

    def cuia_show_sidebar(self, params=None):
        self.show_sidebar(True)
        return True

    def cuia_hide_sidebar(self, params=None):
        self.show_sidebar(False)
        return True

    def cuia_toggle_sidebar(self, params=None):
        self.show_sidebar(not self._sidebar_shown)
        return True

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

    def _active_chain_changed(self):
        if not self._shown or self.special_processor is not None:
            return
        chain = self.chain_manager.get_active_chain()
        procs = chain.get_processors() if chain else []
        if chain and self.ui.current_processor not in procs:
            self.ui.set_current_processor(chain.current_processor)
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
            # The processor's header also without pages (Tk: the audio player without a file)
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

    # The chain as Tk's side chain draws it (zynthian_side_chain.build_graph): chain options, MIDI
    # input, chain controllers, the MIDI tools, the synth (or MIDI output), audio input, the audio
    # effects, audio output; kind sets the colour, link the line to the next node

    _NODE_SCREENS = {"chain_options": "chain_options", "midi_input": "midi_in", "midi_output": "midi_out",
                     "audio_in": "audio_in", "audio_out": "audio_out"}

    def _chain_nodes(self):
        chain = None if self.special_processor else self.chain_manager.get_active_chain()
        nodes = []
        if chain is None:
            return nodes

        def add(title, proc, slot=None):
            ptype = proc if isinstance(proc, str) else proc.type
            nodes.append({"title": title, "proc": proc, "slot": slot,
                          "dst": ptype in ("chain_controllers", "MIDI Synth", "Audio Effect", "MIDI Tool", "Special",
                                           "midi_output", "audio_out"),
                          "src": ptype in ("chain_controllers", "MIDI Synth", "Audio Effect", "MIDI Tool", "Special",
                                           "Audio Generator", "midi_input", "audio_in")})

        add("Chain Options" + (f"\n{chain.title}" if chain.title else ""), "chain_options")
        if chain.is_midi():
            ch = f"CH#{chain.midi_chan + 1:02}" if chain.midi_chan is not None and chain.midi_chan < 16 else "CH#ALL"
            add(f"MIDI Input\n{ch}", "midi_input")
        if chain.zctrls:
            add("Chain\nControllers", "chain_controllers")
        for i, slot in enumerate(chain.midi_slots):
            for proc in slot:
                add(proc.get_name(), proc, ("midi", i))
        if chain.synth_slots:
            for i, slot in enumerate(chain.synth_slots):
                for proc in slot:
                    add(proc.get_name(), proc, ("synth", i))
        elif chain.is_midi():
            add("MIDI Output", "midi_output")
        if chain.audio_thru and chain.zynmixer_proc and chain.zynmixer_proc.eng_code != "MR":
            add("Audio Input", "audio_in")
        for i, slot in enumerate(chain.audio_slots):
            for proc in slot:
                add(proc.get_name(), proc, ("audio", i))
        if chain.is_audio():
            add("Audio Output", "audio_out")
        return nodes

    @Property("QVariantList", notify=processorsChanged)
    def chainNodes(self):
        nodes = self._chain_nodes()
        self._nodes = nodes
        out = []
        for i, n in enumerate(nodes):
            proc = n["proc"]
            nxt = nodes[i + 1] if i + 1 < len(nodes) else None
            if isinstance(proc, str):
                kind = {"midi_input": "midi", "midi_output": "midi", "chain_controllers": "midi",
                        "audio_in": "audio", "audio_out": "audio"}.get(proc, "other")
                bypassed = False
            else:
                kind = {"MIDI Input": "midi", "MIDI Output": "midi", "MIDI Tool": "midi", "MIDI Synth": "synth",
                        "Audio Generator": "synth", "Audio Input": "audio", "Audio Output": "audio",
                        "Audio Effect": "audio", "Special": "special"}.get(proc.type, "other")
                try:
                    bypassed = bool(proc.is_bypassed())
                except Exception:
                    bypassed = False
            # Line to the next node: two lines between parallel processors, one into a
            # destination, half of one out of a source
            if (nxt and not isinstance(proc, str) and not isinstance(nxt["proc"], str)
                    and proc.type == nxt["proc"].type and n["slot"] == nxt["slot"]):
                link = "parallel"
            elif n["src"]:
                link = "full" if nxt and nxt["dst"] else "half"
            else:
                link = ""
            out.append({"title": n["title"], "kind": kind, "link": link, "bypassed": bypassed,
                        "isProcessor": not isinstance(proc, str)})
        return out

    @Property(int, notify=pageChanged)
    def chainNode(self):
        """The selected side chain node: the chain controllers on a chain page, else the
        current processor"""
        nodes = getattr(self, "_nodes", None) or self._chain_nodes()
        entries = self.pages.entries
        on_chain_page = 0 <= self._page < len(entries) and entries[self._page]["data"] \
            and entries[self._page]["data"][0] == "chain"
        for i, n in enumerate(nodes):
            if on_chain_page and n["proc"] == "chain_controllers":
                return i
            if not on_chain_page and n["proc"] is self.ui.current_processor:
                return i
        return -1

    @Slot(int)
    def nodeTapped(self, i):
        """A tap on a side chain node (zynthian_side_chain.on_release): a processor's pages, a
        second tap its options; the other nodes open their screen (Tk: a subscreen)"""
        nodes = getattr(self, "_nodes", None) or self._chain_nodes()
        if not 0 <= i < len(nodes):
            return
        proc = nodes[i]["proc"]
        if self.ui.movingProcessor:
            self.ui.endMoveProcessor()
        if proc == "chain_controllers":
            first = next((r for r, e in enumerate(self.pages.entries)
                          if not e["separator"] and e["data"][0] == "chain"), None)
            if first is not None:
                self.setPage(first)
        elif isinstance(proc, str):
            self.ui.openChainScreen(self._NODE_SCREENS[proc])
        elif i == self.chainNode:
            self.ui.show_screen("processor_options")
        else:
            self.selectProcessor(self._processors.index(proc) if proc in self._processors else -1)

    @Slot(int)
    def nodeLongPressed(self, i):
        """Long press on a processor node: move it (zynthian_side_chain.on_long_press)"""
        nodes = getattr(self, "_nodes", None) or self._chain_nodes()
        if 0 <= i < len(nodes) and not isinstance(nodes[i]["proc"], str):
            proc = nodes[i]["proc"]
            if proc in self._processors:
                self.selectProcessor(self._processors.index(proc))
            if self.chain_manager.can_move_processor(proc):
                self.ui.start_move_processor(proc, stay=True)

    @Property(str, notify=selectPathChanged)
    def selectPath(self):
        """The title as zynthian_gui_control.set_select_path: the processor's preset path (with
        the MIDI learn mode while learning), else the chain's title"""
        proc = self.ui.current_processor
        if proc is not None:
            if self._mode == "control" and self.midi_learning:
                kind = "GLOBAL" if self.midi_learning == MIDI_LEARNING_GLOBAL else "CHAIN"
                return f"{proc.get_basepath()}/{kind} Control MIDI-Learn"
            return proc.get_presetpath()
        chain = self.chain_manager.get_active_chain()
        return chain.get_title() if chain else ""

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
        if wtype == "drawbar":
            wtype = None  # No Qt drawbar widget (yet): the controllers are shown
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

    def select_mixer_processor(self, page=1):
        """The chain's mixer controls (zynthian_gui_control.select_mixer_processor): page
        number page of its audio mixer processor"""
        rows = [row for row, e in enumerate(self.pages.entries)
                if not e["separator"] and e["data"][0] == "proc"
                and getattr(e["data"][1], "eng_code", None) in ("MI", "MR")]
        if rows:
            self.setPage(rows[min(page, len(rows) - 1)])

    # Knobs, switches and keys, as zynthian_gui_chain_control + zynthian_gui_control

    @Property(bool, notify=modeChanged)
    def selectMode(self):
        return self._mode == "select"

    def set_mode(self, mode):
        if mode != self._mode:
            if mode == "select":
                self.exit_midi_learn()
            self._mode = mode
            self.modeChanged.emit()

    def _knob_controller(self, i):
        """The controller knob i turns (the layout's ctrl_order), or None"""
        order = list(zynthian_gui_config.layout.get("ctrl_order", (0, 1, 2, 3)))
        return self.controllers[order.index(i)] if i in order else None

    def _processor_step(self, step):
        """The chain's previous / next processor (Tk: the chain sidebar's cursor)"""
        procs = self._processors
        if not procs:
            return
        cur = self.ui.current_processor
        i = procs.index(cur) if cur in procs else 0
        i = max(0, min(len(procs) - 1, i + step))
        self.selectProcessor(i)

    def zynpot(self, i, d):
        """zynthian_gui_chain_control.zynpot_cb: in select mode knob 2 the processor, knob 3 the
        page; in control mode knob i its controller (learning it while MIDI learning)"""
        if self._mode == "select":
            if i == 2 and self.isChain:
                self._processor_step(1 if d > 0 else -1)
            elif i == zynthian_gui_config.select_ctrl:
                self.move_page(1 if d > 0 else -1)
            return True
        c = self._knob_controller(i)
        if c is not None and c.zctrl is not None:
            # Fine while the knob is pushed (push-rotate, kits: zynthian_gui_controller.zynpot_cb)
            c.nudge_fine(d, self.ui.zynpot_push_rotate(i))
            if self.midi_learning:
                self.midi_learn(c.index, self.midi_learning)
        return True

    def switch(self, i, t):
        """zynthian_gui_chain_control.switch (+ the control subscreen's): bold while MIDI
        learning the controller's options; 3 bold bank / preset; 0 short rotate the chains; 1
        bold the main menu; 2 in select mode the processor's select"""
        if t == "B" and self.midi_learning:
            c = self._knob_controller(i)
            if c is not None:
                c.options()
            return True
        if i == 3 and t == "B":
            self.ui.cuia_bank_preset()
            return True
        if i == 0 and t == "S":
            if self.isChain:
                self.chain_manager.rotate_chain()
            return True
        if i == 1 and t == "B" and self.isChain:
            # zynthian_gui_chain_control; the special processors' screens (Tk's plain control
            # screen) take the default: the root
            self.ui.show_screen("main_menu")
            return True
        if i == 2 and self._mode == "select":
            self._processor_select(t)
            return True
        return False

    def _processor_select(self, t):
        """Select on the chain sidebar (zynthian_side_chain.switch_select): short the
        processor's options, bold move it (select again ends the move)"""
        proc = self.ui.current_processor
        if self.ui.movingProcessor:
            self.ui.endMoveProcessor()
            if t == "S":
                return
        if proc is None:
            return
        if t == "S":
            self.ui.show_screen("processor_options")
        elif t == "B":
            self.ui.start_move_processor(proc, stay=True)

    def switch_select(self, t="S"):
        """SELECT: short toggles control / select mode, bold the processor's options"""
        if t == "S":
            self.set_mode("select" if self._mode == "control" else "control")
            return True
        if t == "B":
            self.show_menu_processor()
            return True
        return False

    def show_menu_processor(self):
        # Not for the special processors (audio player, tempo, ALSA mixer: Tk's processor
        # options refuse them, build_view with id < -1)
        proc = self.ui.current_processor
        if proc is not None and getattr(proc, "id", 0) < -1:
            return
        self.ui.show_screen("processor_options")

    def show_menu(self):
        """MENU (zynthian_gui_chain_control.show_menu): in select mode the processor's options,
        else select mode"""
        if self._mode == "select" or not self.isChain:
            # (the special processors' screens are Tk's plain control screen: its menu)
            self.show_menu_processor()
        else:
            self.set_mode("select")

    def cuia_v5_zynpot_switch(self, params):
        """V5 knob pushes: in select mode 2 the processor's select, 3 SELECT; in control mode
        short MIDI learn of that controller (a file path: open it), bold / long its options"""
        try:
            i, t = int(params[0]), str(params[1]).upper()
        except (TypeError, ValueError, IndexError):
            return False
        if self._mode == "select":
            if i == 2:
                self._processor_select(t)
                return True
            if i == 3:
                self.switch_select(t)
                return True
            return False
        c = self._knob_controller(i)
        if t == "S":
            if c is not None and c.zctrl is not None and getattr(c.zctrl, "is_path", False):
                c.zctrl.nudge(0)
            else:
                self.toggle_midi_learn(c.index if c is not None else None)
            return True
        if t in ("B", "L"):
            if c is not None:
                c.options()
            return True
        return False

    def cuia_arrow_right(self, params=None):
        self.navigate("right")
        return True

    def cuia_arrow_left(self, params=None):
        self.navigate("left")
        return True

    def move_page(self, step):
        entries = self.pages.entries
        i = self._page + step
        while 0 <= i < len(entries) and entries[i]["separator"]:
            i += step
        if 0 <= i < len(entries):
            self.setPage(i)

    def navigate(self, what):
        """Arrows: up / down the page; left / right the processor in select mode, else the
        chain; SELECT as switch_select"""
        if what == "up":
            self.move_page(-1)
        elif what == "down":
            self.move_page(1)
        elif what in ("left", "right"):
            step = 1 if what == "right" else -1
            if self._mode == "select":
                self._processor_step(step)
            elif self.isChain:
                if step > 0:
                    self.chain_manager.next_chain()
                else:
                    self.chain_manager.previous_chain()
        elif what == "select":
            self.switch_select("S")
        elif what == "select_bold":
            self.switch_select("B")

    def back(self):
        """BACK: leave MIDI learn, then select mode (zynthian_gui_chain_control.back_action)"""
        if self.midi_learning or self.note_learn:
            self.exit_midi_learn()
            return True
        if self._mode == "select":
            self.set_mode("control")
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
