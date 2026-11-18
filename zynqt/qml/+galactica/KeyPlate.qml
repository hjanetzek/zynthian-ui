import QtQuick
import ".."

// Galactica: plates with clipped corners and a steel outline, amber when pressed
Panel {
    property color fill: Theme.keyBackground
    property bool pressed: false
    property real minSide: Math.min(width, height)   // the keypad's smallest key side (Keypad.qml)

    anchors.margins: 2
    color: pressed ? Qt.lighter(Theme.keyBackground, 1.8) : Theme.keyBackground
    borderColor: pressed ? Theme.frameActive : Theme.frame
    borderWidth: Theme.frameWidth
}
