// Level meter: the gradient over the full height, the part above the level covered by a
// rectangle in the background colour. No clip: clipping keeps the scene graph from batching.
import QtQuick

Item {
    id: root

    property real value   // 0..1

    width: 6

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.meterHigh }
            GradientStop { position: 0.2; color: Theme.meterMid }
            GradientStop { position: 0.45; color: Theme.meterLow }
        }
    }
    Rectangle {
        width: parent.width
        height: parent.height * (1 - root.value)
        color: Theme.panel
    }
}
