// M0 spike: window with top bar, screen stack and the V5 touch keypad, in logical pixels for
// 960x600 (the Duet's 1920x1200 at output scale 2).
import QtQuick
import QtQuick.Layouts

Window {
    id: root

    property int currentScreen: 0
    readonly property var masterLevels: meters.levels

    width: 960
    height: 600
    visible: true
    visibility: startFullScreen ? Window.FullScreen : Window.Windowed
    color: Theme.background
    title: "zynthian Qt spike"

    Keypad {
        id: keypad

        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 192
        onPressed: name => {
            if (name === "MIX")
                root.currentScreen = 0
            else if (name === "PRESET")
                root.currentScreen = 1
        }
    }

    Rectangle {
        id: topBar

        anchors.left: keypad.right
        anchors.right: parent.right
        anchors.top: parent.top
        height: 50
        color: Theme.background

        Text {
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: 8
            text: root.currentScreen === 0 ? "Mixer" : "Main/Presets"
            color: Theme.text
            font.pixelSize: 28
            font.family: Theme.fontFamily
        }

        // Master meters in the top bar, as in zynthian's status area
        Row {
            anchors.right: parent.right
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2
            Repeater {
                model: 2
                Rectangle {
                    required property int index
                    width: 160
                    height: 8
                    color: Theme.panel
                    Rectangle {
                        height: parent.height
                        width: parent.width * (root.masterLevels[parent.index] || 0)
                        color: Theme.meterLow
                    }
                }
            }
        }
    }

    StackLayout {
        anchors.left: keypad.right
        anchors.right: parent.right
        anchors.top: topBar.bottom
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 100   // bottom keypad row
        currentIndex: root.currentScreen

        MixerScreen {}
        ListScreen {}
    }
}
