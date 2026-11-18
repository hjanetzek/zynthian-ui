// v4: one controller slot as zynthian_gui_controller draws it in Tk's V4 layout (vertical, arc
// graph): the title at the top left over the whole width, the 300 degree arc centred below it
// at the bottom, the value in the arc, the MIDI binding under it. Otherwise as tk's Controller.
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
    // on_size_arc, vertical
    readonly property real x0: Math.floor(width / 2)
    readonly property real y0: height - radius_ + arcWidth - 4
    readonly property int valueWidth: 2 * (radius_ - arcWidth - 1)
    readonly property int titleWidth: width - 4
    readonly property int titleHeight: Math.max(1, y0 - radius_)
    readonly property int fontPx: Theme.tkPx(Theme.tkFontSize)

    // Title (set_title: the font size reduced until the wrapped text fits)
    Text {
        x: 4
        y: 2
        width: root.titleWidth
        height: root.titleHeight
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

    // Touch as every theme's controller (shared)
    ControllerTouch { ctrl: root.ctrl }
}
