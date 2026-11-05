// Level meter as in Zrythm (Meter.qml): rectangles, no custom drawing. The gradient covers the
// meter's full height and is uncovered from the bottom up to the level.
import QtQuick

Item {
    id: root

    property real value   // 0..1

    width: 6

    Item {
        anchors.bottom: parent.bottom
        width: parent.width
        height: parent.height * root.value
        clip: true

        Rectangle {
            anchors.bottom: parent.bottom
            width: root.width
            height: root.height
            gradient: Gradient {
                GradientStop { position: 0.0; color: Theme.meterHigh }
                GradientStop { position: 0.2; color: Theme.meterMid }
                GradientStop { position: 0.45; color: Theme.meterLow }
            }
        }
    }
}
