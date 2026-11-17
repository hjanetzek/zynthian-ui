import QtQuick
import ".."

// The label of a keypad key (classic: its text in the key colours; enterprise: dark text at the
// bottom right of filled keys). Themes replace it (+<theme>/KeyFace.qml).
Item {
    id: face
    property int key
    property string label
    property real radius: 0      // the plate's corner radius with Theme.keyRadius (Keypad.qml)

    Label {
        anchors.centerIn: Theme.keyFilled ? undefined : parent
        anchors.right: Theme.keyFilled ? parent.right : undefined
        anchors.bottom: Theme.keyFilled ? parent.bottom : undefined
        // Filled keys: clear of the rounded corner (keyRadius: inside its arc; else pills)
        anchors.rightMargin: !Theme.keyFilled ? 0 : (face.radius > 0 ? Math.max(8, 0.35 * face.radius)
                                                     : (parent.width > parent.height ? parent.height / 2 : 12))
        anchors.bottomMargin: !Theme.keyFilled ? 0 : (face.radius > 0 ? Math.max(8, 0.3 * face.radius) : 8)
        horizontalAlignment: Theme.keyFilled ? Text.AlignRight : Text.AlignHCenter
        text: face.label
        color: Theme.keyFilled ? Theme.keyFilledText
                               : (face.key === 12 ? Theme.keyBack : (face.key === 14 || face.key === 2 ? Theme.keyYes : Theme.keyText))
        size: 20
        title: true
        lineHeight: Theme.keyLineHeight
    }
}
