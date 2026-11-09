// tk: zynthian_gui_selector's zselector under the info pane, on the screens where Tk shows it
// (zsel_hidden=False: bank, preset, MIDI recorder): a zynthian_gui_controller with selcounter
// (the caption at the top left, the 1-based position among the selectable entries where the arc
// would be, "/count" under it), H/6 high with tiny_ctrls, else 0.19 H (measured).
import QtQuick
import ".."

Item {
    id: root
    property var screen: null
    readonly property bool shown: screen !== null && screen.selectorShown !== undefined && screen.selectorShown
    readonly property real screenHeight: parent ? parent.height : 0

    visible: shown
    implicitHeight: shown ? (screen.selectorTiny ? Math.floor(screenHeight / 6) : Math.floor(0.19 * screenHeight)) : 0

    Rectangle {
        id: slot
        anchors.fill: parent
        anchors.topMargin: 2
        color: Theme.panel

        // on_size_arc with selcounter: the value above the middle
        readonly property int radius_: {
            let r = Math.floor(Math.min(width, height) / 2)
            return r > 4 ? r - 4 : r
        }
        readonly property int arcWidth: Math.floor(radius_ / 4)
        readonly property real x0: width - radius_ - 2
        readonly property real y0: Math.floor(height / 2) - Math.floor(radius_ / 3) - 2
        readonly property int valueWidth: 2 * (radius_ - arcWidth - 1)
        readonly property int fontPx: Theme.tkPx(Theme.tkFontSize)

        Text {
            x: 4
            y: 4
            width: slot.width - 2 * slot.radius_
            text: root.shown ? root.screen.selectorCaption : ""
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: slot.fontPx
            elide: Text.ElideRight
        }
        Text {
            x: slot.x0 - width / 2
            y: slot.y0 - height / 2
            text: root.shown ? root.screen.selectorValue : ""
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: slot.fontPx
        }
        Text {
            x: slot.x0 - width / 2
            y: slot.height - 2 - height
            text: root.shown ? "/" + root.screen.selectorMax : ""
            color: Theme.text
            font.family: Theme.fontFamily
            // Tk's code says value_width // 7 points (5 here), its screen shows ~0.7 F
            font.pixelSize: Theme.tkPx(Math.floor(0.7 * Theme.tkFontSize))
        }
    }
}
