// Touch on a controller slot, for every theme's Controller (shared): drag up / down changes it like
// an encoder (zctrl.nudge: integer, logarithmic and enumerated values step as with the knobs, one
// step per 8 px), a tap switches a toggle or opens a file controller's file selector (while MIDI
// learning: learns it), a long press opens its options (MIDI learn, X-Y, ...), the wheel nudges it.
// Fills its parent.
import QtQuick

Item {
    id: touch
    property var ctrl: null
    readonly property bool active: ctrl !== null && ctrl.active

    anchors.fill: parent

    DragHandler {
        target: null
        enabled: touch.active
        // Up / down in the rotated UI (ZYNTHIAN_UI_ROTATION)
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
        enabled: touch.active
        onTapped: {
            if (touch.ctrl.bindKind.indexOf("learn") === 0 || zyn.chainControl.learnText !== "")
                touch.ctrl.touched()
            else if (touch.ctrl.isToggle)
                touch.ctrl.toggle()
            else if (touch.ctrl.isPath)
                touch.ctrl.nudge(1)     // a file: the file selector (zynthian_gui_controller)
        }
        onLongPressed: touch.ctrl.options()
    }
    WheelHandler {
        enabled: touch.active
        onWheel: event => touch.ctrl.nudge(event.angleDelta.y > 0 ? 1 : -1)
    }
}
