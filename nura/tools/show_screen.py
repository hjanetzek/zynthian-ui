# Switch zynthian to a screen, e.g. before a screenshot.
# Run with nura/tools/zyninject.sh show_screen.py -s 'SCREEN="admin"'
#
# Screen names: mixer, main_menu, admin, chain_manager, snapshot, zs3, ... (zyngui.screens)

SCREEN = "mixer"
OUTPUT = "/tmp/zynthian-show-screen.txt"

from zyngui import zynthian_gui_config

_zyngui = zynthian_gui_config.zyngui
_zyngui.show_screen(SCREEN)
with open(OUTPUT, "w") as _f:
    _f.write(f"current screen: {_zyngui.current_screen}\n")
