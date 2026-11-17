// v4: what the kit's four knobs do on this screen, at the screen's edges next to them: a narrow
// column on each side, the upper half for the top knob, the lower half for the bottom one (knob
// 0 top left, 1 bottom left, 2 top right, 3 bottom right). The texts run along the edge (left:
// bottom to top, right: top to bottom). A tap on a hint is a push of its knob's switch, with
// Tk's timing: short (< 0.3 s), bold (to 2 s), long. An empty text leaves its half blank.
import QtQuick
import ".."

Item {
    id: root

    // texts[i]: knob i
    property var texts: ["", "", "", ""]
    // The width of a column: the text height and a margin
    readonly property int edge: Theme.tkPx(Math.floor(0.7 * Theme.tkFontSize)) + 4

    Repeater {
        model: 4
        Rectangle {
            id: hint
            required property int index
            readonly property bool onRight: index >= 2
            x: onRight ? root.width - root.edge : 0
            y: index % 2 === 0 ? 0 : Math.floor(root.height / 2)
            width: root.edge
            height: Math.floor(root.height / 2) - (index % 2 === 0 ? 1 : 0)
            color: Theme.background
            Text {
                anchors.centerIn: parent
                width: hint.height - 4
                rotation: hint.onRight ? 90 : -90
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
                text: root.texts[hint.index] || ""
                color: tap.pressed ? Theme.text : Theme.textOff
                font.family: Theme.fontFamily
                font.pixelSize: Theme.tkPx(Math.floor(0.7 * Theme.tkFontSize))
            }
            TapHandler {
                id: tap
                property real t0: 0
                longPressThreshold: 2.0
                onPressedChanged: if (pressed) t0 = Date.now()
                onTapped: zyn.cuia("_zynswitch", [hint.index, Date.now() - t0 > 300 ? "B" : "S"])
                onLongPressed: zyn.cuia("_zynswitch", [hint.index, "L"])
            }
        }
    }
}
