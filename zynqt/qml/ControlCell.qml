// tk: a cell of chain control's grid (ControlGrid, docs/qt-control-grid.md) in the style of Tk's
// controller: square, on color_panel_bg, the name at the top left (two lines at most, elided), the
// value text at the bottom left (shrunk to fit, then elided), the MIDI binding at the top right; a
// 300 degree arc at the right for continuous values (from the zero of ranges across it) in the
// page's section colour; a toggle a square lit when on, a list its position as an arc segment, a
// trigger a button frame. A slot of a page without a controller is a recessed plate; a cell
// without a page is not drawn. Read-only controllers and select mode are dimmed. Themes replace
// this file for another look (+<theme>/ControlCell.qml, same properties); the touch is shared
// (ControlCellTouch, in ControlGrid).
import QtQuick
import QtQuick.Shapes

Rectangle {
    id: root

    property var ctrl: null           // GridCellProxy
    property bool dimmed: false       // select mode
    property color accent: Theme.select   // the page's section colour

    readonly property bool active: ctrl !== null && ctrl.active
    readonly property string kind: active ? ctrl.kind : "empty"
    readonly property bool greyed: dimmed || (active && !ctrl.enabled)
    readonly property bool continuous: kind === "float" || kind === "integer"
    readonly property int pad: Math.max(2, Math.round(Math.min(width, height) * 0.05))
    readonly property int nameSize: Math.max(Theme.tkPx(7), Math.min(Theme.tkPx(Theme.tkFontSize), Math.round(height * 0.15)))
    readonly property int valueSize: Math.max(Theme.tkPx(7), Math.min(Theme.tkPx(Math.floor(1.15 * Theme.tkFontSize)), Math.round(height * 0.2)))
    // The arc at the right (continuous values, lists), as big as fits beside the texts
    readonly property bool arcShown: continuous || kind === "list"
    readonly property int arcSize: arcShown ? Math.min(height - 2 * pad, Math.round(width * 0.32)) : 0

    visible: ctrl !== null && ctrl.valid
    color: active ? Theme.panel : Theme.panelHighlight

    Item {
        anchors.fill: parent
        visible: root.active
        opacity: root.greyed ? 0.45 : 1

        // the MIDI binding under the arc (as Tk's controller), or at the bottom right
        Text {
            id: bind
            x: root.arcShown ? arc.x + (arc.width - width) / 2
             : (toggle.visible ? toggle.x - root.pad : root.width - root.pad) - width
            anchors.bottom: parent.bottom
            anchors.bottomMargin: root.pad
            z: 1
            visible: text !== ""
            text: root.active ? root.ctrl.bindText : ""
            font.family: Theme.fontFamily
            font.pixelSize: Math.max(Theme.tkPx(6), Math.round(root.nameSize * 0.75))
            color: {
                const k = root.active ? root.ctrl.bindKind : ""
                return k === "xy" ? Theme.bindXy
                     : k === "learnGlobal" || k === "abs" ? Theme.bindGlobal
                     : k === "learn" ? Theme.bindChain
                     : k === "chain" && text.indexOf("#") >= 0 ? Theme.bindChain : Theme.textOff
            }
        }

        Text {
            x: root.pad
            y: root.pad
            width: root.width - 2 * root.pad - (root.arcShown ? root.arcSize : 0)
            text: root.active ? root.ctrl.gridName : ""
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: root.nameSize
            wrapMode: Text.Wrap
            maximumLineCount: 2
            elide: Text.ElideRight
        }

        Text {
            id: value
            x: root.pad
            anchors.bottom: parent.bottom
            anchors.bottomMargin: root.pad
            width: root.width - 2 * root.pad - (root.arcShown ? root.arcSize + root.pad : 0)
                   - (toggle.visible ? toggle.width + root.pad : 0)
                   - (bind.visible && !root.arcShown ? bind.width + root.pad : 0)
            height: root.valueSize * 1.3
            verticalAlignment: Text.AlignBottom
            text: root.active ? root.ctrl.valueText : ""
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: root.valueSize
            minimumPixelSize: Theme.tkPx(7)
            fontSizeMode: Text.HorizontalFit
            elide: Text.ElideRight
        }

        // Continuous values and lists: Tk's arc (lists: a segment at the label's place)
        Shape {
            id: arc
            visible: root.arcShown
            x: root.width - root.pad - root.arcSize
            y: Math.round((root.height - root.arcSize) / 2)
            width: root.arcSize
            height: root.arcSize
            preferredRendererType: Shape.CurveRenderer
            readonly property real lw: Math.max(2, Math.round(root.arcSize / 8))
            readonly property real r: root.arcSize / 2 - lw / 2
            readonly property real f: root.active ? root.ctrl.fraction : 0
            readonly property real o: root.active ? root.ctrl.origin : 0
            readonly property int n: root.active ? root.ctrl.listCount : 0
            readonly property int i: root.active ? root.ctrl.listIndex : -1
            ShapePath {
                strokeColor: Theme.panelHighlight
                strokeWidth: arc.lw
                fillColor: "transparent"
                capStyle: ShapePath.FlatCap
                PathAngleArc {
                    centerX: root.arcSize / 2; centerY: root.arcSize / 2
                    radiusX: arc.r; radiusY: arc.r
                    startAngle: 120; sweepAngle: 300
                }
            }
            ShapePath {
                strokeColor: root.accent
                strokeWidth: arc.lw
                fillColor: "transparent"
                capStyle: ShapePath.FlatCap
                PathAngleArc {
                    centerX: root.arcSize / 2; centerY: root.arcSize / 2
                    radiusX: arc.r; radiusY: arc.r
                    startAngle: root.kind === "list" && arc.n > 0 ? 120 + 300 * Math.max(0, arc.i) / arc.n
                              : 120 + 300 * Math.min(arc.o, arc.f)
                    sweepAngle: root.kind === "list" && arc.n > 0 ? Math.max(4, 300 / arc.n)
                              : Math.max(1, 300 * Math.abs(arc.f - arc.o))
                }
            }
        }

        // Toggle: a square, lit when on; trigger: a button frame
        Rectangle {
            id: toggle
            visible: root.kind === "toggle" || root.kind === "trigger"
            readonly property int side: Math.round(Math.min(root.height * 0.4, root.width * 0.3))
            width: side
            height: side
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: root.pad
            color: root.kind === "toggle" && root.active && root.ctrl.listIndex > 0 ? root.accent : "transparent"
            border.color: root.accent
            border.width: Math.max(2, Math.round(side / 10))
        }
    }
}
