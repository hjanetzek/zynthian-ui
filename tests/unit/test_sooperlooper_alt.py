"""SooperLooper widget in ALT mode: program changes (zyngui.zynthian_sooperlooper_data.alt_program_change,
shared by the Tk widget and the Qt chain control)."""

from types import SimpleNamespace

import pytest

sld = pytest.importorskip("zyngui.zynthian_sooperlooper_data")


class Ctrl:
    def __init__(self):
        self.calls = []

    def toggle(self):
        self.calls.append("toggle")

    def nudge(self, d):
        self.calls.append(("nudge", d))


def processor():
    return SimpleNamespace(controllers_dict={k: Ctrl() for k in ("replace", "substitute", "insert", "loop_count")})


@pytest.mark.parametrize("program,ctrl,call", [(5, "replace", "toggle"), (6, "substitute", "toggle"),
                                               (7, "insert", "toggle"), (8, "loop_count", ("nudge", 1))])
def test_programs(program, ctrl, call):
    p = processor()
    sld.alt_program_change(p, program)
    assert {k: c.calls for k, c in p.controllers_dict.items() if c.calls} == {ctrl: [call]}


def test_other_programs_do_nothing():
    p = processor()
    for program in (0, 1, 4, 9, 127):
        sld.alt_program_change(p, program)
    assert not any(c.calls for c in p.controllers_dict.values())
