import QtQuick
import ".."

// The plate of a keypad key. Classic: square keys with a 1 px gap. In the overlay keypad
// translucent, the blurred screen showing through. Themes replace it (+<theme>/KeyPlate.qml).
Panel {
    property color fill: Theme.keyBackground   // the key's colour in themes with filled keys
    property bool pressed: false
    property bool translucent: false
    property real minSide: Math.min(width, height)   // the keypad's smallest key side (Keypad.qml)

    color: {
        const c = pressed ? Qt.lighter(Theme.keyBackground, 1.8) : Theme.keyBackground
        return translucent ? Qt.rgba(c.r, c.g, c.b, pressed ? 0.85 : 0.55) : c
    }
    borderColor: translucent ? Qt.rgba(1, 1, 1, 0.15) : Theme.background
    borderWidth: 1
}
