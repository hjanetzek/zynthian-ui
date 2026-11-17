// tk: the pattern editor as zynthian_gui_pated_notes draws it. No toolbar; the piano roll on the
// left (9 % of the width), the grid on black (row lines: the tonic's brighter; step lines: bars
// white, beats grey, steps dark), notes grey by velocity (selected blue, the moving copy green),
// the cursor and block in red; below: the velocity bar (yellow) and the play ruler (beat
// numbers, step ticks, the playhead in red). Cell sizes from 16 x 16 cells plus the zoom (knob
// 1, pinch). Tap toggles a note, a bold press edits it (the knobs, title bar), drag scrolls.
import QtQuick

Rectangle {
    id: root

    readonly property var pe: zyn.patternEditor
    readonly property var rows: pe.rows
    readonly property int nRows: rows.length
    readonly property int steps: Math.max(1, pe.steps)
    readonly property var cursor: pe.cursorCell
    readonly property int playheadHeight: 12

    // zynthian_gui_pated_base geometry
    readonly property int gridWidth: Math.floor(width * 0.91)
    readonly property int keyWidth: width - gridWidth
    readonly property int gridHeight: height - playheadHeight
    readonly property int baseRowHeight: Math.floor(gridHeight / 16)
    readonly property int baseStepWidth: Math.floor(gridWidth / Math.min(16, steps))
    readonly property int maxRowHeight: Math.floor(gridHeight / 6)
    readonly property int minRowHeight: Math.floor(gridHeight / Math.min(36, Math.max(6, nRows)))
    readonly property int maxStepWidth: Math.floor(gridWidth / 8)
    readonly property int minStepWidth: Math.floor(gridWidth / Math.min(64, Math.max(8, steps)))
    readonly property int rowHeight: Math.max(minRowHeight, Math.min(maxRowHeight, baseRowHeight + pe.zoomValue))
    readonly property int stepWidth: Math.max(minStepWidth, Math.min(maxStepWidth, baseStepWidth + pe.zoomValue))
    readonly property int selectThickness: 1 + Math.floor(width / 500)
    readonly property int gridFont: Math.min(20, Math.floor(rowHeight / 2))
    // Rows shown (Tk's view_rows, for the cursor row of the next pattern loaded)
    readonly property int viewRows: Math.max(1, Math.floor(gridHeight / rowHeight))
    onViewRowsChanged: if (height > 0) pe.setViewRows(viewRows)

    function reportZoomLimits() {
        if (gridWidth > 0 && gridHeight > 0)
            pe.setZoomLimits(Math.min(minRowHeight - baseRowHeight, minStepWidth - baseStepWidth),
                             Math.max(maxRowHeight - baseRowHeight, maxStepWidth - baseStepWidth))
    }
    onMinRowHeightChanged: Qt.callLater(reportZoomLimits)
    onMinStepWidthChanged: Qt.callLater(reportZoomLimits)
    onBaseStepWidthChanged: Qt.callLater(reportZoomLimits)
    onGridHeightChanged: Qt.callLater(reportZoomLimits)

    function rowY(row) { return (nRows - 1 - row) * rowHeight }
    function grey(v) {
        const c = Math.min(255, v + 70) / 255
        return Qt.rgba(c, c, c, 1)
    }

    // Keep the cursor in view (select_cell: set_step_offset / set_keymap_offset)
    function showCursor() {
        const y = rowY(cursor[1])
        if (y < grid.contentY)
            grid.contentY = Math.max(0, y)
        else if (y + rowHeight > grid.contentY + grid.height)
            grid.contentY = Math.min(grid.contentHeight - grid.height, y + rowHeight - grid.height)
        const x = cursor[0] * stepWidth
        if (x < grid.contentX)
            grid.contentX = Math.max(0, x)
        else if (x + stepWidth > grid.contentX + grid.width)
            grid.contentX = Math.max(0, Math.min(grid.contentWidth - grid.width, x + stepWidth - grid.width))
    }
    onCursorChanged: Qt.callLater(showCursor)
    // Zoom keeps the bottom row and the left step (Tk: keymap_offset, step_offset)
    property real lastRowHeight: rowHeight
    property real lastStepWidth: stepWidth
    onRowHeightChanged: {
        // Not while the screen gets its size (the bindings start from 0): showRefRow places it;
        // a pinch places the grid itself (under the fingers)
        if (lastRowHeight <= 0 || grid.height <= 0 || pinch.active) {
            lastRowHeight = rowHeight
            return
        }
        const bottom = (grid.contentHeight - grid.contentY - grid.height) / lastRowHeight
        lastRowHeight = rowHeight
        Qt.callLater(() => {
            grid.contentY = Math.max(0, Math.min(grid.contentHeight - grid.height,
                                                 grid.contentHeight - grid.height - bottom * rowHeight))
            showCursor()
        })
    }
    onStepWidthChanged: {
        const left = grid.contentX / lastStepWidth
        lastStepWidth = stepWidth
        if (pinch.active)
            return
        Qt.callLater(() => {
            grid.contentX = Math.max(0, Math.min(grid.contentWidth - grid.width, left * stepWidth))
            showCursor()
        })
    }
    Connections {
        target: root.pe
        function onPatternChanged() { Qt.callLater(root.showRefRow) }
    }
    // Tk (load_pattern, set_keymap_offset): the pattern's reference note as the bottom row, the
    // cursor in the middle of the view rows above it. Also when this screen is created: the
    // pattern was loaded before (the Loader creates the screen after the switch)
    function showRefRow() {
        grid.contentY = Math.max(0, Math.min(grid.contentHeight - grid.height,
                                             grid.contentHeight - grid.height - pe.refRow * rowHeight))
        showCursor()
    }
    Component.onCompleted: {
        if (height > 0)
            pe.setViewRows(viewRows)
        Qt.callLater(showRefRow)
    }

    color: Theme.background

    PatternToolbar { id: toolbar; pe: root.pe }

    // Piano roll
    Item {
        id: keys
        visible: !root.pe.ccMode
        x: 0
        width: root.keyWidth
        height: root.gridHeight
        clip: true
        Column {
            y: -grid.contentY
            Repeater {
                model: root.nRows
                Item {
                    id: key
                    required property int index
                    readonly property int row: root.nRows - 1 - index
                    readonly property var k: root.rows[row]
                    width: root.keyWidth
                    height: root.rowHeight
                    Rectangle {
                        y: 1
                        width: parent.width
                        height: parent.height - 1
                        color: key.k.black ? "#000000" : "#ffffff"
                    }
                    Text {
                        x: 2
                        anchors.verticalCenter: parent.verticalCenter
                        visible: text !== ""
                        text: key.k.name
                        color: key.k.black ? "#ffffff" : Theme.background
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.tkPx(root.gridFont)
                    }
                    TapHandler { onTapped: root.pe.playRow(key.row) }
                }
            }
        }
    }

    Flickable {
        id: grid
        visible: !root.pe.ccMode
        x: root.keyWidth
        width: root.gridWidth
        height: root.gridHeight
        contentWidth: root.steps * root.stepWidth
        contentHeight: Math.max(root.nRows * root.rowHeight, height)
        clip: true
        interactive: !root.pe.selectMode && !pinch.active
        boundsBehavior: Flickable.StopAtBounds
        flickDeceleration: 3000

        // The bottom row shown is the pattern's reference note (Tk's keymap_offset): kept
        // (only after the user scrolled: the programmatic centring would drift by rounding)
        onMovementEnded: refNoteTimer.restart()
        Timer {
            id: refNoteTimer
            interval: 300
            onTriggered: root.pe.setRefNote(Math.max(0, Math.round((grid.contentHeight - grid.contentY - grid.height) / root.rowHeight)))
        }
        PatternPinch {
            id: pinch
            grid: grid
            view: root
            // the bottom row kept as the reference note (as after a scroll)
            onActiveChanged: if (!active) refNoteTimer.restart()
        }

        Item {
            id: content
            width: grid.contentWidth
            height: grid.contentHeight
            readonly property real rowsTop: height - root.nRows * root.rowHeight

            // Row lines (GRID_LINE_STRONG on the tonic, else GRID_LINE_WEAK)
            Repeater {
                model: root.nRows
                Rectangle {
                    required property int index
                    y: content.rowsTop + root.rowY(index) + root.rowHeight
                    width: content.width
                    height: 1
                    color: root.pe && root.rows[index].note % 12 === root.pe.tonic ? "#a0a0a0" : "#505050"
                }
            }
            // Step lines: bars white, beats grey, steps dark
            Repeater {
                model: root.steps + 1
                Rectangle {
                    required property int index
                    readonly property int spb: Math.max(1, root.pe.stepsPerBeat)
                    readonly property bool beat: index % spb === 0
                    readonly property bool bar: beat && (index / spb) % Math.max(1, root.pe.beatsPerBar) === 0
                    x: index * root.stepWidth
                    width: 1
                    height: content.height
                    color: bar ? "#ffffff" : (beat ? "#a0a0a0" : "#505050")
                }
            }
            Item {
                y: content.rowsTop
                width: content.width
                height: root.nRows * root.rowHeight
                Repeater {
                    model: root.pe.events
                    PatternNote {
                        stepWidth: root.stepWidth
                        rowHeight: root.rowHeight
                        nRows: root.nRows
                        // get_cell: no frame, 1 px inside the cell
                        x: Math.floor(modelData.step * root.stepWidth) + 1
                        y: root.rowY(modelData.row) + 1
                        width: Math.max(1, Math.floor(root.stepWidth * modelData.duration) - 1)
                        height: root.rowHeight - 1
                        radius: 0
                        border.width: 0
                        readonly property int v: Math.min(255, modelData.velocity + 70)
                        fill: modelData.selected ? Qt.rgba(v / 510, v / 510, v / 255, 1) : root.grey(modelData.velocity)
                    }
                }
                Repeater {
                    model: root.pe.copyEvents
                    PatternNote {
                        stepWidth: root.stepWidth
                        rowHeight: root.rowHeight
                        nRows: root.nRows
                        x: Math.floor(modelData.step * root.stepWidth) + 1
                        y: root.rowY(modelData.row) + 1
                        width: Math.max(1, Math.floor(root.stepWidth * modelData.duration) - 1)
                        height: root.rowHeight - 1
                        radius: 0
                        border.width: 0
                        readonly property int v: Math.min(255, modelData.velocity + 70)
                        fill: Qt.rgba(v / 510, v / 255, v / 510, 1)
                    }
                }
                // Selected block (red frame)
                Rectangle {
                    readonly property var b: root.pe.copyEvents.length ? [] : root.pe.block
                    visible: b.length === 4
                    x: (b[0] || 0) * root.stepWidth
                    y: root.rowY(b[3] || 0)
                    width: ((b[2] || 0) - (b[0] || 0) + 1) * root.stepWidth
                    height: ((b[3] || 0) - (b[1] || 0) + 1) * root.rowHeight
                    color: "transparent"
                    border.color: Theme.select
                    border.width: root.selectThickness
                }
                // Cursor: the note's extent (or one cell), red; hidden in the block mode
                Rectangle {
                    visible: !root.pe.selectMode
                    x: root.cursor[0] * root.stepWidth
                    y: root.rowY(root.cursor[1])
                    width: Math.max(1, Math.floor(root.stepWidth * root.pe.cursorDuration)) + 1
                    height: root.rowHeight + 1
                    color: "transparent"
                    border.color: Theme.select
                    border.width: root.selectThickness
                }
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
                TapHandler {
                    enabled: root.pe.selectMode && root.pe.hasCopy
                    onTapped: (eventPoint) => root.pe.pasteAt(Math.floor(eventPoint.position.x / root.stepWidth),
                        root.nRows - 1 - Math.floor(eventPoint.position.y / root.rowHeight))
                }
                // zynthian_gui_pated_notes on_grid_press / drag / release: a tap toggles the
                // note; held (800 ms) without moving: the note's parameters (edit mode); held,
                // then dragged: on a note up / down its velocity, sideways its duration; on an
                // empty cell the cursor follows and the note is added on release. A drag
                // without holding scrolls (the Flickable).
                MouseArea {
                    anchors.fill: parent
                    enabled: !root.pe.selectMode
                    pressAndHoldInterval: 800
                    preventStealing: held
                    property bool held: false
                    property bool dragged: false
                    property var start: null      // [step, row]
                    property var note: []          // [start step, velocity, duration]
                    property point pressPos
                    function cell(x, y) {
                        return [Math.floor(x / root.stepWidth), root.nRows - 1 - Math.floor(y / root.rowHeight)]
                    }
                    onPressed: (mouse) => {
                        held = false; dragged = false
                        pressPos = Qt.point(mouse.x, mouse.y)
                        start = cell(mouse.x, mouse.y)
                        note = root.pe.noteAt(start[0], start[1])
                        if (note.length)
                            start[0] = note[0]
                        root.pe.setCursor(start[0], start[1])
                    }
                    onPressAndHold: held = true
                    onPositionChanged: (mouse) => {
                        if (!held)
                            return
                        dragged = true
                        if (note.length) {
                            if (Math.abs(mouse.y - pressPos.y) > root.rowHeight / 2 && !durationMode)
                                velocityMode = true
                            else if ((mouse.x > (start[0] + 1) * root.stepWidth || mouse.x < start[0] * root.stepWidth) && !velocityMode)
                                durationMode = true
                            if (velocityMode)
                                root.pe.dragVelocity(start[0], start[1],
                                    Math.round(note[1] + (pressPos.y - mouse.y) / root.rowHeight * root.height / 100))
                            if (durationMode)
                                root.pe.dragDuration(start[0], start[1], Math.floor(mouse.x / root.stepWidth) - start[0])
                        } else {
                            const c = cell(mouse.x, mouse.y)
                            root.pe.setCursor(c[0], c[1])
                        }
                    }
                    property bool velocityMode: false
                    property bool durationMode: false
                    onReleased: (mouse) => {
                        if (!held)
                            root.pe.toggleNote(start[0], start[1])
                        else if (!dragged)
                            root.pe.touchBold(start[0], start[1])
                        else if (!note.length)
                            root.pe.toggleNote(root.cursor[0], root.cursor[1])
                        else
                            root.pe.editDone()
                        held = false; velocityMode = false; durationMode = false
                    }
                    onCanceled: { held = false; velocityMode = false; durationMode = false; root.pe.editDone() }
                }
            }
        }
    }

    // Velocity bar (under the piano roll; not in the CC view, as zynthian_gui_pated_cc)
    Rectangle {
        visible: !root.pe.ccMode
        x: 0
        y: root.gridHeight
        width: root.keyWidth
        height: root.playheadHeight
        color: "#282828"
        Rectangle {
            width: parent.width * root.pe.cursorVelocity / 127
            height: parent.height
            color: "#ffff00"
        }
    }

    // Play ruler: beat numbers, step ticks, the playhead
    Item {
        x: root.keyWidth
        y: root.gridHeight
        width: root.gridWidth
        height: root.playheadHeight
        clip: true
        Rectangle { anchors.fill: parent; color: "#282828" }
        Item {
            x: -grid.contentX
            height: parent.height
            Rectangle {
                x: 1 + root.pe.playhead * root.stepWidth
                width: root.stepWidth
                height: parent.height
                visible: root.pe.playhead >= 0
                color: Theme.select
            }
            Repeater {
                model: root.steps
                Item {
                    required property int index
                    readonly property int spb: Math.max(1, root.pe.stepsPerBeat)
                    x: index * root.stepWidth
                    Rectangle {
                        visible: parent.index % parent.spb !== 0
                        width: 1
                        height: Math.floor(0.7 * root.playheadHeight)
                        color: Theme.textOff
                    }
                    Text {
                        visible: parent.index % parent.spb === 0
                        x: parent.index === 0 ? 0 : -width / 2
                        y: -2
                        text: Math.floor(parent.index / parent.spb) + 1
                        color: "#a0a0a0"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.tkPx(root.playheadHeight - 2)
                    }
                }
            }
        }
    }

    // CC view
    PatternCcLane {
        visible: root.pe.ccMode
        x: root.keyWidth
        width: root.gridWidth
        height: root.gridHeight
        pe: root.pe
        steps: root.steps
        keyWidth: root.keyWidth
    }
}
