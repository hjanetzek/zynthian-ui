// Level meter (as zynthian_gui_dpm): the gradient over the full height, the part above the level
// covered in the background colour, and a peak-hold line. Values are fractions of the height
// (MixerMeters). No clip: clipping keeps the scene graph from batching (measured on the Duet:
// half the render thread time without it).
import QtQuick

Item {
    id: root

    property real value   // 0..1
    property real hold    // 0..1
    property color background: Theme.background

    width: 6

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.meterHigh }
            GradientStop { position: 0.06; color: Theme.meterHigh }   // over -3 dB
            GradientStop { position: 0.2; color: Theme.meterMid }     // high -10 dB
            GradientStop { position: 0.3; color: Theme.meterLow }
        }
    }
    Rectangle {
        width: parent.width
        height: parent.height * (1 - root.value)
        color: root.background
    }
    Rectangle {
        visible: root.hold > 0
        width: parent.width
        height: 2
        y: parent.height * (1 - root.hold)
        color: root.hold > 0.94 ? Theme.meterHigh : (root.hold > 0.8 ? Theme.meterMid : Theme.meterLow)
    }
}
