// tk: the CC view as zynthian_gui_pated_cc draws it: 128 values (plus 8 rows below) over the
// height, a grey line every 8 values with its number in the piano roll column (left of the lane),
// the step lines of the grid, each event a white line from its value to its end value over its
// duration (a square at the start when interpolating), the cursor red at the step and value row.
// Touch as the shared lane: drag paints values, long press removes a step's value.
import QtQuick

Item {
    id: lane
    property var pe: zyn.patternEditor
    property int steps: 1
    property real keyWidth: 72
    readonly property real sw: width / Math.max(1, steps)
    readonly property int rh: Math.max(1, Math.floor(height / 128))
    readonly property int markerWidth: Math.floor((width + keyWidth) / 150)
    readonly property var values: pe.ccValues
    function rowY(v) { return height - (8 + v) * rh }

    // Value lines and numbers
    Repeater {
        model: 17
        Item {
            required property int index
            readonly property int v: index * 8
            y: lane.rowY(v)
            Rectangle { width: lane.width; height: 1; color: "#505050" }
            Text {
                x: -6 - width
                y: -0.5 * lane.rh - height / 2
                text: parent.v
                color: "#ffffff"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.tkPx(lane.rh * 4)
            }
        }
    }
    // Step lines: bars white, beats grey, steps dark
    Repeater {
        model: lane.steps + 1
        Rectangle {
            required property int index
            readonly property int spb: Math.max(1, lane.pe.stepsPerBeat)
            readonly property bool beat: index % spb === 0
            readonly property bool bar: beat && (index / spb) % Math.max(1, lane.pe.beatsPerBar) === 0
            x: index * lane.sw
            width: 1
            height: lane.height
            color: bar ? "#ffffff" : (beat ? "#a0a0a0" : "#505050")
        }
    }
    // Events
    Repeater {
        model: lane.values.length
        Item {
            required property int index
            readonly property var v: lane.values[index]
            visible: v !== null && v !== undefined
            readonly property real x1: index * lane.sw + 1
            readonly property real y1: v ? lane.rowY(v[0] + 1) + 1 : 0
            readonly property real x2: v ? x1 + lane.sw * v[2] - 1 : 0
            readonly property real y2: v ? y1 + (v[0] - v[1]) * lane.rh - 1 : 0
            Rectangle {   // the line from start to end value
                x: parent.x1
                y: parent.y1 - 1
                width: Math.hypot(parent.x2 - parent.x1, parent.y2 - parent.y1)
                height: 2
                color: "#ffffff"
                transformOrigin: Item.Left
                rotation: Math.atan2(parent.y2 - parent.y1, parent.x2 - parent.x1) * 180 / Math.PI
            }
            Rectangle {
                visible: lane.pe.ccInterpolate
                x: parent.x1 - lane.markerWidth
                y: parent.y1 - lane.markerWidth
                width: 2 * lane.markerWidth
                height: width
                color: "#ffffff"
            }
        }
    }
    // Cursor
    Rectangle {
        readonly property real cx: lane.pe.ccCursor * lane.sw + 1
        readonly property real cy: lane.rowY(lane.pe.ccRow + 1) + 1
        // Tk: the square +-(marker width + 1) around the point, its 2 px outline centred on that
        readonly property int m: lane.markerWidth + 2
        x: lane.pe.ccInterpolate ? cx - m : cx
        y: lane.pe.ccInterpolate ? cy - m : cy
        width: lane.pe.ccInterpolate ? 2 * m : lane.sw - 1
        height: lane.pe.ccInterpolate ? 2 * m : lane.rh
        color: Theme.select
        border.color: Theme.select
    }
    MouseArea {
        anchors.fill: parent
        pressAndHoldInterval: 600
        property bool held: false
        function paint(mouse) {
            if (held)
                return
            lane.pe.setCc(Math.floor(mouse.x / lane.sw),
                          Math.round((lane.height - Math.max(0, Math.min(lane.height, mouse.y))) / lane.rh) - 8)
        }
        onPressed: (mouse) => { held = false; paint(mouse) }
        onPositionChanged: (mouse) => paint(mouse)
        onReleased: lane.pe.ccEditDone()
        onPressAndHold: (mouse) => { held = true; lane.pe.removeCc(Math.floor(mouse.x / lane.sw)) }
    }
}
