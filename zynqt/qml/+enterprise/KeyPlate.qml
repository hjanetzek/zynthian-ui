import QtQuick
import ".."

// Enterprise: filled keys in the key's colour, all with one corner radius: Theme.keyRadius of the
// keypad's smallest key side (minSide, without the margins), so the smallest keys are pills and
// the others rounded plates with the same corners, side and bottom keys alike
Panel {
    property color fill: Theme.keyBackground
    property bool pressed: false
    property bool translucent: false
    property real minSide: Math.min(width, height)   // the keypad's smallest key side (Keypad.qml)

    anchors.margins: 3
    cornerRadius: Theme.keyRadius > 0 ? Theme.keyRadius * Math.max(0, minSide - 2 * anchors.margins) : -1
    color: {
        const c = pressed ? Qt.lighter(fill, 1.25) : fill
        return translucent ? Qt.rgba(c.r, c.g, c.b, pressed ? 0.85 : 0.7) : c
    }
    borderColor: "transparent"
    borderWidth: 0
}
