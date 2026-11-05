"""MIDI CC routing and note range/transpose of the active chain (zynthian_gui_midi_cc,
zynthian_gui_midi_key_range). The note range is shown as four controllers in the chain control
screen (a pseudo-processor, like tempo); the Tk screen's piano drawing is not ported."""

import ctypes
import logging

from zyncoder.zyncore import lib_zyncore
from zyngine.zynthian_controller import zynthian_controller
from zynqt.screens.base import SelectorScreen, entry

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def note_name(num):
    return f"{NOTE_NAMES[num % 12]}{num // 12 - 1}"


class MidiCC(SelectorScreen):
    """CC numbers passed through to the chain's processors"""

    name = "midi_cc"

    def fill(self):
        chain = self.chain_manager.get_active_chain()
        self.set_title(f"{chain.get_name()}/MIDI CC")
        self.zmop_index = chain.zmop_index if chain.zmop_index is not None and chain.zmop_index >= 0 else None
        if self.zmop_index is None:
            self.set_entries([entry("This chain has no MIDI.", enabled=False)])
            return
        self.cc_route = (ctypes.c_uint8 * 128)()
        lib_zyncore.zmop_get_cc_route(self.zmop_index, self.cc_route)
        info = ("Select MIDI CC numbers passed-thru to chain processors. "
                "It could interfere with MIDI-learning. Use with caution!")
        self.set_entries([entry(f"{'☒' if on else '☐'} CC {ccnum:02d}", data=ccnum, info=info)
                          for ccnum, on in enumerate(self.cc_route)])

    def select_action(self, index, t):
        if t != "S" or self.zmop_index is None:
            return
        ccnum = self.entries[index]["data"]
        self.cc_route[ccnum] = 0 if self.cc_route[ccnum] else 1
        lib_zyncore.zmop_set_cc_route(self.zmop_index, self.cc_route)
        self.fill()


class KeyRangeProcessor:
    """Pseudo-processor for the chain control screen: note range and transpose of a chain's MIDI
    output (zmop), as zynthian_gui_midi_key_range"""

    type = "MIDI"
    id = -10

    class _Engine:
        name = "Note Range & Transpose"

    def __init__(self, chain):
        self.chain = chain
        self.zmop_index = chain.zmop_index
        self.engine = self._Engine()
        z = self.zmop_index
        self.octave = zynthian_controller(self, "octave transpose", {
            "name": "Octave transpose", "short_name": "Octave", "value_min": -5, "value_max": 6,
            "labels": [f"+{n}" if n > 0 else str(n) for n in range(-5, 7)]})
        self.semitone = zynthian_controller(self, "semitone transpose", {
            "name": "Semitone transpose", "short_name": "Semitone", "value_min": -12, "value_max": 12,
            "labels": [f"+{n}" if n > 0 else str(n) for n in range(-12, 13)]})
        notes = [note_name(n) for n in range(128)]
        self.low = zynthian_controller(self, "note low", {"name": "Lowest note", "short_name": "Low note",
                                                          "value_min": 0, "value_max": 127, "labels": notes})
        self.high = zynthian_controller(self, "note high", {"name": "Highest note", "short_name": "High note",
                                                            "value_min": 0, "value_max": 127, "labels": notes})
        # Current values, without sending them back
        self._loading = True
        self.octave.set_value(lib_zyncore.zmop_get_transpose_octave(z), False)
        self.semitone.set_value(lib_zyncore.zmop_get_transpose_semitone(z), False)
        self.low.set_value(lib_zyncore.zmop_get_note_low(z), False)
        self.high.set_value(lib_zyncore.zmop_get_note_high(z), False)
        self._loading = False

    # What the chain control screen asks of a processor

    def get_name(self):
        return "Note Range"

    def get_ctrl_screens(self):
        return {"Note range & transpose": [self.octave, self.semitone, self.low, self.high]}

    def get_ctrl_screen(self, title):
        return self.get_ctrl_screens()[title]

    def get_current_screen_index(self):
        return 0

    def set_current_screen_index(self, index):
        pass

    # zynthian_controller calls this when a value changes (as zynthian_gui_midi_key_range)

    def send_controller_value(self, zctrl):
        if self._loading:
            return
        z = self.zmop_index
        lib_zyncore.ui_send_all_notes_off_chain(z)   # no stuck notes
        if zctrl is self.low:
            if zctrl.value > self.high.value:
                zctrl.set_value(self.high.value - 1)
                return
            lib_zyncore.zmop_set_note_low(z, zctrl.value)
        elif zctrl is self.high:
            if zctrl.value < self.low.value:
                zctrl.set_value(self.low.value + 1)
                return
            lib_zyncore.zmop_set_note_high(z, zctrl.value)
        elif zctrl is self.octave:
            lib_zyncore.zmop_set_transpose_octave(z, zctrl.value)
        elif zctrl is self.semitone:
            lib_zyncore.zmop_set_transpose_semitone(z, zctrl.value)
        logging.debug(f"MIDI key range {zctrl.symbol} => {zctrl.value}")
