// zynthian Qt Quick UI: window with the touch keypad, the top bar and the screens, in logical
// pixels for 960x600 (the Duet's 1920x1200 at output scale 2).
import QtQuick
import QtQuick.Layouts

Window {
    id: root

    readonly property var screenNames: ["mixer", "main_menu", "chain_control"]
    readonly property var screenTitles: ({ mixer: "Mixer", main_menu: "Main", chain_control: "Chain" })

    width: 960
    height: 600
    visible: true
    visibility: startFullScreen ? Window.FullScreen : Window.Windowed
    color: Theme.background
    title: "zynthian"

    Keypad {
        id: keypad

        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 192
    }

    TopBar {
        id: topBar

        anchors.left: keypad.right
        anchors.right: parent.right
        anchors.top: parent.top
        height: 50
        title: root.screenTitles[zyn.currentScreen] || zyn.currentScreen
    }

    StackLayout {
        id: screens

        anchors.left: keypad.right
        anchors.right: parent.right
        anchors.top: topBar.bottom
        anchors.bottom: parent.bottom
        anchors.bottomMargin: keypad.keyHeight
        currentIndex: Math.max(0, root.screenNames.indexOf(zyn.currentScreen))

        MixerScreen { shown: screens.currentIndex === 0 }
        PlaceholderScreen { text: "Main menu: not ported yet" }
        PlaceholderScreen { text: "Chain control: not ported yet" }
    }

    // Busy: loading snapshots, starting engines
    Rectangle {
        anchors.fill: screens
        visible: zyn.busy
        color: "#c0000000"
        Text {
            anchors.centerIn: parent
            width: parent.width - 40
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            text: zyn.busyMessage || "Busy..."
            color: Theme.text
            font.pixelSize: 28
            font.family: Theme.fontFamily
        }
        TapHandler {}   // swallow taps while busy
    }

    component PlaceholderScreen: Rectangle {
        property alias text: label.text
        color: Theme.panel
        Text {
            id: label
            anchors.centerIn: parent
            color: Theme.textOff
            font.pixelSize: 24
            font.family: Theme.fontFamily
        }
    }
}
