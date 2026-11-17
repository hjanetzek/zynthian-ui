// v4: the mixer (and launcher) of +v4/V4Mixer.qml between the knob hints: level (top left),
// balance (bottom left; the launcher: the phrase), main level (top right), selection (bottom
// right), as zynthian_gui_mixer.zynpot_cb with Tk's V4 layout.
import QtQuick
import ".."

Item {
    id: root

    property bool shown: true
    readonly property bool launcherMode: zyn.currentScreen === "launcher"

    KnobHints {
        id: hints
        anchors.fill: parent
        texts: root.launcherMode ? ["level", "phrase", "main", "chain"] : ["level", "balance", "main", "select"]
    }

    V4Mixer {
        x: hints.edge
        width: parent.width - 2 * hints.edge
        height: parent.height
        shown: root.shown
    }
}
