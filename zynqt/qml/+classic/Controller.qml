// One controller slot (ControllerProxy): name, value, a value arc, its MIDI binding. The content
// is tk's (the name with spaces, Tk's value text, no arc on path controllers, read-only and select
// mode dimmed), the touch shared (ControllerTouch): only the look is classic's.
import QtQuick
import QtQuick.Shapes
import ".."

Panel {
    id: root

    property var ctrl: null
    property bool dimmed: false     // Tk's enable(False): select mode
    readonly property bool active: ctrl !== null && ctrl.active
    readonly property bool greyed: dimmed || (active && ctrl.readonly)

    color: Theme.panel
    cut: Theme.cutLarge

    // MIDI binding (as zynthian_gui_controller.plot_midi_bind): "??#??" while learning, else
    // channel#CC; colours as color_hl (chain) / color_ml (global, learning globally)
    Label {
        id: bindText
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 6
        visible: root.active && text !== ""
        text: root.active ? root.ctrl.bindText : ""
        color: {
            const k = root.active ? root.ctrl.bindKind : ""
            return k === "xy" ? Theme.bindXy
                 : k === "learnGlobal" || k === "abs" ? Theme.bindGlobal
                 : k === "learn" ? Theme.bindChain
                 : k === "chain" && text.indexOf("#") >= 0 ? Theme.bindChain : Theme.textOff
        }
        size: 16
        title: true
        SequentialAnimation on opacity {
            running: root.active && root.ctrl.bindKind.indexOf("learn") === 0
            loops: Animation.Infinite
            onRunningChanged: if (!running) bindText.opacity = 1
            NumberAnimation { to: 0.3; duration: 400 }
            NumberAnimation { to: 1; duration: 400 }
        }
    }

    Label {
        id: nameText
        anchors.left: parent.left
        anchors.right: bindText.visible ? bindText.left : parent.right
        anchors.top: parent.top
        anchors.margins: 6
        elide: Text.ElideRight
        text: root.active ? root.ctrl.name.replace(/_/g, " ") : ""
        opacity: root.greyed ? 0.5 : 1
        color: Theme.text
        size: 18
        title: true
    }

    Item {
        id: dial
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 6
        width: Math.min(parent.height - nameText.height - 16, parent.width * 0.5)
        height: width
        visible: root.active && !root.ctrl.isPath
        opacity: root.greyed ? 0.5 : 1

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

    Label {
        anchors.left: parent.left
        anchors.right: dial.visible ? dial.left : parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 6
        horizontalAlignment: Text.AlignLeft
        elide: Text.ElideRight
        text: root.active ? root.ctrl.tkValueText : ""
        opacity: root.greyed ? 0.5 : 1
        color: Theme.text
        body: true   // values keep their units' case (dB, Hz)
        size: 26
        title: true
    }

    // Touch as every theme's controller (shared)
    ControllerTouch { ctrl: root.ctrl }
}
