// Filter response of a controller page (zynthian_widget_filter): an XY pad, drag sideways for
// the cutoff, up/down for the resonance
import QtQuick
import QtQuick.Shapes

Rectangle {
    id: root

    property var view
    color: Theme.widgetBackground
    clip: true

    onWidthChanged: if (view && width > 0) view.setSize(width, height)
    onHeightChanged: if (view && width > 0) view.setSize(width, height)
    onViewChanged: if (view && width > 0) view.setSize(width, height)

    // Grid: dB lines, 8 frequency divisions
    Repeater {
        model: root.view ? root.view.gridY : []
        Rectangle {
            required property real modelData
            x: 10; y: modelData; width: root.width - 20; height: 1; color: Theme.widgetGrid
        }
    }
    Repeater {
        model: 9
        Rectangle {
            required property int index
            x: 10 + (root.width - 20) * index / 8; y: 10; width: 1; height: root.height - 20; color: Theme.widgetGrid
        }
    }
    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.GeometryRenderer
        ShapePath {
            strokeWidth: 2
            strokeColor: Theme.widgetLine
            fillColor: Theme.widgetFill
            PathPolyline { path: root.view ? root.view.shape : [] }
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
