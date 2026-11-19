// Drawbars (DrawbarView; zynthian_widget_drawbar, zynthian_widget_setbfree): nine Hammond
// drawbars, each slides down out of its slot by its setting (0 pushed in ... 8 pulled out): the
// face with the footage at its end, the numbers above it, the setting's number brighter. Drag a
// drawbar up / down to change it (relative to its setting at the press, as Tk).
import QtQuick

Rectangle {
    id: root

    property var view
    readonly property var bars: view ? view.bars : []
    readonly property int border: 2
    readonly property int maxPos: view ? view.positions - 1 : 8
    readonly property real stepHeight: height / (maxPos + 1)
    readonly property int barWidth: Math.floor((width - 2 * border) / Math.max(maxPos + 1, bars.length))
    readonly property real yOffset: -2   // Tk's DRAWBAR_Y_OFFSET
    readonly property int fontSize: Math.max(8, Math.min(Math.floor(stepHeight * 0.7), Math.floor(barWidth * 0.45)))
    color: Theme.widgetBackground
    clip: true

    Repeater {
        model: root.bars.length
        Item {
            id: bar
            required property int index
            readonly property var d: root.bars[index]
            readonly property color face: d.colour === "brown" ? Theme.drawbarBrown
                                          : (d.colour === "white" ? Theme.drawbarWhite : Theme.drawbarBlack)
            readonly property int number: Math.round(d.position)
            x: root.border + index * root.barWidth
            width: root.barWidth
            height: root.height

            Rectangle {   // the slot (drag area)
                y: -1
                width: parent.width
                height: parent.height + 2
                color: Theme.widgetBackground
                border.color: Theme.drawbarTrack
                border.width: 1
            }
            // The drawbar: moved up by its distance from fully pulled out
            Item {
                width: parent.width
                height: parent.height
                y: (bar.d.position - root.maxPos) * root.stepHeight + root.yOffset
                Rectangle {   // the shaft
                    x: 2
                    width: parent.width - 4
                    height: parent.height
                    color: Theme.widgetBackground
                    border.color: Theme.drawbarOutline
                    border.width: 1
                }
                Repeater {   // the numbers on the shaft, 8 at the top
                    model: root.maxPos
                    Text {
                        required property int index
                        x: 1
                        width: bar.width
                        y: (index + 0.5) * root.stepHeight - height / 2
                        horizontalAlignment: Text.AlignHCenter
                        text: root.maxPos - index
                        color: root.maxPos - index === bar.number ? Theme.drawbarNumberOn : Theme.drawbarNumber
                        font.pixelSize: root.fontSize
                    }
                }
                Rectangle {   // the face, at the end
                    x: 1
                    y: root.maxPos * root.stepHeight
                    width: parent.width - 2
                    height: parent.height - y
                    color: bar.face
                    border.color: Theme.drawbarOutline
                    border.width: 1
                    Text {
                        x: 1
                        width: parent.width
                        y: root.stepHeight / 2 - height / 2
                        horizontalAlignment: Text.AlignHCenter
                        text: bar.d.footage
                        color: bar.d.colour === "white" ? Theme.drawbarBlack : Theme.drawbarWhite
                        font.pixelSize: root.fontSize
                    }
                }
            }
            MouseArea {
                anchors.fill: parent
                preventStealing: true
                property real pressY
                function clampY(y) { return Math.max(0, Math.min(root.height, y)) }
                onPressed: (mouse) => { pressY = clampY(mouse.y); root.view.press(bar.index) }
                onPositionChanged: (mouse) => root.view.drag((clampY(mouse.y) - pressY) / root.height)
                onReleased: root.view.release()
                onCanceled: root.view.release()
            }
        }
    }
}
