// The pattern editor's playhead over the grid or the CC view: a vertical line at `pos` (steps,
// with the fraction; < 0 or >= steps: hidden) and a gradient tail behind it (to the left), wrapped
// to the pattern's end near step 0. Plain Rectangles with a horizontal Gradient (no shaders, for
// the software renderer). Theme tokens: playheadLineWidth, playheadColor, playheadTailColor,
// playheadTailSteps, playheadTailOpacity, playheadTailCurve. The grid uses two instances, the
// tail behind the notes and the line above them. Only the x of these items changes per frame.
import QtQuick

Item {
    id: ph
    property real pos: -1
    property real stepWidth: 1
    property int steps: 1
    property bool showLine: true
    property bool showTail: true

    readonly property real patternWidth: steps * stepWidth
    readonly property bool shown: pos >= 0 && pos < steps
    // whole pixels: the items move (and repaint) only when the line moves by a pixel
    readonly property int lineX: Math.round(pos * stepWidth)
    readonly property int tailWidth: Math.max(0, Math.round(Theme.playheadTailSteps * stepWidth))
    readonly property int lineWidth: Math.max(1, Math.round(Theme.playheadLineWidth))

    width: patternWidth
    // The tail may reach past the pattern's ends: the grid's Flickable clips it there; where
    // nothing clips (the CC view) set clip (it costs batching, docs/qt-theming.md "Performance")
    visible: shown

    function tailColor(t) {
        const c = Theme.playheadTailColor
        return Qt.rgba(c.r, c.g, c.b, c.a * Theme.playheadTailOpacity * Math.pow(t, Theme.playheadTailCurve))
    }
    // the tail, and its part past the pattern's end when the line is near step 0
    Repeater {
        model: ph.showTail && ph.tailWidth > 0 && Theme.playheadTailOpacity > 0 ? 2 : 0
        Rectangle {
            required property int index
            x: ph.lineX - ph.tailWidth + index * ph.patternWidth
            visible: index === 0 || x < ph.patternWidth
            width: ph.tailWidth
            height: ph.height
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: ph.tailColor(0) }
                GradientStop { position: 0.25; color: ph.tailColor(0.25) }
                GradientStop { position: 0.5; color: ph.tailColor(0.5) }
                GradientStop { position: 0.75; color: ph.tailColor(0.75) }
                GradientStop { position: 1; color: ph.tailColor(1) }
            }
        }
    }
    Rectangle {
        visible: ph.showLine
        x: Math.max(0, Math.min(ph.patternWidth - width, ph.lineX - Math.floor(width / 2)))
        width: ph.lineWidth
        height: ph.height
        color: Theme.playheadColor
    }
}
