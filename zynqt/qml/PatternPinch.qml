// Two-finger pinch on the pattern grid (Tk's on_gesture: the zoom). The zoom follows the fingers'
// distance from the cell size at the start, and the cell under the fingers' centre stays under
// it (the grid also follows the centre). Declared inside the grid's Flickable; `view` is the
// screen with rowHeight, stepWidth, baseRowHeight and pe. The Flickable must not be interactive
// while `active` (it would move the content as well).
import QtQuick

PinchHandler {
    id: pinch
    required property Flickable grid
    required property var view
    target: null
    grabPermissions: PointerHandler.CanTakeOverFromAnything

    property real startRowHeight: 0
    property real anchorStep: 0     // the content point under the centre: in steps from the left
    property real anchorRow: 0      // ... and in rows from the bottom

    function centre() {
        return grid.mapFromItem(null, centroid.scenePosition.x, centroid.scenePosition.y)
    }
    function place() {
        const c = centre()
        grid.contentX = Math.max(0, Math.min(grid.contentWidth - grid.width, anchorStep * view.stepWidth - c.x))
        grid.contentY = Math.max(0, Math.min(grid.contentHeight - grid.height,
                                             grid.contentHeight - anchorRow * view.rowHeight - c.y))
    }
    onActiveChanged: {
        if (!active)
            return
        grid.cancelFlick()
        startRowHeight = view.rowHeight
        const c = centre()
        anchorStep = (grid.contentX + c.x) / view.stepWidth
        anchorRow = (grid.contentHeight - grid.contentY - c.y) / view.rowHeight
    }
    onActiveScaleChanged: {
        if (!active)
            return
        // setZoom updates the cell sizes and the content size at once (bindings)
        view.pe.setZoom(Math.round(startRowHeight * activeScale - view.baseRowHeight))
        place()
    }
    onCentroidChanged: if (active) place()
}
