import QtQuick
import ".."

// tk: the Tk V5 keypad's keys (zynthian_gui_touchkeypad_v5.draw_button): rectangles with a 1 px
// outline in the background colour, placed edge to edge, so neighbours share their outline: one
// line at the key's left and top edge, the next key's line closes it (1 px between the keys).
Rectangle {
    property color fill: Theme.keyBackground
    property bool pressed: false
    property bool translucent: false

    color: translucent ? Qt.rgba(0, 0, 0, 0.25) : Theme.background
    Rectangle {
        x: 1; y: 1
        width: parent.width - 1
        height: parent.height - 1
        color: {
            const c = parent.pressed ? Qt.lighter(Theme.keyBackground, 1.8) : Theme.keyBackground
            return parent.translucent ? Qt.rgba(c.r, c.g, c.b, parent.pressed ? 0.85 : 0.55) : c
        }
    }
}
