// classic (and galactica, enterprise: their plates, colours and the controlGrid* tokens): a cell of
// chain control's grid (ControlGrid, docs/qt-control-grid.md) as a plate: the name at the top (two
// lines at most, elided), the MIDI binding at the top right, the value text above a bar along the
// bottom in the page's section colour: continuous values from the zero of ranges across it (in
// segments with controlCellSegments), a list one segment per label (the value's lit; long lists a
// marker), a toggle a lamp lit when on, a trigger an outlined button. A slot of a page without a
// controller is a recessed plate; a cell without a page is not drawn. Read-only controllers and
// select mode are dimmed. Same properties as the tk cell; the touch is shared (ControlCellTouch).
import QtQuick
import ".."

Panel {
    id: root

    property var ctrl: null           // GridCellProxy
    property bool dimmed: false       // select mode
    property color accent: Theme.select   // the page's section colour

    readonly property bool active: ctrl !== null && ctrl.active
    readonly property string kind: active ? ctrl.kind : "empty"
    readonly property bool greyed: dimmed || (active && !ctrl.enabled)
    readonly property bool continuous: kind === "float" || kind === "integer"
    readonly property int pad: Math.max(3, Math.round(Math.min(width, height) * 0.07) + Math.round(root._c / 3))
    readonly property real nameSize: Math.max(9, Math.min(18, height * 0.15)) / Theme.fontScale
    readonly property real valueSize: Math.max(10, Math.min(24, height * 0.2)) / Theme.fontScale
    readonly property int barHeight: Math.max(4, Math.round(height * 0.09))

    visible: ctrl !== null && ctrl.valid
    color: active ? Theme.panel : Theme.panelHighlight
    borderColor: active ? Theme.frame : "transparent"
    cut: Theme.cut

    Item {
        anchors.fill: parent
        visible: root.active
        opacity: root.greyed ? 0.45 : 1

        // the MIDI binding at the right of the value (left of a lamp)
        Label {
            id: bind
            anchors.right: lamp.visible ? lamp.left : parent.right
            anchors.rightMargin: lamp.visible ? 4 : root.pad
            anchors.bottom: bar.top
            anchors.bottomMargin: Math.max(2, Math.round(root.pad / 2))
            visible: text !== ""
            text: root.active ? root.ctrl.bindText : ""
            size: root.nameSize * 0.8
            title: true
            color: {
                const k = root.active ? root.ctrl.bindKind : ""
                return k === "xy" ? Theme.bindXy
                     : k === "learnGlobal" || k === "abs" ? Theme.bindGlobal
                     : k === "learn" ? Theme.bindChain
                     : k === "chain" && text.indexOf("#") >= 0 ? Theme.bindChain : Theme.textOff
            }
            SequentialAnimation on opacity {
                running: root.active && root.ctrl.bindKind.indexOf("learn") === 0
                loops: Animation.Infinite
                onRunningChanged: if (!running) bind.opacity = 1
                NumberAnimation { to: 0.3; duration: 400 }
                NumberAnimation { to: 1; duration: 400 }
            }
        }

        Label {
            x: root.pad
            y: root.pad
            width: root.width - 2 * root.pad
            text: root.active ? root.ctrl.gridName : ""
            color: Theme.text
            size: root.nameSize
            title: true
            wrapMode: Text.Wrap
            maximumLineCount: 2
            elide: Text.ElideRight
            lineHeight: 0.9
        }

        Label {
            x: root.pad
            anchors.bottom: bar.top
            anchors.bottomMargin: Math.max(2, Math.round(root.pad / 2))
            width: root.width - 2 * root.pad - (lamp.visible ? lamp.width + 4 : 0) - (bind.visible ? bind.width + 4 : 0)
            height: Math.round(root.valueSize * Theme.fontScale * 1.25)
            verticalAlignment: Text.AlignBottom
            text: root.active ? root.ctrl.valueText : ""
            color: Theme.text
            size: root.valueSize
            body: true      // values keep their units' case (dB, Hz)
            title: true
            minimumPixelSize: 8
            fontSizeMode: Text.HorizontalFit
            elide: Text.ElideRight
        }

        // Toggle: a lamp, lit when on; trigger: an outlined button
        Rectangle {
            id: lamp
            visible: root.kind === "toggle" || root.kind === "trigger"
            readonly property int side: Math.round(Math.min(root.height * 0.3, root.width * 0.28))
            anchors.right: parent.right
            anchors.bottom: bar.top
            anchors.margins: root.pad
            anchors.bottomMargin: Math.max(2, Math.round(root.pad / 2))
            width: root.kind === "trigger" ? side * 1.4 : side
            height: side
            radius: Theme.panelRadius > 0 || Theme.pillButtons ? height / 2 : (root.cut > 0 ? 0 : 3)
            color: root.kind === "toggle" && root.active && root.ctrl.listIndex > 0 ? root.accent : "transparent"
            border.color: root.accent
            border.width: 2
        }

        // The bar: track, then the value (continuous: from the origin; lists: the label's segment)
        Item {
            id: bar
            x: root.pad
            anchors.bottom: parent.bottom
            anchors.bottomMargin: root.pad
            width: root.width - 2 * root.pad
            height: root.barHeight
            visible: root.continuous || root.kind === "list" || root.kind === "toggle"
            readonly property real f: root.active ? root.ctrl.fraction : 0
            readonly property real o: root.active ? root.ctrl.origin : 0
            readonly property int n: root.active ? root.ctrl.listCount : 0
            readonly property int i: root.active ? root.ctrl.listIndex : -1
            // segments: lists (up to 16 labels), else the theme's (0: one bar)
            readonly property int segments: root.kind === "list" || root.kind === "toggle"
                                            ? (n <= 16 ? n : 0) : Theme.controlCellSegments
            readonly property real r: Theme.panelRadius > 0 || Theme.pillButtons ? height / 2 : 0

            Rectangle {
                visible: bar.segments === 0
                anchors.fill: parent
                radius: bar.r
                color: Theme.panelHighlight
            }
            Rectangle {
                // continuous: from the origin to the value; a long list: a marker at its place
                visible: bar.segments === 0
                readonly property real a: root.kind === "list" ? Math.max(0, bar.i) / Math.max(1, bar.n) : Math.min(bar.o, bar.f)
                readonly property real b: root.kind === "list" ? (Math.max(0, bar.i) + 1) / Math.max(1, bar.n) : Math.max(bar.o, bar.f)
                x: a * bar.width
                width: Math.max(2, (b - a) * bar.width)
                height: parent.height
                radius: bar.r
                color: root.accent
            }
            Repeater {
                model: bar.segments
                Rectangle {
                    required property int index
                    readonly property real w: (bar.width + 2) / bar.segments
                    readonly property bool lit: root.kind === "list" || root.kind === "toggle"
                        ? index === bar.i
                        : (index + 0.5) / bar.segments >= Math.min(bar.o, bar.f) && (index + 0.5) / bar.segments <= Math.max(bar.o, bar.f)
                    x: index * w
                    width: Math.max(1, w - 2)
                    height: bar.height
                    radius: bar.r
                    color: lit ? root.accent : Theme.panelHighlight
                }
            }
        }
    }
}
