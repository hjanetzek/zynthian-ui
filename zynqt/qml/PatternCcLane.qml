import QtQuick

// CC view: the steps fit the width; a bar per step with a value (0..127, end value for
// interpolated ramps); drag paints values, long press removes a step's value
Item {
    id: ccLane
    property var pe: zyn.patternEditor
    property int steps: 1
    property real keyWidth: 72
    readonly property real sw: width / ccLane.steps
    readonly property var values: ccLane.pe.ccValues

    Rectangle { anchors.fill: parent; color: Theme.gridRowDark }
    // Value lines every 16
    Repeater {
        model: 9
        Rectangle {
            required property int index
            y: ccLane.height - index * 16 / 127 * ccLane.height
            width: ccLane.width
            height: 1
            color: index % 4 === 0 ? Theme.gridBeat : Theme.gridRow
            Label {
                x: -ccLane.keyWidth
                y: -8
                width: ccLane.keyWidth - 6
                horizontalAlignment: Text.AlignRight
                text: Math.min(127, parent.index * 16)
                color: Theme.textOff
                size: 12
            }
        }
    }
    // Beat lines
    Repeater {
        model: ccLane.steps
        Rectangle {
            required property int index
            x: index * ccLane.sw
            width: 1
            height: ccLane.height
            visible: index % ccLane.pe.stepsPerBeat === 0
            color: Theme.gridBeat
        }
    }
    // Values
    Repeater {
        model: ccLane.values.length
        Item {
            required property int index
            readonly property var v: ccLane.values[index]
            x: index * ccLane.sw
            width: ccLane.sw
            height: ccLane.height
            visible: v !== null && v !== undefined
            Rectangle {
                anchors.bottom: parent.bottom
                x: 2
                width: parent.width - 4
                height: parent.v ? parent.v[0] / 127 * ccLane.height : 0
                color: index === ccLane.pe.ccCursor ? Theme.ccBarCurrent : Theme.ccBar
                border.color: Theme.noteFrame
                border.width: 1
            }
        }
    }
    // Playhead and cursor
    Rectangle {
        x: ccLane.pe.ccCursor * ccLane.sw
        width: ccLane.sw
        height: ccLane.height
        color: "transparent"
        border.color: Theme.select
        border.width: 2
    }
    MouseArea {
        anchors.fill: parent
        pressAndHoldInterval: 600
        property bool held: false
        function paint(mouse) {
            if (held)
                return
            ccLane.pe.setCc(Math.floor(mouse.x / ccLane.sw),
                          Math.round(127 * (1 - Math.max(0, Math.min(ccLane.height, mouse.y)) / ccLane.height)))
        }
        onPressed: (mouse) => { held = false; paint(mouse) }
        onPositionChanged: (mouse) => paint(mouse)
        onReleased: ccLane.pe.ccEditDone()
        onPressAndHold: (mouse) => { held = true; ccLane.pe.removeCc(Math.floor(mouse.x / ccLane.sw)) }
    }
}
