// Level meter (as zynthian_gui_dpm): the gradient over the full height, the part above the level
// covered in the background colour, and a peak-hold line. Values are fractions of the height
// (MixerMeters). No clip: clipping keeps the scene graph from batching (measured on the Duet:
// half the render thread time without it).
import QtQuick

Item {
    id: root

    property real value   // 0..1
    property real hold    // 0..1
    // Colour thresholds as fractions from the top, as zynthian_gui_dpm with the default 72 dB range:
    // red above -2 dB (DPM_OVER_DB), yellow above the -18 dB "0dB" reference (DPM_HIGH_DB)
    property real overPos: 2 / 72
    property real highPos: 18 / 72
    property color background: Theme.background

    width: 6

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.meterHigh }
            GradientStop { position: root.overPos; color: Theme.meterHigh }
            GradientStop { position: root.overPos + 0.01; color: Theme.meterMid }
            GradientStop { position: root.highPos; color: Theme.meterMid }
            GradientStop { position: root.highPos + 0.01; color: Theme.meterLow }
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
        color: root.hold > 1 - root.overPos ? Theme.meterHigh : (root.hold > 1 - root.highPos ? Theme.meterMid : Theme.meterLow)
    }
}
