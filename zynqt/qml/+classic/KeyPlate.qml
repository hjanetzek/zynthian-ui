import QtQuick
import ".."

// The plate of a keypad key. Classic: square keys with a 1 px gap. Themes replace it
// (+<theme>/KeyPlate.qml).
Panel {
    property color fill: Theme.keyBackground   // the key's colour in themes with filled keys
    property bool pressed: false
    property real minSide: Math.min(width, height)   // the keypad's smallest key side (Keypad.qml)

    color: pressed ? Qt.lighter(Theme.keyBackground, 1.8) : Theme.keyBackground
    borderColor: Theme.background
    borderWidth: 1
}
