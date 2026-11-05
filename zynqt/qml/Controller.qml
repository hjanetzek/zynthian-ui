// One controller slot (ControllerProxy): name, value, a value arc. Drag up/down to change it
// like an encoder (zctrl.nudge, so integer, logarithmic and enumerated values step as with the
// knobs), tap to switch a toggle.
import QtQuick
import QtQuick.Shapes

Rectangle {
    id: root

    property var ctrl: null
    readonly property bool active: ctrl !== null && ctrl.active

    color: Theme.panel

    Text {
        id: nameText
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 6
        elide: Text.ElideRight
        text: root.active ? root.ctrl.name : ""
        color: Theme.text
        font.pixelSize: 18
        font.family: Theme.fontFamily
    }

    Item {
        id: dial
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 6
        width: Math.min(parent.height - nameText.height - 16, parent.width * 0.5)
        height: width
        visible: root.active

        readonly property real f: root.active ? root.ctrl.fraction : 0

        Shape {
            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer
            ShapePath {   // track
                strokeColor: Theme.panelHighlight
                strokeWidth: 6
                fillColor: "transparent"
                capStyle: ShapePath.RoundCap
                PathAngleArc {
                    centerX: dial.width / 2; centerY: dial.height / 2
                    radiusX: dial.width / 2 - 4; radiusY: radiusX
                    startAngle: 135; sweepAngle: 270
                }
            }
            ShapePath {   // value
                strokeColor: root.active && root.ctrl.isToggle && dial.f > 0.5 ? Theme.meterLow : Theme.keyText
                strokeWidth: 6
                fillColor: "transparent"
                capStyle: ShapePath.RoundCap
                PathAngleArc {
                    centerX: dial.width / 2; centerY: dial.height / 2
                    radiusX: dial.width / 2 - 4; radiusY: radiusX
                    startAngle: 135; sweepAngle: Math.max(1, 270 * dial.f)
                }
            }
        }
    }

    Text {
        anchors.left: parent.left
        anchors.right: dial.left
        anchors.bottom: parent.bottom
        anchors.margins: 6
        horizontalAlignment: Text.AlignLeft
        elide: Text.ElideRight
        text: root.active ? root.ctrl.valueText : ""
        color: Theme.text
        font.pixelSize: 26
        font.family: Theme.fontFamily
    }

    DragHandler {
        id: drag
        target: null
        enabled: root.active
        xAxis.enabled: false
        property real lastY: 0
        onActiveChanged: lastY = 0
        onTranslationChanged: {
            // One step per 8 logical pixels
            const steps = Math.trunc((lastY - translation.y) / 8)
            if (steps !== 0) {
                root.ctrl.nudge(steps)
                lastY -= steps * 8
            }
        }
    }
    TapHandler {
        enabled: root.active
        onTapped: if (root.ctrl.isToggle) root.ctrl.toggle()
    }
    WheelHandler {
        enabled: root.active
        onWheel: event => root.ctrl.nudge(event.angleDelta.y > 0 ? 1 : -1)
    }
}
