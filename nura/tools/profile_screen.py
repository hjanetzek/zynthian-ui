# Profile switching to one screen (show_screen() and the Tk events after it) with cProfile.
# Run with nura/tools/zyninject.sh profile_screen.py [-s SCREEN='"admin"'] [-s FROM='"mixer"']
#
# Runs in zynthian's main thread. Since Python 3.12 cProfile records all threads: sleep and
# refresh_status entries can come from the background threads.

SCREEN = "main_menu"     # screen to profile switching to
FROM = "mixer"           # screen shown before, and again afterwards
TOP = 30
OUTPUT = "/tmp/zynthian-profile-screen.txt"

import cProfile
import io
import pstats
from zyngui import zynthian_gui_config

_zyngui = zynthian_gui_config.zyngui
_top = zynthian_gui_config.top
_zyngui.show_screen(FROM)
_top.update()
_pr = cProfile.Profile()
_pr.enable()
_zyngui.show_screen(SCREEN)
_top.update()
_pr.disable()
_s = io.StringIO()
_st = pstats.Stats(_pr, stream=_s)
_st.sort_stats("cumulative").print_stats(TOP)
_st.sort_stats("tottime").print_stats(TOP // 2)
_zyngui.show_screen(FROM)
with open(OUTPUT, "w") as _f:
    _f.write(f"Switching from {FROM} to {SCREEN}\n" + _s.getvalue())
