// zynthian Qt Quick UI: window with the touch keypad, the top bar and the screens, in logical
// pixels for 960x600 (the Duet's 1920x1200 at output scale 2).
import QtQuick
import QtQuick.Layouts

Window {
    id: root

    // Screens with their own QML; tempo and alsa_mixer are chain control with a special processor
    readonly property var qmlScreens: ["mixer", "chain_control", "tempo", "alsa_mixer", "audio_player",
                                       "midi_key_range"]
    readonly property var qmlTitles: ({ mixer: "Mixer", chain_control: "Chain", tempo: "Tempo",
                                        alsa_mixer: "Audio Levels", audio_player: "Audio Player",
                                        midi_key_range: "Note Range & Transpose" })

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
        title: zyn.currentList ? zyn.currentList.title : (root.qmlTitles[zyn.currentScreen] || zyn.currentScreen)
    }

    StackLayout {
        id: screens

        anchors.left: keypad.right
        anchors.right: parent.right
        anchors.top: topBar.bottom
        anchors.bottom: parent.bottom
        anchors.bottomMargin: keypad.keyHeight
        currentIndex: zyn.currentList ? 2 : (zyn.currentScreen === "mixer" ? 0 : 1)

        MixerScreen { shown: screens.currentIndex === 0 }
        ChainControlScreen {}
        // One view per selector screen, kept: switching only changes which one is visible
        Item {
            Repeater {
                model: zyn.listScreenObjects
                SelectorScreen {
                    required property var modelData
                    anchors.fill: parent
                    screen: modelData
                    visible: modelData === zyn.currentList
                }
            }
        }
    }

    // Info message, as zynthian_gui.show_info
    Rectangle {
        anchors.horizontalCenter: screens.horizontalCenter
        anchors.bottom: screens.bottom
        anchors.bottomMargin: 16
        width: Math.min(screens.width - 40, infoText.implicitWidth + 40)
        height: infoText.implicitHeight + 20
        radius: 6
        visible: zyn.info !== ""
        color: "#e0202830"
        border.color: Theme.keyText
        Text {
            id: infoText
            anchors.centerIn: parent
            width: Math.min(implicitWidth, screens.width - 80)
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            text: zyn.info
            color: Theme.text
            font.pixelSize: 20
        }
    }

    // Confirmation (zynthian_gui_confirm): SEL/YES confirms, BACK/NO cancels
    Rectangle {
        anchors.fill: screens
        visible: zyn.confirmText !== ""
        color: "#d0000000"
        TapHandler {}   // modal

        Column {
            anchors.centerIn: parent
            spacing: 30
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                width: screens.width - 80
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                text: zyn.confirmText
                color: Theme.text
                font.pixelSize: 28
                font.family: Theme.fontFamily
            }
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 40
                DialogButton { text: "NO"; color: "#802020"; onTapped: zyn.confirmNo() }
                DialogButton { text: "YES"; color: "#208020"; onTapped: zyn.confirmYes() }
            }
        }
    }

    Keyboard {
        anchors.fill: screens
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

    component DialogButton: Rectangle {
        id: button
        property alias text: label.text
        signal tapped
        width: 160
        height: 70
        radius: 4
        Text {
            id: label
            anchors.centerIn: parent
            color: Theme.text
            font.pixelSize: 26
            font.family: Theme.fontFamily
        }
        TapHandler { onTapped: button.tapped() }
    }
}
