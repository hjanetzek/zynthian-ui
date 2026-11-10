"""The kit's encoders and switches (zyncore), as zynthian_gui's control and zynpot threads read
them (docs/qt-hardware-input.md). No Qt here: ZynUI passes what to call.

- Switches: a thread polls get_zynswitch() every 10 ms and puts ("zynswitch", [i, "P"]) on the
  push and ("zynswitch", [i, "R", dtus]) on the release (zyncore's debounced duration) on the
  CUIA queue, where ZynUI._cuia_task times them as the touch keypad's. zyncore's own long press
  detection is off (long_us 20 s): the CUIA task's autolong does it, once.
- Encoders: zyncore's callback (its ISR thread) adds the delta under a lock and wakes a thread,
  which calls notify_pots() once until ZynUI took the deltas (take_pot_deltas() in the GUI
  thread): a fast turn while the GUI is busy is one summed delta.

Only with a kit's zyncore build: the generic one (DUMMIES: the Duet, desktops) has no
get_zynswitch / setup_zynpot_cb and reports no switches or encoders.
"""

import ctypes
import logging
import os
from threading import Event, Lock, Thread

POLL_SECONDS = 0.01        # as zynthian_gui.control_thread_task
NO_LONG_US = 20 * 1000000  # zyncore's long press detection off (zynthian_gui: while push-rotating)

ZYNPOT_CB = ctypes.CFUNCTYPE(None, ctypes.c_ubyte, ctypes.c_int)

# Encoder behaviour (zyncore's setup_behaviour_zynpot): 1 one step per detent, 0 speed-based
# acceleration
STEP_FIXED = 1
STEP_ACCEL = 0


def list_step(count):
    """A list of count entries (zynthian_gui_controller.config: up to 32 values one per detent)"""
    return STEP_FIXED if count <= 32 else STEP_ACCEL


def zctrl_step(zctrl):
    """The encoder behaviour for a controller, as zynthian_gui_controller.config"""
    if zctrl is None:
        return STEP_FIXED
    if isinstance(zctrl.ticks, list):
        return list_step(len(zctrl.ticks))
    if getattr(zctrl, "is_path", False):
        return STEP_ACCEL
    if zctrl.is_integer and zctrl.value_range <= 32:
        return STEP_FIXED
    return STEP_ACCEL


def available(lib, last_switch_index, num_pots):
    """(switches, encoders) to read from this zyncore build"""
    if lib is None or os.environ.get("ZYNTHIAN_QT_HW_INPUT", "") == "0":
        return False, False
    switches = last_switch_index >= 0 and hasattr(lib, "get_zynswitch")
    pots = num_pots > 0 and hasattr(lib, "setup_zynpot_cb")
    return switches, pots


class HwInput:
    """lib: lib_zyncore; put_event(event): the CUIA queue's put_nowait; has_ui_action(i): custom
    switch i (from 4) has UI actions (MIDI-only switches are zyncore's alone, as zynthian_gui
    skips them); notify_pots(): called from a thread when encoder deltas are pending;
    activity(): user activity (power save)"""

    def __init__(self, lib, last_switch_index, num_pots, put_event, has_ui_action, notify_pots=None,
                 activity=None):
        self.lib = lib
        self.last_switch_index = last_switch_index
        self.num_pots = num_pots
        self.put_event = put_event
        self.has_ui_action = has_ui_action
        self.notify_pots = notify_pots
        self.activity = activity or (lambda: None)
        self.switches, self.pots = available(lib, last_switch_index, num_pots)
        # ZYNTHIAN_QT_HW_INPUT=log: every switch event and encoder delta in the log (checking the
        # buttons' mapping on a kit, docs/qt-hardware-input.md section 5)
        self.log_events = os.environ.get("ZYNTHIAN_QT_HW_INPUT", "") == "log"
        self._exit = Event()
        self._threads = []
        self._pot_lock = Lock()
        self._pot_event = Event()
        self._pot_deltas = [0] * max(num_pots, 0)
        self._pot_pending = False
        self._zynpot_cb = None

    @property
    def enabled(self):
        return self.switches or self.pots

    def start(self):
        if self.switches:
            self._start_thread(self._switch_task, "zynswitch")
        if self.pots:
            self._start_thread(self._pot_task, "zynpot")
            # Kept referenced: ctypes frees the trampoline with the object
            self._zynpot_cb = ZYNPOT_CB(self._on_zynpot)
            self.lib.setup_zynpot_cb(self._zynpot_cb)
        # A warning: the default log level shows it (kits only)
        logging.warning(f"Hardware input: switches {'on' if self.switches else 'off'} (last index "
                     f"{self.last_switch_index}), encoders {'on' if self.pots else 'off'} ({self.num_pots})")

    def _start_thread(self, target, name):
        t = Thread(target=target, name=name, daemon=True)
        t.start()
        self._threads.append(t)

    def stop(self):
        """Before the interpreter goes down: no callbacks into Python from zyncore after this"""
        if self._zynpot_cb is not None:
            try:
                self.lib.setup_zynpot_cb(None)
            except Exception as e:
                logging.warning(f"Hardware input: can't unset the encoder callback: {e}")
        self._exit.set()
        self._pot_event.set()
        for t in self._threads:
            t.join(1)
        self._threads = []

    # Switches

    def poll_switches(self):
        """One poll of the switches (zynthian_gui.zynswitches)"""
        for i in range(self.last_switch_index + 1):
            if i >= 4 and not self.has_ui_action(i):
                continue
            dtus = self.lib.get_zynswitch(i, NO_LONG_US)
            if dtus < 0:
                continue
            self.activity()
            if self.log_events:
                logging.warning(f"Hardware input: switch {i} " + ("pushed" if dtus == 0 else f"released after {dtus // 1000} ms"))
            if dtus == 0:
                self.put_event(("zynswitch", [i, "P"]))
            else:
                self.put_event(("zynswitch", [i, "R", dtus]))

    def _switch_task(self):
        while not self._exit.is_set():
            try:
                self.poll_switches()
            except Exception as e:
                logging.exception(f"Hardware input: polling the switches: {e}")
                self._exit.wait(1)
            self._exit.wait(POLL_SECONDS)

    # Encoders

    def _on_zynpot(self, i, d):
        """zyncore's ISR thread: as little as possible, and never raise"""
        try:
            with self._pot_lock:
                self._pot_deltas[i] += d
            self._pot_event.set()
        except Exception:
            pass

    def _pot_task(self):
        while not self._exit.is_set():
            self._pot_event.wait()
            self._pot_event.clear()
            if self._exit.is_set():
                break
            with self._pot_lock:
                if self._pot_pending or not any(self._pot_deltas):
                    continue
                self._pot_pending = True
            self.activity()
            if self.notify_pots:
                self.notify_pots()

    def take_pot_deltas(self):
        """The deltas since the last call, as [(i, d)], and allow the next notify_pots()"""
        with self._pot_lock:
            deltas = [(i, d) for i, d in enumerate(self._pot_deltas) if d]
            self._pot_deltas = [0] * len(self._pot_deltas)
            self._pot_pending = False
        if self.log_events and deltas:
            logging.warning(f"Hardware input: encoders {deltas}")
        return deltas

    def feed_pot(self, i, d):
        """A delta as zyncore's callback would deliver it (tests)"""
        self._on_zynpot(i, d)
