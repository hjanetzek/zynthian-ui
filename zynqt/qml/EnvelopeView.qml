// Envelope of a controller page (zynthian_widget_envelope): drag a phase to change it
// (attack, decay, hold, release sideways; sustain and fade up/down)
import QtQuick
import QtQuick.Shapes

Rectangle {
    id: root

    property var view
    color: "#101418"
    clip: true

    onWidthChanged: if (view && width > 0) view.setSize(width, height)
    onHeightChanged: if (view && width > 0) view.setSize(width, height)
    onViewChanged: if (view && width > 0) view.setSize(width, height)

    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.GeometryRenderer
        ShapePath {
            strokeWidth: 3
            strokeColor: "#5a9ef0"
            fillColor: "#203a58"
            joinStyle: ShapePath.RoundJoin
            PathPolyline { path: root.view ? root.view.shape : [] }
        }
    }
    // The dragged phase
    Shape {
        anchors.fill: parent
        visible: root.view && root.view.dragShape.length > 0
        preferredRendererType: Shape.GeometryRenderer
        ShapePath {
            strokeWidth: 3
            strokeColor: "#5a9ef0"
            fillColor: "#5a9ef0"
            PathPolyline { path: root.view ? root.view.dragShape : [] }
        }
    }
    MouseArea {
        anchors.fill: parent
        preventStealing: true
        onPressed: (mouse) => root.view.press(mouse.x, mouse.y)
        onPositionChanged: (mouse) => root.view.drag(mouse.x, mouse.y)
        onReleased: root.view.release()
        onCanceled: root.view.release()
    }
}
