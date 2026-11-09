import QtQuick

// The label of a keypad key (classic: its text in the key colours; enterprise: dark text at the
// bottom right of filled keys). Themes replace it (+<theme>/KeyFace.qml).
Item {
    id: face
    property int key
    property string label

    Label {
        anchors.centerIn: Theme.keyFilled ? undefined : parent
        anchors.right: Theme.keyFilled ? parent.right : undefined
        anchors.bottom: Theme.keyFilled ? parent.bottom : undefined
        anchors.rightMargin: Theme.keyFilled ? (parent.width > parent.height ? parent.height / 2 : 12) : 0
        anchors.bottomMargin: Theme.keyFilled ? 8 : 0
        horizontalAlignment: Theme.keyFilled ? Text.AlignRight : Text.AlignHCenter
        text: face.label
        color: Theme.keyFilled ? Theme.keyFilledText
                               : (face.key === 12 ? Theme.keyBack : (face.key === 14 || face.key === 2 ? Theme.keyYes : Theme.keyText))
        size: 20
        title: true
        lineHeight: Theme.keyLineHeight
    }
}
