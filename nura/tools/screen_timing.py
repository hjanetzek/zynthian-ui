# Time switching between screens, including Tk's drawing.
# Run with nura/tools/zyninject.sh screen_timing.py [-s SCREENS='["mixer", "admin"]'] [-s ROUNDS=3]
#
# Runs in zynthian's main thread. Per switch:
#   show    zynthian's show_screen() (building the screen, Python)
#   draw    Tk's pending redraws (update_idletasks)
#   events  the remaining Tk events and callbacks (update)
# The first round includes one-time work (images loaded on first use).

SCREENS = ["main_menu", "admin", "mixer"]
ROUNDS = 2
OUTPUT = "/tmp/zynthian-screen-timing.txt"

import time
from zyngui import zynthian_gui_config

_zyngui = zynthian_gui_config.zyngui
_top = zynthian_gui_config.top
_res = []
_top.update()
for _round in range(ROUNDS):
    for _name in SCREENS:
        _t0 = time.perf_counter()
        _zyngui.show_screen(_name)
        _t1 = time.perf_counter()
        _top.update_idletasks()
        _t2 = time.perf_counter()
        _top.update()
        _t3 = time.perf_counter()
        _res.append(f"{_round + 1}  {_name:12s} show {1000 * (_t1 - _t0):6.1f} ms  draw {1000 * (_t2 - _t1):6.1f} ms"
                    f"  events {1000 * (_t3 - _t2):6.1f} ms  total {1000 * (_t3 - _t0):6.1f} ms")
_res.append(f"screen {_top.winfo_width()}x{_top.winfo_height()}, font size {zynthian_gui_config.font_size}")
with open(OUTPUT, "w") as _f:
    _f.write("\n".join(_res) + "\n")
