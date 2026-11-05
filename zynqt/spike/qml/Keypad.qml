// V5 touch keypad: two columns of five keys on the left, a row of ten at the bottom (drawn by
// the root window across the full width, see bottomRow)
import QtQuick

Item {
    id: root

    signal pressed(string name)

    readonly property var sideKeys: [["OPT", "ADMIN"], ["MIX", "LEVEL"], ["CTRL", "PRESET"],
                                     ["PAD", "STEP"], ["", "METRO"], ["ZS3", "SHOT"],
                                     ["BACK", "NO"], ["SEL", "YES"], ["ALT", "HELP"], ["^", ""]]
    readonly property var bottomKeys: ["<", "v", ">", "REC", "STOP", "PLAY", "F1", "F2", "F3", "F4"]

    Grid {
        id: side

        columns: 2
        width: parent.width
        height: parent.height - 100
        Repeater {
            model: root.sideKeys
            Key {
                required property var modelData
                width: side.width / 2
                height: side.height / 5
                label: modelData[0] + (modelData[1] ? "\n" + modelData[1] : "")
                onTapped: root.pressed(modelData[1] === "PRESET" ? "PRESET" : modelData[0])
            }
        }
    }

    Row {
        id: bottomRow

        y: parent.height - 100
        width: Window.window ? Window.window.width : 960
        height: 100
        Repeater {
            model: root.bottomKeys
            Key {
                required property string modelData
                width: bottomRow.width / 10
                height: bottomRow.height
                label: modelData
                onTapped: root.pressed(modelData)
            }
        }
    }

    component Key: Rectangle {
        id: key

        property string label
        signal tapped

        color: tap.pressed ? Qt.lighter(Theme.keyBackground, 1.8) : Theme.keyBackground
        border.color: Theme.background
        border.width: 1

        Text {
            anchors.centerIn: parent
            horizontalAlignment: Text.AlignHCenter
            text: key.label
            color: Theme.keyText
            font.pixelSize: 20
            font.family: Theme.fontFamily
        }

        TapHandler {
            id: tap
            onTapped: key.tapped()
        }
    }
}
