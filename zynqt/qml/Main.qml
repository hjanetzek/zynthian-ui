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
                                        midi_key_range: "Note Range & Transpose",
                                        chain_manager: "Chain Manager", launcher: "Launcher",
                                        pattern_editor: "Pattern Editor", control_xy: "X-Y Touchpad" })

    // Titles of the QML screens; the chain manager's as Tk's: "Chain: " and the selected node's chain
    function screenTitle(screen) {
        if (screen === "chain_manager") {
            const g = zyn.chainManager.graph, sel = zyn.chainManager.selection
            if (sel.length && g[sel[0]])
                return "Chain: " + g[sel[0]].rows[0][0].title
        }
        return root.qmlTitles[screen] || screen
    }

    // Rotation of the whole UI (zynthian_qt_main.py: ZYNTHIAN_UI_ROTATION), see the item ui below
    readonly property int uiRotation: typeof zynUiRotation !== "undefined" ? zynUiRotation : 0

    width: 960
    height: 600
    visible: true
    visibility: startFullScreen ? Window.FullScreen : Window.Windowed
    color: Theme.background
    title: "zynthian"

    // Touch keypad: an overlay brought up from the top edge (tap or swipe down on the title),
    // hidden again 4 s after the last key or by another tap on the title; or docked (the screens
    // beside and above it). Tapping the status area (or Admin > Docked Touch Keypad) switches.
    // The theme's sizes that follow the window (tk: as zynthian_gui_config)
    Binding { target: Theme; property: "screenWidth"; value: ui.width }
    Binding { target: Theme; property: "screenHeight"; value: ui.height }
    Binding { target: Theme; property: "keypadShown"; value: root.keypadDocked }

    // Themes without an on-screen keypad (keypadEnabled false, v4: the kit's knobs and switches)
    readonly property bool keypadDocked: zyn.keypadDocked && Theme.keypadEnabled
    property bool keypadOverlay: false
    // The keypad on the right (ZYNTHIAN_UI_TOUCH_NAVIGATION v5_keypad_right)
    readonly property bool keypadRight: typeof zynConfig !== "undefined" && zynConfig.keypadRight === true
    readonly property real screensLeft: keypadDocked && !keypadRight ? keypad.width : 0
    readonly property real screensRight: keypadDocked && keypadRight ? keypad.width : 0
    onKeypadDockedChanged: keypadOverlay = false

    Timer {
        id: keypadHide
        interval: 4000
        onTriggered: root.keypadOverlay = false
    }
    function showKeypadOverlay(show) {
        keypadOverlay = show && Theme.keypadEnabled
        if (show)
            keypadHide.restart()
    }

    readonly property real elbowArm: 180
    readonly property bool elbowShown: Theme.elbow && zyn.topBarShown

    Binding { target: Theme; property: "uiSideways"; value: ui.sideways }

    // Everything visible, rotated by uiRotation (ZYNTHIAN_UI_ROTATION: 0, 90, 180, 270) for
    // displays without output rotation (Qt's eglfs on KMS: no compositor to rotate, and Qt Quick
    // ignores QT_QPA_EGLFS_ROTATION); the layout follows this item's size, not the window's.
    // Touch follows the item transform (raw panel coordinates: evdevtouch, no calibration matrix).
    Item {
        id: ui
        readonly property bool sideways: root.uiRotation === 90 || root.uiRotation === 270
        anchors.centerIn: parent
        width: sideways ? root.height : root.width
        height: sideways ? root.width : root.height
        rotation: root.uiRotation

        // Overlay keypad: the screens under it blurred (KeypadBlur, only while shown), translucent keys
        Loader {
            x: screens.x
            y: screens.y
            width: screens.width
            height: screens.height
            z: 19
            active: root.keypadOverlay
            source: "KeypadBlur.qml"
            onLoaded: {
                item.source = screens
                item.sideWidth = Qt.binding(() => keypad.width)
                item.bottomHeight = Qt.binding(() => keypad.keyHeight)
                item.sideRight = Qt.binding(() => root.keypadRight)
            }
        }

        Keypad {
            id: keypad

            x: root.keypadRight ? ui.width - width : 0
            rightHanded: root.keypadRight
            // The overlay leaves the top bar free: its title hides the keypad again
            anchors.top: root.keypadDocked ? parent.top : topBar.bottom
            anchors.bottom: parent.bottom
            width: Theme.keypadWidth
            keyHeight: Theme.keypadKeyHeight
            z: 20
            visible: root.keypadDocked || root.keypadOverlay
            translucent: !root.keypadDocked
            onKeyPressed: if (root.keypadOverlay) keypadHide.restart()
        }

        // Enterprise: the elbow frames the screens, its arm continues as the top bar's segments
        // (not with the top bar hidden)

        TopBar {
            id: topBar

            anchors.left: parent.left
            anchors.leftMargin: root.screensLeft
            overlayHint: !root.keypadDocked
            onTitleTapped: if (!root.keypadDocked) root.showKeypadOverlay(!root.keypadOverlay)
            onTitleSwipedDown: if (!root.keypadDocked) root.showKeypadOverlay(true)
            onStatusTapped: if (Theme.keypadEnabled) zyn.toggleKeypadDocked()
            anchors.right: parent.right
            anchors.rightMargin: root.screensRight
            anchors.top: parent.top
            // HIDE_TOPBAR: the screens get its height. Enterprise: taller, the segments below the status
            height: zyn.topBarShown ? (Theme.elbow ? Theme.topBarHeight + Theme.elbowBar - 4 : Theme.topBarHeight) : 0
            visible: zyn.topBarShown
            barStart: root.elbowShown ? root.elbowArm + 6 : 0
            title: zyn.currentList ? zyn.currentList.title : root.screenTitle(zyn.currentScreen)
        }

        Elbow {
            visible: root.elbowShown
            x: root.screensLeft + (root.keypadDocked && Theme.keyFilled ? 3 : 0)
            y: topBar.height - thickness
            width: parent.width - x - root.screensRight
            height: screens.y + screens.height - y
            arm: root.elbowArm
        }

        StackLayout {
            id: screens

            anchors.left: parent.left
            anchors.leftMargin: root.screensLeft + (root.elbowShown ? Theme.elbowBar * 1.6 + 8 : 0)
            anchors.topMargin: root.elbowShown ? 6 : 0
            anchors.right: parent.right
            anchors.rightMargin: root.screensRight
            anchors.top: topBar.bottom
            anchors.bottom: parent.bottom
            anchors.bottomMargin: root.keypadDocked ? keypad.keyHeight : 0
            currentIndex: zyn.currentList ? 2
                          : (zyn.currentScreen === "mixer" || zyn.currentScreen === "launcher") ? 0
                          : zyn.currentScreen === "chain_manager" ? 3
                          : zyn.currentScreen === "pattern_editor" ? 4
                          : zyn.currentScreen === "control_xy" ? 5 : 1

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
            ChainManagerScreen {}
            PatternEditorScreen {}
            ControlXYScreen {}
        }

        // Info message, as zynthian_gui.show_info
        Panel {
            anchors.horizontalCenter: screens.horizontalCenter
            anchors.bottom: screens.bottom
            anchors.bottomMargin: 16
            width: Math.min(screens.width - 40, infoText.implicitWidth + 40)
            height: infoText.implicitHeight + 20
            radius: 6
            visible: zyn.info !== ""
            color: Theme.overlay
            borderColor: Theme.keyText
            borderWidth: Math.max(1, Theme.frameWidth)
            cut: Theme.cutLarge
            Label {
                id: infoText
                anchors.centerIn: parent
                width: Math.min(implicitWidth, screens.width - 80)
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                text: zyn.info
                color: Theme.text
                body: true
                size: 20
            }
        }

        // Confirmation (zynthian_gui_confirm): SEL/YES confirms, BACK/NO cancels
        Rectangle {
            anchors.fill: screens
            visible: zyn.confirmText !== ""
            color: Theme.dim
            MouseArea { anchors.fill: parent; onWheel: (wheel) => wheel.accepted = true }   // modal: keeps touches from the screen below

            Column {
                anchors.centerIn: parent
                spacing: 30
                Label {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: screens.width - 80
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    text: zyn.confirmText
                    color: Theme.text
                    body: true
                    size: 28
                    title: true
                }
                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 40
                    DialogButton { text: "NO"; color: Theme.dialogNo; onTapped: zyn.confirmNo() }
                    DialogButton { text: "YES"; color: Theme.dialogYes; onTapped: zyn.confirmYes() }
                }
            }
        }

        Keyboard {
            anchors.fill: screens
        }

        // Help (zynthian_gui_help): the screen's zynthian-help page; links followed, arrows scroll,
        // BACK or the close button closes it
        Rectangle {
            id: help
            anchors.fill: screens
            visible: zyn.helpShown
            color: Theme.background
            MouseArea { anchors.fill: parent; onWheel: (wheel) => wheel.accepted = false }

            Flickable {
                id: helpFlick
                anchors.fill: parent
                anchors.margins: 16
                anchors.rightMargin: 80
                contentHeight: helpText.implicitHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                Label {
                    id: helpText
                    width: helpFlick.width
                    textFormat: Text.RichText
                    wrapMode: Text.WordWrap
                    baseUrl: zyn.helpBaseUrl
                    text: zyn.helpHtml
                    color: Theme.text
                    linkColor: Theme.link
                    body: true
                    size: 20
                    onLinkActivated: (link) => zyn.helpLink(link)
                    onTextChanged: helpFlick.contentY = 0
                }
            }
            Connections {
                target: zyn
                function onHelpScroll(steps) {
                    helpFlick.contentY = Math.max(0, Math.min(helpFlick.contentHeight - helpFlick.height,
                                                              helpFlick.contentY + steps * helpFlick.height * 0.8))
                }
            }
            DialogButton {
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.margins: 8
                width: 64
                height: 64
                text: "✕"
                color: Theme.keyBackground
                textColor: Theme.text
                onTapped: zyn.helpClose()
            }
        }

        // Value editor (zynthian param editor): steps, OK applies; arrows step, SEL OK, BACK cancels
        Rectangle {
            anchors.fill: screens
            visible: zyn.valueEditorShown
            color: Theme.dim
            MouseArea { anchors.fill: parent; onWheel: (wheel) => zyn.valueEditorStep(wheel.angleDelta.y > 0 ? 1 : -1) }

            Column {
                anchors.centerIn: parent
                spacing: 24
                Label {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: zyn.valueEditorTitle
                    color: Theme.textOff
                    size: 24
                    title: true
                }
                Label {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: zyn.valueEditorText
                    color: Theme.text
                    body: true
                    size: 56
                    title: true
                }
                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 16
                    DialogButton { text: "−10"; width: 110; color: Theme.keyBackground; textColor: Theme.text; onTapped: zyn.valueEditorStep(-10) }
                    DialogButton { text: "−1"; width: 110; color: Theme.keyBackground; textColor: Theme.text; onTapped: zyn.valueEditorStep(-1) }
                    DialogButton { text: "+1"; width: 110; color: Theme.keyBackground; textColor: Theme.text; onTapped: zyn.valueEditorStep(1) }
                    DialogButton { text: "+10"; width: 110; color: Theme.keyBackground; textColor: Theme.text; onTapped: zyn.valueEditorStep(10) }
                }
                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 40
                    DialogButton { text: "Cancel"; color: Theme.dialogNo; onTapped: zyn.valueEditorCancel() }
                    DialogButton { text: "OK"; color: Theme.dialogYes; onTapped: zyn.valueEditorAccept() }
                }
            }
        }

        // Busy: loading snapshots, starting engines
        Rectangle {
            anchors.fill: screens
            visible: zyn.busy
            color: Theme.dimBusy
            Column {
                anchors.centerIn: parent
                width: parent.width - 80
                spacing: 16
                Label {
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    text: zyn.busyMessage || "Busy..."
                    color: Theme.text
                    body: true
                    size: 28
                    title: true
                }
                // Tasks with counted steps (snapshot loading): a progress bar and the current step
                Rectangle {
                    visible: zyn.busyProgress >= 0
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: Math.min(parent.width, 600)
                    height: 14
                    radius: 7
                    color: Theme.panel
                    Rectangle {
                        width: parent.width * Math.max(0, zyn.busyProgress)
                        height: parent.height
                        radius: 7
                        color: Theme.keyText
                        Behavior on width { NumberAnimation { duration: 150 } }
                    }
                }
                Label {
                    visible: zyn.busyProgress >= 0
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                    text: zyn.busyDetails
                    color: Theme.textOff
                    body: true
                    size: 16
                }
            }
            MouseArea { anchors.fill: parent; onWheel: (wheel) => wheel.accepted = true }   // swallow taps while busy
        }

        // Power save (POWER_SAVE, or the configured time without input): the whole window black;
        // the next touch or key wakes it (ZynUI.user_activity drops that touch)
        Rectangle {
            anchors.fill: parent
            z: 100
            visible: !!zyn.status.powerSave
            color: "black"
            MouseArea { anchors.fill: parent; onWheel: (wheel) => wheel.accepted = true }
        }
    }

    component PlaceholderScreen: Rectangle {
        property alias text: label.text
        color: Theme.panel
        Label {
            id: label
            anchors.centerIn: parent
            color: Theme.textOff
            size: 24
            title: true
        }
    }

    component DialogButton: Panel {
        id: button
        property alias text: label.text
        property color textColor: Theme.dialogText   // on dialogNo / dialogYes
        signal tapped
        width: 160
        height: 70
        radius: 4
        button: true
        borderColor: Theme.dialogFrame
        cut: Theme.cutLarge
        Label {
            id: label
            anchors.centerIn: parent
            color: button.textColor
            size: 26
            title: true
        }
        TapHandler { gesturePolicy: TapHandler.ReleaseWithinBounds; onTapped: button.tapped() }
    }
}
