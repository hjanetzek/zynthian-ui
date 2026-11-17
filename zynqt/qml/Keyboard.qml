// On-screen keyboard for names (zynthian_gui_keyboard): ZynUI.show_keyboard() shows it, OK
// calls keyboardAccept(text). A physical keyboard types into the field too. Sizes times
// Theme.dialogScale.
import QtQuick

Rectangle {
    id: root

    property bool shift: false
    readonly property var rows: ["1234567890", "qwertyuiop", "asdfghjkl'", "zxcvbnm-_."]

    color: Theme.keyboardBackground
    visible: zyn.keyboardShown

    onVisibleChanged: if (visible) { field.text = zyn.keyboardText; field.selectAll(); field.forceActiveFocus() }

    MouseArea { anchors.fill: parent; onWheel: (wheel) => wheel.accepted = true }   // modal: keeps touches from the screen below

    Connections {
        target: zyn
        function onKeyboardSubmit() { zyn.keyboardAccept(field.text) }
    }

    Column {
        anchors.fill: parent
        anchors.margins: Math.round(8 * Theme.dialogScale)
        spacing: Math.round(6 * Theme.dialogScale)

        Label {
            text: zyn.keyboardTitle
            color: Theme.textOff
            size: Math.round(18 * Theme.dialogScale)
            title: true
        }

        Panel {
            width: parent.width
            height: Math.round(48 * Theme.dialogScale)
            color: Theme.panel
            borderColor: Theme.dialogFrame
            TextInput {
                id: field
                anchors.fill: parent
                anchors.margins: Math.round(8 * Theme.dialogScale)
                verticalAlignment: TextInput.AlignVCenter
                color: Theme.text
                selectionColor: Theme.keyText
                font.pixelSize: Math.round(26 * Theme.dialogScale)
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
                spacing: Math.round(4 * Theme.dialogScale)
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
            spacing: Math.round(4 * Theme.dialogScale)
            Key { label: "⇧"; width: Math.round(100 * Theme.dialogScale); highlighted: root.shift; onTapped: root.shift = !root.shift }
            Key { label: "space"; width: Math.round(300 * Theme.dialogScale); onTapped: field.insert(field.cursorPosition, " ") }
            Key {
                label: "⌫"; width: Math.round(100 * Theme.dialogScale)
                onTapped: if (field.selectedText.length > 0) field.remove(field.selectionStart, field.selectionEnd)
                          else if (field.cursorPosition > 0) field.remove(field.cursorPosition - 1, field.cursorPosition)
            }
            Key { label: "Cancel"; width: Math.round(120 * Theme.dialogScale); onTapped: zyn.keyboardCancel() }
            Key { label: "OK"; width: Math.round(120 * Theme.dialogScale); highlighted: true; onTapped: zyn.keyboardAccept(field.text) }
        }
    }

    component Key: Panel {
        id: key
        property string label
        property bool highlighted: false
        signal tapped
        width: Math.round(70 * Theme.dialogScale)
        height: Math.round(52 * Theme.dialogScale)
        radius: 3
        button: true
        color: tap.pressed ? Theme.keyText : (highlighted ? Theme.keyboardHighlight
                                                           : Theme.keyBackground)
        Label {
            anchors.centerIn: parent
            text: key.label
            color: key.highlighted && !tap.pressed ? Theme.keyboardHighlightText : Theme.text
            size: Math.round(22 * Theme.dialogScale)
            body: true   // letter keys show their case
            title: true
        }
        TapHandler { id: tap; gesturePolicy: TapHandler.ReleaseWithinBounds; onTapped: key.tapped() }
    }
}
