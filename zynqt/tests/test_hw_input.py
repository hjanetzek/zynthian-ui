"""Unit tests of zynqt.hw_input (no Qt, no zyncore): python3 -m unittest zynqt.tests.test_hw_input"""

import threading
import time
import unittest

from zynqt import hw_input
from zynqt.hw_input import HwInput, NO_LONG_US


class FakeZyncore:
    """get_zynswitch as zyncoder.c: 0 once after a push, the duration once after the release,
    -1 otherwise (the long press detection is off with NO_LONG_US)"""

    def __init__(self):
        self.push = {}
        self.dtus = {}
        self.calls = []
        self.cb = "unset"

    def get_zynswitch(self, i, long_us):
        self.calls.append(i)
        assert long_us == NO_LONG_US
        if self.push.pop(i, False):
            return 0
        if i in self.dtus:
            return self.dtus.pop(i)
        return -1

    def setup_zynpot_cb(self, cb):
        self.cb = cb


class Dummies:
    """The generic build: neither function"""


def make(lib=None, last=7, pots=4, actions=(4, 5, 6, 7), notify=None):
    events = []
    hw = HwInput(lib or FakeZyncore(), last, pots, events.append, lambda i: i in actions, notify)
    return hw, events


class TestAvailable(unittest.TestCase):
    def test_dummies(self):
        self.assertEqual(hw_input.available(Dummies(), -1, 0), (False, False))
        # Even if the counts said otherwise: no functions, nothing to read
        self.assertEqual(hw_input.available(Dummies(), 7, 4), (False, False))
        self.assertEqual(hw_input.available(None, 7, 4), (False, False))

    def test_kit(self):
        self.assertEqual(hw_input.available(FakeZyncore(), 7, 4), (True, True))
        self.assertEqual(hw_input.available(FakeZyncore(), -1, 4), (False, True))

    def test_env_off(self):
        import os
        os.environ["ZYNTHIAN_QT_HW_INPUT"] = "0"
        try:
            self.assertEqual(hw_input.available(FakeZyncore(), 7, 4), (False, False))
        finally:
            del os.environ["ZYNTHIAN_QT_HW_INPUT"]

    def test_dummies_not_started(self):
        hw, events = make(Dummies(), -1, 0)
        self.assertFalse(hw.enabled)


class TestSwitches(unittest.TestCase):
    def test_push_release(self):
        hw, events = make()
        lib = hw.lib
        lib.push[0] = True
        hw.poll_switches()
        self.assertEqual(events, [("zynswitch", [0, "P"])])
        lib.dtus[0] = 450000
        hw.poll_switches()
        self.assertEqual(events[1], ("zynswitch", [0, "R", 450000]))
        hw.poll_switches()
        self.assertEqual(len(events), 2)

    def test_push_and_release_in_one_poll(self):
        hw, events = make()
        hw.lib.push[2] = True
        hw.lib.dtus[2] = 5000
        hw.poll_switches()
        hw.poll_switches()
        self.assertEqual(events, [("zynswitch", [2, "P"]), ("zynswitch", [2, "R", 5000])])

    def test_skips_switches_without_ui_actions(self):
        hw, events = make(actions=(5,))
        hw.poll_switches()
        # 0-3 always, from 4 only those with UI actions (MIDI switches are zyncore's)
        self.assertEqual(hw.lib.calls, [0, 1, 2, 3, 5])

    def test_last_index(self):
        hw, events = make(last=1)
        hw.poll_switches()
        self.assertEqual(hw.lib.calls, [0, 1])


class TestEncoders(unittest.TestCase):
    def test_coalesced(self):
        notified = threading.Event()
        hw, events = make(notify=notified.set)
        hw.switches = False
        hw.start()
        self.assertIsNotNone(hw.lib.cb)
        try:
            hw.feed_pot(3, 1)
            self.assertTrue(notified.wait(1))
            notified.clear()
            # While the GUI hasn't taken them: summed, no further notification
            hw.feed_pot(3, 2)
            hw.feed_pot(0, -1)
            time.sleep(0.05)
            self.assertFalse(notified.is_set())
            self.assertEqual(hw.take_pot_deltas(), [(0, -1), (3, 3)])
            self.assertEqual(hw.take_pot_deltas(), [])
            hw.feed_pot(1, 4)
            self.assertTrue(notified.wait(1))
            self.assertEqual(hw.take_pot_deltas(), [(1, 4)])
        finally:
            hw.stop()
        self.assertIsNone(hw.lib.cb)

    def test_two_isr_threads(self):
        hw, events = make()
        hw.pots = True

        def turn(i):
            for _ in range(1000):
                hw.feed_pot(i, 1)
        threads = [threading.Thread(target=turn, args=(i % 2,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(hw.take_pot_deltas(), [(0, 2000), (1, 2000)])

    def test_callback_never_raises(self):
        hw, events = make(pots=1)
        hw.feed_pot(5, 1)  # out of range: ignored, as the ISR must not see an exception
        self.assertEqual(hw.take_pot_deltas(), [])


class FakeZctrl:
    def __init__(self, ticks=None, is_integer=False, value_range=127, is_path=False):
        self.ticks = ticks
        self.is_integer = is_integer
        self.value_range = value_range
        self.is_path = is_path


class TestSteps(unittest.TestCase):
    """zynthian_gui_controller.config's rule"""

    def test_lists(self):
        self.assertEqual(hw_input.list_step(32), hw_input.STEP_FIXED)
        self.assertEqual(hw_input.list_step(33), hw_input.STEP_ACCEL)
        self.assertEqual(hw_input.zctrl_step(FakeZctrl(ticks=list(range(5)))), hw_input.STEP_FIXED)
        self.assertEqual(hw_input.zctrl_step(FakeZctrl(ticks=list(range(100)))), hw_input.STEP_ACCEL)

    def test_numbers(self):
        self.assertEqual(hw_input.zctrl_step(FakeZctrl(is_integer=True, value_range=16)), hw_input.STEP_FIXED)
        self.assertEqual(hw_input.zctrl_step(FakeZctrl(is_integer=True, value_range=127)), hw_input.STEP_ACCEL)
        self.assertEqual(hw_input.zctrl_step(FakeZctrl(value_range=1)), hw_input.STEP_ACCEL)  # float
        self.assertEqual(hw_input.zctrl_step(FakeZctrl(is_path=True)), hw_input.STEP_ACCEL)
        self.assertEqual(hw_input.zctrl_step(None), hw_input.STEP_FIXED)


if __name__ == "__main__":
    unittest.main()
