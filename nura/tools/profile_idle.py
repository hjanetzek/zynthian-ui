# Profile zynthian with cProfile while it runs normally (nothing is changed on screen).
# Run with nura/tools/zyninject.sh profile_idle.py [-s DURATION=20]
#
# Since Python 3.12 cProfile records all threads: time.sleep and queue waits of the
# background threads show up in "tottime", ignore them. Tk calls made from other threads run
# in the main thread; their cost appears as {method 'call' of '_tkinter.tkapp' objects}.

DURATION = 10        # seconds
TOP = 30             # functions per listing
OUTPUT = "/tmp/zynthian-profile-idle.txt"

import cProfile
import io
import pstats
import threading
import time


def _zyn_profile_idle():
    pr = cProfile.Profile()
    pr.enable()
    time.sleep(DURATION)
    pr.disable()
    s = io.StringIO()
    st = pstats.Stats(pr, stream=s)
    st.sort_stats("tottime").print_stats(TOP)
    st.sort_stats("cumulative").print_stats(TOP)
    with open(OUTPUT, "w") as f:
        f.write(s.getvalue())


# Not in the main thread: that would block the UI for the whole duration
threading.Thread(target=_zyn_profile_idle, name="profile_idle", daemon=True).start()
