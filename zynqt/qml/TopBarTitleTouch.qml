// Touch on the top bar's title, for every theme's TopBar (shared), with zynthian's tap timing
// (zynthian_gui_base.cb_topbar_*): a tap goes to the root screen (on the mixer and launcher: BACK,
// i.e. switch between them), bold (> 0.3 s, zynswitch_bold_seconds) or long press (0.8 s) opens
// the main menu.
import QtQuick

Item {
    id: touch

    readonly property bool onMixer: zyn.currentScreen === "mixer" || zyn.currentScreen === "launcher"

    TapHandler {
        property real t0: 0
        longPressThreshold: 0.8
        onPressedChanged: if (pressed) t0 = Date.now()
        onTapped: {
            if (Date.now() - t0 > 300)   // bold (zynswitch_bold_seconds)
                zyn.cuia("main_menu", [])
            else if (touch.onMixer)
                zyn.cuia("back", [])
            else
                zyn.cuia("show_screen", ["root"])
        }
        onLongPressed: zyn.cuia("main_menu", [])
    }
}
