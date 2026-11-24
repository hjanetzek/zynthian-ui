// Touch on a cell of chain control's grid, for every theme's ControlCell (shared, as
// ControllerTouch for the controller column): drag up / down changes it like an encoder (one step
// per 8 px; on any page, the selection stays), a tap selects its page (and switches a toggle,
// presses a trigger, steps a list, opens a file controller's file selector; while MIDI learning:
// learns it), a long press selects its page and opens the controller's options, the wheel nudges
// it. Fills its parent.
import QtQuick

Item {
    id: touch
    property var ctrl: null           // GridCellProxy
    readonly property bool valid: ctrl !== null && ctrl.valid
    readonly property bool active: ctrl !== null && ctrl.active

    anchors.fill: parent

    DragHandler {
        target: null
        enabled: touch.active && touch.ctrl.enabled
        xAxis.enabled: Theme.uiSideways
        yAxis.enabled: !Theme.uiSideways
        property real lastY: 0
        onActiveChanged: { lastY = 0; if (active) touch.ctrl.touched() }
        onTranslationChanged: {
            const steps = Math.trunc((lastY - Theme.localDrag(touch, centroid).y) / 8)
            if (steps !== 0) {
                touch.ctrl.nudge(steps)
                lastY -= steps * 8
            }
        }
    }
    TapHandler {
        enabled: touch.valid
        onTapped: touch.ctrl.tapped()
        onLongPressed: touch.ctrl.options()
    }
    WheelHandler {
        enabled: touch.active && touch.ctrl.enabled
        onWheel: event => touch.ctrl.nudge(event.angleDelta.y > 0 ? 1 : -1)
    }
}
