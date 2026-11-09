import QtQuick
import ".."

// Enterprise: filled keys in the key's colour, pills (wide keys) or rounded plates
Panel {
    property color fill: Theme.keyBackground
    property bool pressed: false
    property bool translucent: false

    anchors.margins: 3
    button: width > height
    color: {
        const c = pressed ? Qt.lighter(fill, 1.25) : fill
        return translucent ? Qt.rgba(c.r, c.g, c.b, pressed ? 0.85 : 0.7) : c
    }
    borderColor: "transparent"
    borderWidth: 0
}
