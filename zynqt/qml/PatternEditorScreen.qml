// Pattern editor (notes): toolbar, piano keys (left, scrolling with the grid), playhead, and the
// grid: steps across, keymap rows up. Tap a cell adds/removes a note, long press edits it.
import QtQuick

Item {
    id: root

    readonly property var pe: zyn.patternEditor
    readonly property var rows: pe.rows
    readonly property int nRows: rows.length
    readonly property int steps: Math.max(1, pe.steps)
    readonly property real keyWidth: 72
    // Zoom (knob 1, pinch) as Tk's set_grid_zoom: base sizes plus the zoom, within limits
    readonly property real baseRowHeight: 34
    readonly property real baseStepWidth: Math.max(30, grid.width / Math.min(steps, 32))
    readonly property real minRowHeight: Math.floor(grid.height / Math.min(36, Math.max(6, nRows)))
    readonly property real maxRowHeight: Math.max(baseRowHeight, Math.floor(grid.height / 6))
    readonly property real minStepWidth: Math.min(baseStepWidth, Math.floor(grid.width / Math.min(64, Math.max(8, steps))))
    readonly property real maxStepWidth: Math.max(baseStepWidth, Math.floor(grid.width / 8))
    readonly property real rowHeight: Math.max(Math.min(minRowHeight, baseRowHeight), Math.min(maxRowHeight, baseRowHeight + pe.zoomValue))
    readonly property real stepWidth: Math.max(minStepWidth, Math.min(maxStepWidth, baseStepWidth + pe.zoomValue))
    function reportZoomLimits() {
        if (grid.width > 0 && grid.height > 0)
            pe.setZoomLimits(Math.round(Math.min(minRowHeight - baseRowHeight, minStepWidth - baseStepWidth)),
                             Math.round(Math.max(maxRowHeight - baseRowHeight, maxStepWidth - baseStepWidth)))
    }
    onMinRowHeightChanged: Qt.callLater(reportZoomLimits)
    onMaxStepWidthChanged: Qt.callLater(reportZoomLimits)
    onBaseStepWidthChanged: Qt.callLater(reportZoomLimits)
    readonly property var cursor: pe.cursorCell
    // Rows shown (Tk's view_rows, for the cursor row of the next pattern loaded)
    readonly property int viewRows: Math.max(1, Math.floor(grid.height / rowHeight))
    onViewRowsChanged: pe.setViewRows(viewRows)
    Component.onCompleted: pe.setViewRows(viewRows)

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

    // Toolbar (+tk: none, as Tk)
    PatternToolbar {
        id: toolbar
        pe: root.pe
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 4
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
        visible: !root.pe.ccMode
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
        visible: !root.pe.ccMode
        anchors.left: keys.right
        anchors.right: parent.right
        anchors.top: playStrip.bottom
        anchors.bottom: parent.bottom
        anchors.leftMargin: 2
        contentWidth: root.steps * root.stepWidth
        contentHeight: root.nRows * root.rowHeight
        clip: true
        interactive: !root.pe.selectMode && !pinch.active   // select mode: drags select a block
        boundsBehavior: Flickable.StopAtBounds
        // Pinch: the zoom (Tk's on_gesture)
        PatternPinch {
            id: pinch
            grid: grid
            view: root
        }

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
                    color: root.rows[root.nRows - 1 - index].black ? Theme.gridRowDark : Theme.gridRow
                    Rectangle { width: parent.width; height: 1; color: Theme.gridRowLine }
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
                    color: bar ? Theme.gridBar : (beat ? Theme.gridBeat : Theme.gridStep)
                }
            }
            // Notes (brighter with velocity; faded if never played), with their stutter (ticks:
            // retriggers, rising or falling with its velocity effect) and play/stutter frequency
            // or chance
            Repeater {
                model: root.pe.events
                PatternNote {
                    stepWidth: root.stepWidth
                    rowHeight: root.rowHeight
                    nRows: root.nRows
                }
            }
            // The copied block moved by the knobs (block edit mode), before it is pasted
            Repeater {
                model: root.pe.copyEvents
                PatternNote {
                    stepWidth: root.stepWidth
                    rowHeight: root.rowHeight
                    nRows: root.nRows
                    opacity: 0.6
                    fill: Theme.selectionFill
                }
            }
            // Selected block
            Rectangle {
                readonly property var b: root.pe.block
                visible: b.length === 4
                x: (b[0] || 0) * root.stepWidth
                y: root.rowY(b[3] || 0)
                width: ((b[2] || 0) - (b[0] || 0) + 1) * root.stepWidth
                height: ((b[3] || 0) - (b[1] || 0) + 1) * root.rowHeight
                color: Theme.selectionFill
                border.color: Theme.selectionFrame
                border.width: 2
            }
            // Select mode: drag marks a block
            DragHandler {
                enabled: root.pe.selectMode
                target: null
                dragThreshold: 4
                property var start: null
                onActiveChanged: if (active) start = [Math.floor(centroid.pressPosition.x / root.stepWidth),
                                                      root.nRows - 1 - Math.floor(centroid.pressPosition.y / root.rowHeight)]
                onCentroidChanged: if (active && start) root.pe.selectBlock(start[0], start[1],
                                            Math.floor(centroid.position.x / root.stepWidth),
                                            root.nRows - 1 - Math.floor(centroid.position.y / root.rowHeight))
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
                    if (root.pe.selectMode && root.pe.hasCopy)
                        root.pe.pasteAt(c[0], c[1])
                    else if (!root.pe.selectMode)
                        root.pe.toggleNote(c[0], c[1])
                }
                onLongPressed: {
                    const c = cell(point.position)
                    root.pe.editNote(c[0], c[1])
                }
            }
        }
    }

    // CC view
    PatternCcLane {
        visible: root.pe.ccMode
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: playStrip.bottom
        anchors.bottom: parent.bottom
        anchors.leftMargin: root.keyWidth + 2
        anchors.topMargin: 4
        pe: root.pe
        steps: root.steps
        keyWidth: root.keyWidth
    }
}
