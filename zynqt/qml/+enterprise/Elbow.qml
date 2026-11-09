// Frame of the enterprise theme: an elbow, a horizontal arm (under the top bar) joined to a wider
// vertical bar (left of the screens) by a rounded outer and inner corner, the vertical bar ending
// in a half circle. One filled ShapePath.
import QtQuick
import ".."
import QtQuick.Shapes

Shape {
    id: root

    property color color: Theme.elbowColor
    property real arm: 180                    // length of the horizontal arm
    property real thickness: Theme.elbowBar   // of the horizontal arm
    property real barWidth: thickness * 1.6   // of the vertical bar

    readonly property real _R: thickness * 2.2    // outer corner
    readonly property real _r: thickness          // inner corner

    ShapePath {
        fillColor: root.color
        strokeColor: "transparent"
        startX: 0; startY: root._R
        PathArc { x: root._R; y: 0; radiusX: root._R; radiusY: root._R; direction: PathArc.Clockwise }
        PathLine { x: root.arm; y: 0 }
        PathLine { x: root.arm; y: root.thickness }
        PathLine { x: root.barWidth + root._r; y: root.thickness }
        PathArc {
            x: root.barWidth; y: root.thickness + root._r
            radiusX: root._r; radiusY: root._r; direction: PathArc.Counterclockwise
        }
        PathLine { x: root.barWidth; y: root.height - root.barWidth / 2 }
        PathArc {
            x: 0; y: root.height - root.barWidth / 2
            radiusX: root.barWidth / 2; radiusY: root.barWidth / 2; direction: PathArc.Clockwise
        }
        PathLine { x: 0; y: root._R }
    }
}
