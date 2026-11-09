// tk: one controller slot as zynthian_gui_controller draws it (horizontal layout, arc graph):
// the title at the top left, a 300 degree arc at the right in color_ctrl_bg_on (color_off when
// disabled in select mode or read-only), the value in the arc, the MIDI binding under it. Touch
// as the default Controller.
import QtQuick
import QtQuick.Shapes
import ".."

Rectangle {
    id: root

    property var ctrl: null
    property bool dimmed: false     // Tk's enable(False): select mode
    readonly property bool active: ctrl !== null && ctrl.active

    color: Theme.panel

    // on_size_arc
    readonly property int radius_: {
        let r = Math.floor(Math.min(width, height) / 2)
        return r > 4 ? r - 4 : r
    }
    readonly property int arcWidth: Math.floor(radius_ / 4)
    readonly property real x0: width - radius_ - 2
    readonly property real y0: Math.floor(height / 2)
    readonly property int valueWidth: 2 * (radius_ - arcWidth - 1)
    readonly property int titleWidth: Math.floor(width - radius_ * 2)
    readonly property int fontPx: Theme.tkPx(Theme.tkFontSize)

    // Title (set_title: the font size reduced until the wrapped text fits)
    Text {
        x: 4
        y: 4
        width: root.titleWidth
        height: root.titleWidth
        visible: root.active
        // Tk wraps at spaces only (a word too wide gets a smaller font): no break after "/"
        text: root.active ? root.ctrl.name.replace(/_/g, " ").replace(/\//g, "/\u2060") : ""
        color: Theme.text
        font.family: Theme.fontFamily
        font.pixelSize: root.fontPx
        minimumPixelSize: Theme.tkPx(8)
        fontSizeMode: Text.Fit
        wrapMode: Text.WordWrap
        verticalAlignment: Text.AlignTop
    }

    Shape {
        anchors.fill: parent
        visible: root.active && !root.ctrl.isPath
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: !root.dimmed && !(root.active && root.ctrl.readonly) ? Theme.select : Theme.tkColor("off", "#5a626d")
            strokeWidth: root.arcWidth
            fillColor: "transparent"
            capStyle: ShapePath.FlatCap
            PathAngleArc {
                centerX: root.x0
                centerY: root.y0
                radiusX: root.radius_ - root.arcWidth
                radiusY: radiusX
                startAngle: root.active ? root.ctrl.tkArcStart : 0
                sweepAngle: root.active ? root.ctrl.tkArcSweep : 0
            }
        }
    }

    // calculate_value_font_size: the sample text (tk_plot) fitted into the arc, at most 1.15 F
    TextMetrics {
        id: sampleMetrics
        font.family: Theme.fontFamily
        font.pixelSize: 100
        text: root.active && root.ctrl.tkValueSample !== "" ? root.ctrl.tkValueSample : "0"
    }
    Text {
        x: root.x0 - width / 2
        y: root.y0 - height / 2
        width: root.valueWidth
        visible: root.active
        text: root.active ? root.ctrl.tkValueText : ""
        color: Theme.text
        font.family: Theme.fontFamily
        font.pixelSize: Math.max(Theme.tkPx(8), Math.min(Theme.tkPx(Math.floor(1.15 * Theme.tkFontSize)),
                                 Math.floor(100 * root.valueWidth / Math.max(1, sampleMetrics.advanceWidth))))
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
    }

    // MIDI binding: centred under the arc, at the bottom
    Text {
        x: root.x0 - width / 2
        y: root.height - 2 - height
        visible: root.active && text !== ""
        text: root.active ? root.ctrl.bindText : ""
        font.family: Theme.fontFamily
        font.pixelSize: Theme.tkPx(Math.max(Math.floor(root.valueWidth / 7), 8))
        color: {
            const k = root.active ? root.ctrl.bindKind : ""
            return k === "xy" ? Theme.bindXy
                 : k === "learnGlobal" || k === "abs" ? Theme.bindGlobal
                 : k === "learn" ? Theme.bindChain
                 : k === "chain" && text.indexOf("#") >= 0 ? Theme.bindChain : Theme.text
        }
    }

    DragHandler {
        target: null
        enabled: root.active
        xAxis.enabled: false
        property real lastY: 0
        onActiveChanged: { lastY = 0; if (active) root.ctrl.touched() }
        onTranslationChanged: {
            const steps = Math.trunc((lastY - translation.y) / 8)
            if (steps !== 0) {
                root.ctrl.nudge(steps)
                lastY -= steps * 8
            }
        }
    }
    TapHandler {
        enabled: root.active
        onTapped: {
            if (root.ctrl.bindKind.indexOf("learn") === 0 || zyn.chainControl.learnText !== "")
                root.ctrl.touched()
            else if (root.ctrl.isToggle)
                root.ctrl.toggle()
        }
        onLongPressed: root.ctrl.options()
    }
    WheelHandler {
        enabled: root.active
        onWheel: event => root.ctrl.nudge(event.angleDelta.y > 0 ? 1 : -1)
    }
}
