// On-screen keyboard for names (zynthian_gui_keyboard): ZynUI.show_keyboard() shows it, OK
// calls keyboardAccept(text). A physical keyboard types into the field too.
import QtQuick

Rectangle {
    id: root

    property bool shift: false
    readonly property var rows: ["1234567890", "qwertyuiop", "asdfghjkl'", "zxcvbnm-_."]

    color: "#f0101418"
    visible: zyn.keyboardShown

    onVisibleChanged: if (visible) { field.text = zyn.keyboardText; field.selectAll(); field.forceActiveFocus() }

    TapHandler {}   // modal

    Connections {
        target: zyn
        function onKeyboardSubmit() { zyn.keyboardAccept(field.text) }
    }

    Column {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 6

        Text {
            text: zyn.keyboardTitle
            color: Theme.textOff
            font.pixelSize: 18
            font.family: Theme.fontFamily
        }

        Rectangle {
            width: parent.width
            height: 48
            color: Theme.panel
            TextInput {
                id: field
                anchors.fill: parent
                anchors.margins: 8
                verticalAlignment: TextInput.AlignVCenter
                color: Theme.text
                selectionColor: Theme.keyText
                font.pixelSize: 26
                font.family: Theme.fontFamily
                onAccepted: zyn.keyboardAccept(text)
                Keys.onEscapePressed: zyn.keyboardCancel()
            }
        }

        Repeater {
            model: root.rows
            Row {
                id: keyRow
                required property string modelData
                spacing: 4
                Repeater {
                    model: keyRow.modelData.split("")
                    Key {
                        required property string modelData
                        label: root.shift ? modelData.toUpperCase() : modelData
                        onTapped: { field.insert(field.cursorPosition, label); root.shift = false }
                    }
                }
            }
        }

        Row {
            spacing: 4
            Key { label: "⇧"; width: 100; highlighted: root.shift; onTapped: root.shift = !root.shift }
            Key { label: "space"; width: 300; onTapped: field.insert(field.cursorPosition, " ") }
            Key {
                label: "⌫"; width: 100
                onTapped: if (field.selectedText.length > 0) field.remove(field.selectionStart, field.selectionEnd)
                          else if (field.cursorPosition > 0) field.remove(field.cursorPosition - 1, field.cursorPosition)
            }
            Key { label: "Cancel"; width: 120; onTapped: zyn.keyboardCancel() }
            Key { label: "OK"; width: 120; highlighted: true; onTapped: zyn.keyboardAccept(field.text) }
        }
    }

    component Key: Rectangle {
        id: key
        property string label
        property bool highlighted: false
        signal tapped
        width: 70
        height: 52
        radius: 3
        color: tap.pressed ? Theme.keyText : (highlighted ? "#205080" : Theme.keyBackground)
        Text {
            anchors.centerIn: parent
            text: key.label
            color: Theme.text
            font.pixelSize: 22
            font.family: Theme.fontFamily
        }
        TapHandler { id: tap; onTapped: key.tapped() }
    }
}
