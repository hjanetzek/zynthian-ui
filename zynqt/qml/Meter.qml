// Level meter (as zynthian_gui_dpm): a gradient over the full height, uncovered from the bottom
// up to the level, and a peak-hold line. Values are fractions of the height (MixerMeters).
import QtQuick

Item {
    id: root

    property real value   // 0..1
    property real hold    // 0..1

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
                GradientStop { position: 0.06; color: Theme.meterHigh }   // over -3 dB
                GradientStop { position: 0.2; color: Theme.meterMid }     // high -10 dB
                GradientStop { position: 0.3; color: Theme.meterLow }
            }
        }
    }

    Rectangle {
        visible: root.hold > 0
        width: parent.width
        height: 2
        y: parent.height * (1 - root.hold)
        color: root.hold > 0.94 ? Theme.meterHigh : (root.hold > 0.8 ? Theme.meterMid : Theme.meterLow)
    }
}
