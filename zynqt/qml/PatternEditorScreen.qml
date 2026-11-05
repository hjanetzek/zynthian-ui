// Pattern editor (notes): toolbar, piano keys (left, scrolling with the grid), playhead, and the
// grid: steps across, keymap rows up. Tap a cell adds/removes a note, long press edits it.
import QtQuick

Item {
    id: root

    readonly property var pe: zyn.patternEditor
    readonly property var rows: pe.rows
    readonly property int nRows: rows.length
    readonly property int steps: Math.max(1, pe.steps)
    readonly property real rowHeight: 34
    readonly property real keyWidth: 72
    readonly property real stepWidth: Math.max(30, grid.width / Math.min(steps, 32))
    readonly property var cursor: pe.cursorCell

    function rowY(row) { return (nRows - 1 - row) * rowHeight }

    // Show the cursor's row
    function showCursor() {
        const y = rowY(cursor[1])
        if (y < grid.contentY || y + rowHeight > grid.contentY + grid.height)
            grid.contentY = Math.max(0, Math.min(grid.contentHeight - grid.height, y - grid.height / 2))
        const x = cursor[0] * stepWidth
        if (x < grid.contentX || x + stepWidth > grid.contentX + grid.width)
            grid.contentX = Math.max(0, Math.min(grid.contentWidth - grid.width, x - grid.width / 2))
    }
    onCursorChanged: Qt.callLater(showCursor)
    Connections {
        target: root.pe
        function onPatternChanged() { Qt.callLater(root.showCursor) }
    }

    // Toolbar
    Row {
        id: toolbar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 4
        height: 48
        spacing: 6
        ToolButton { text: root.pe.playing ? "■ Stop" : "▶ Play"; width: 120; on: root.pe.playing; onTapped: root.pe.togglePlayback() }
        ToolButton { text: "Undo"; onTapped: root.pe.undo() }
        ToolButton { text: "Redo"; onTapped: root.pe.redo() }
        ToolButton { text: root.pe.entryText; width: 190; onTapped: root.pe.entryOptions() }
        ToolButton { text: "Menu"; onTapped: root.pe.menu() }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            width: Math.max(0, toolbar.width - x)
            elide: Text.ElideRight
            text: root.pe.title
            color: Theme.textOff
            font.pixelSize: 16
        }
    }

    // Playhead strip
    Item {
        id: playStrip
        anchors.left: grid.left
        anchors.right: grid.right
        anchors.top: toolbar.bottom
        anchors.topMargin: 4
        height: 10
        clip: true
        Rectangle { anchors.fill: parent; color: Theme.panelHighlight }
        Rectangle {
            visible: root.pe.playhead >= 0
            x: root.pe.playhead * root.stepWidth - grid.contentX
            width: root.stepWidth
            height: parent.height
            color: root.pe.playing ? Theme.meterLow : Theme.disabled
        }
    }

    // Piano keys
    Item {
        id: keys
        anchors.left: parent.left
        anchors.top: grid.top
        anchors.bottom: grid.bottom
        width: root.keyWidth
        clip: true
        Column {
            y: -grid.contentY
            Repeater {
                model: root.nRows
                Rectangle {
                    required property int index
                    readonly property var key: root.rows[root.nRows - 1 - index]
                    width: root.keyWidth
                    height: root.rowHeight
                    color: key.black ? "#202020" : "#d8d8d8"
                    border.color: "#808080"
                    border.width: 1
                    Text {
                        anchors.right: parent.right
                        anchors.rightMargin: 4
                        anchors.verticalCenter: parent.verticalCenter
                        text: parent.key.name
                        color: parent.key.black ? "#e0e0e0" : "#202020"
                        font.pixelSize: 12
                    }
                }
            }
        }
    }

    Flickable {
        id: grid
        anchors.left: keys.right
        anchors.right: parent.right
        anchors.top: playStrip.bottom
        anchors.bottom: parent.bottom
        anchors.leftMargin: 2
        contentWidth: root.steps * root.stepWidth
        contentHeight: root.nRows * root.rowHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Item {
            id: content
            width: grid.contentWidth
            height: grid.contentHeight

            // Row backgrounds (black keys darker)
            Repeater {
                model: root.nRows
                Rectangle {
                    required property int index
                    y: index * root.rowHeight
                    width: content.width
                    height: root.rowHeight
                    color: root.rows[root.nRows - 1 - index].black ? "#262c34" : "#323a45"
                    Rectangle { width: parent.width; height: 1; color: "#1c2128" }
                }
            }
            // Step lines: thicker at beats, brighter at bars
            Repeater {
                model: root.steps
                Rectangle {
                    required property int index
                    readonly property bool beat: index % root.pe.stepsPerBeat === 0
                    readonly property bool bar: index % (root.pe.stepsPerBeat * Math.max(1, root.pe.beatsPerBar)) === 0
                    x: index * root.stepWidth
                    width: bar ? 2 : 1
                    height: content.height
                    color: bar ? "#8090a0" : (beat ? "#566270" : "#2a3038")
                }
            }
            // Notes (brighter with velocity)
            Repeater {
                model: root.pe.events
                Rectangle {
                    required property var modelData
                    x: modelData.step * root.stepWidth + 1
                    y: root.rowY(modelData.row) + 2
                    width: Math.max(6, modelData.duration * root.stepWidth - 2)
                    height: root.rowHeight - 4
                    radius: 3
                    color: Qt.hsla(0.58, 0.8, 0.25 + 0.45 * modelData.velocity / 127, 1)
                    border.color: "#e0f0ff"
                    border.width: 1
                }
            }
            // Cursor
            Rectangle {
                x: root.cursor[0] * root.stepWidth
                y: root.rowY(root.cursor[1])
                width: root.stepWidth
                height: root.rowHeight
                color: "transparent"
                border.color: Theme.select
                border.width: 2
            }

            TapHandler {
                function cell(p) {
                    return [Math.floor(p.x / root.stepWidth), root.nRows - 1 - Math.floor(p.y / root.rowHeight)]
                }
                onTapped: (eventPoint) => {
                    const c = cell(eventPoint.position)
                    root.pe.toggleNote(c[0], c[1])
                }
                onLongPressed: {
                    const c = cell(point.position)
                    root.pe.editNote(c[0], c[1])
                }
            }
        }
    }

    component ToolButton: Rectangle {
        id: button
        property alias text: label.text
        property bool on: false
        signal tapped
        width: 100
        height: parent.height
        radius: 4
        color: tap.pressed ? Theme.keyText : (on ? "#206030" : Theme.keyBackground)
        Text {
            id: label
            anchors.centerIn: parent
            color: Theme.text
            font.pixelSize: 16
        }
        TapHandler { id: tap; gesturePolicy: TapHandler.ReleaseWithinBounds; onTapped: button.tapped() }
    }
}
