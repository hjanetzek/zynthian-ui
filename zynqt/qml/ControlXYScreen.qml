// X-Y touchpad (ControlXY, zynthian_gui_control_xy): drag anywhere to set both controllers; the
// cursor follows them when they change elsewhere. Up is a higher Y value. BACK or three taps
// return (as the Tk screen).
import QtQuick

Item {
    id: root

    readonly property var xy: zyn.controlXY

    Panel {
        id: pad
        anchors.fill: parent
        anchors.margins: 12
        color: Theme.panelHighlight
        borderColor: Theme.xyFrame
        borderWidth: 2
        radius: 6
        cut: Theme.cutLarge

        // Grid lines at quarters
        Repeater {
            model: 3
            Rectangle {
                required property int index
                x: (index + 1) * pad.width / 4; width: 1; height: pad.height; color: Theme.panel
            }
        }
        Repeater {
            model: 3
            Rectangle {
                required property int index
                y: (index + 1) * pad.height / 4; height: 1; width: pad.width; color: Theme.panel
            }
        }

        // Cursor
        readonly property real cx: root.xy ? root.xy.fx * width : 0
        readonly property real cy: root.xy ? (1 - root.xy.fy) * height : 0
        Rectangle { x: pad.cx; width: 2; height: pad.height; color: Theme.keyText }
        Rectangle { y: pad.cy; height: 2; width: pad.width; color: Theme.keyText }
        Rectangle {
            x: pad.cx - width / 2; y: pad.cy - height / 2
            width: 36; height: 36; radius: 18
            color: "transparent"; border.color: Theme.keyText; border.width: 3
        }

        Column {
            x: 16; y: 12
            spacing: 6
            Label { text: root.xy ? root.xy.xText : ""; color: Theme.text; size: 22; title: true; body: true }
            Label { text: root.xy ? root.xy.yText : ""; color: Theme.text; size: 22; title: true; body: true }
        }
        Label {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 8
            text: "X: left → right    Y: down → up    Tap 3 times to exit"
            color: Theme.disabled
            body: true
            size: 16
        }

        function moveTo(p) {
            root.xy.setPosition(Math.max(0, Math.min(1, p.x / width)), Math.max(0, Math.min(1, 1 - p.y / height)))
        }
        // The press moves the cursor (TapHandler); dragging past the threshold keeps moving it
        // (a threshold of 0 would turn finger jitter into drags and lose the exit taps)
        DragHandler {
            target: null
            onCentroidChanged: if (active) pad.moveTo(centroid.position)
        }
        TapHandler {
            onPressedChanged: if (pressed) pad.moveTo(point.position)
            onTapped: if (tapCount >= 3) zyn.back()
        }
    }
}
