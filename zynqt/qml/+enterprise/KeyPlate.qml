import QtQuick
import ".."

// Enterprise: filled keys in the key's colour, all with one corner radius: Theme.keyRadius of the
// keypad's smallest key side (minSide, without the margins; 0.25), so all keys are rounded plates
// with the same corners, side and bottom keys alike
Panel {
    property color fill: Theme.keyBackground
    property bool pressed: false
    property real minSide: Math.min(width, height)   // the keypad's smallest key side (Keypad.qml)

    anchors.margins: 3
    cornerRadius: Theme.keyRadius > 0 ? Theme.keyRadius * Math.max(0, minSide - 2 * anchors.margins) : -1
    color: pressed ? Qt.lighter(fill, 1.25) : fill
    borderColor: "transparent"
    borderWidth: 0
}
