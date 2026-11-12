// Mixer: one strip per chain (mixerStrips), the main mixbus on the right (mainStrip). Faders by
// drag (several at once with multitouch), mute and the toggle control (admin) by tap. Meters run while it is shown.
import QtQuick

Item {
    id: root

    property bool shown: true
    // Launcher mode (screen "launcher", the PAD key): a column of sequence pads per strip, one per
    // phrase, instead of the faders; all columns scroll together
    readonly property bool launcherMode: zyn.currentScreen === "launcher"
    readonly property var launcher: zyn.launcherModel
    property real launcherScroll: 0
    property real padHeight: 60
    readonly property real padAreaHeight: padHeight * launcher.phrases

    // Keep the selected phrase in view
    function showPhrase(phrase) {
        const top = phrase * padHeight
        const view = strips.height - 150   // about the pad area of a strip
        if (top < launcherScroll)
            launcherScroll = Math.max(0, top)
        else if (top + padHeight > launcherScroll + view)
            launcherScroll = Math.max(0, top + padHeight - view)
    }
    Connections {
        target: root.launcher
        function onPhraseChanged() { root.showPhrase(root.launcher.phrase) }
    }
    // The meters' levels, read once per update: every read of a Python list property converts it
    readonly property var stripLevels: mixerMeters.levels
    readonly property var mainLevels: mainMeters.levels
    // Admin "Visible Chains": the strips that fit (the others by flicking); 0: all, up to 72 px wide
    // (wider in launcher mode, for the pads)
    readonly property int stripWidth: zyn.visibleChains > 0
        ? Math.max(40, (width - 4) / (zyn.visibleChains + 1) - 2)
        : Math.max(40, Math.min(launcherMode ? 150 : 72, (width - 4) / Math.max(1, mixerStrips.count + 1) - 2))

    Binding { target: mixerMeters; property: "active"; value: root.shown }
    Binding { target: mainMeters; property: "active"; value: root.shown }

    ListView {
        id: strips

        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.right: mainStripView.left
        anchors.rightMargin: 4
        orientation: ListView.Horizontal
        spacing: 2
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        model: mixerStrips

        delegate: Strip {
            lv: root.stripLevels
            stripModel: mixerStrips
            width: root.stripWidth
            height: strips.height
        }
    }

    ListView {
        id: mainStripView

        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: root.stripWidth
        interactive: false
        model: mainStrip

        delegate: Strip {
            lv: root.mainLevels
            stripModel: mainStrip
            isMain: true
            width: root.stripWidth
            height: mainStripView.height
        }
    }

    // Moving the selected phrase (phrase menu: Move / Clone)
    Row {
        anchors.horizontalCenter: strips.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 90
        spacing: 12
        visible: root.launcherMode && root.launcher.movingPhrase
        z: 10
        MoveButton { text: "\u25b2"; onTapped: root.launcher.move_phrase(-1) }
        MoveButton { text: "Done"; width: 140; onTapped: root.launcher.end_moving_phrase() }
        MoveButton { text: "\u25bc"; onTapped: root.launcher.move_phrase(1) }
    }

    // Moving the active chain (chain options: Move chain)
    Row {
        anchors.horizontalCenter: strips.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 90
        spacing: 12
        visible: zyn.movingChain
        z: 10
        MoveButton { text: "\u25c0"; onTapped: zyn.moveChain(-1) }
        MoveButton { text: "Done"; width: 140; onTapped: zyn.endMoveChain() }
        MoveButton { text: "\u25b6"; onTapped: zyn.moveChain(1) }
    }

    Label {
        anchors.centerIn: strips
        visible: mixerStrips.count === 0
        text: zyn.started ? "No chains" : ""
        color: Theme.textOff
        size: 24
        title: true
    }

    component Strip: Panel {
        id: strip

        required property int index
        required property int chainId
        required property string name
        required property int midiChan
        required property real level
        required property real balance
        required property bool mute
        required property bool toggle
        required property string toggleLabel
        required property int meterIndex
        required property bool active
        property var lv: []   // levels of all strips (MixerMeters.levels)
        property var stripModel
        property bool isMain: false

        color: Theme.panel
        cut: Theme.cutLarge
        // The active chain; red while it is being moved
        borderColor: active ? (zyn.movingChain ? Theme.select : Theme.frameActive) : Theme.frame
        borderWidth: active ? 2 : Theme.frameWidth

        Label {
            id: title
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 2
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            text: strip.isMain ? "Main" : (strip.midiChan >= 0 ? strip.midiChan + 1 : "")
            color: Theme.text
            size: 16
            title: true
        }

        Label {
            id: nameText
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: title.bottom
            anchors.margins: 2
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            text: strip.name
            color: Theme.textOff
            size: 12
        }

        // Strip header (number and name): tap opens the chain's controllers, long press its options
        Item {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: nameText.bottom
            TapHandler {
                onTapped: zyn.openChain(strip.chainId)
                onLongPressed: zyn.openChainOptions(strip.chainId)
            }
        }

        // Balance: a bar from the centre
        Item {
            id: balanceBar
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: nameText.bottom
            anchors.margins: 4
            height: 8
            Rectangle { anchors.fill: parent; color: Theme.panelHighlight }
            Rectangle {
                x: parent.width / 2 + Math.min(0, strip.balance) * parent.width / 2
                width: Math.abs(strip.balance) * parent.width / 2
                height: parent.height
                color: Theme.solo
            }
            DragHandler {
                target: null
                yAxis.enabled: Theme.uiSideways
                property real startBalance
                onActiveChanged: if (active) startBalance = strip.balance
                onTranslationChanged: strip.stripModel.setBalance(strip.index,
                                          startBalance + 2 * Theme.localDrag(parent, centroid).x / balanceBar.width)
            }
            TapHandler { onDoubleTapped: strip.stripModel.setBalance(strip.index, 0) }
        }

        // Launcher mode: the level as a horizontal bar (drag sideways)
        Item {
            id: levelBar
            visible: root.launcherMode
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: balanceBar.bottom
            anchors.margins: 4
            height: visible ? 10 : 0
            Rectangle { anchors.fill: parent; color: Theme.panelHighlight }
            Rectangle { width: parent.width * strip.level; height: parent.height; color: Theme.keyText }
            DragHandler {
                target: null
                yAxis.enabled: Theme.uiSideways
                property real startLevel
                onActiveChanged: if (active) startLevel = strip.level
                onTranslationChanged: strip.stripModel.setLevel(strip.index,
                                          startLevel + Theme.localDrag(parent, centroid).x / levelBar.width)
            }
        }

        Item {
            id: pads

            visible: root.launcherMode
            anchors.top: levelBar.bottom
            anchors.topMargin: 4
            // Room for two buttons in every strip, so the pad rows line up (MIDI strips have one)
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 2 * 36 + buttons.spacing + 8
            anchors.left: parent.left
            anchors.right: parent.right
            clip: true
            onHeightChanged: if (strip.isMain && height > 0) root.padHeight = height / root.launcher.visiblePads

            Column {
                y: -root.launcherScroll
                width: parent.width
                Repeater {
                    // Always instantiated: creating the pads (strips x phrases) on each switch
                    // to the launcher is what made it slow; hidden pads only note changes
                    model: root.launcher.phrases
                    LauncherPad {
                        launcher: root.launcher
                        shown: root.launcherMode
                        required property int index
                        chainId: strip.chainId
                        phrase: index
                        isMain: strip.isMain
                        selected: strip.active && index === root.launcher.phrase
                        width: pads.width
                        height: root.padHeight
                    }
                }
            }
            // Vertical drag scrolls all columns; taps go to the pads
            DragHandler {
                target: null
                xAxis.enabled: Theme.uiSideways
                property real startScroll
                onActiveChanged: if (active) startScroll = root.launcherScroll
                onTranslationChanged: root.launcherScroll = Math.max(0, Math.min(
                    root.padAreaHeight - pads.height, startScroll - Theme.localDrag(parent, centroid).y))
            }
            WheelHandler {
                onWheel: (event) => root.launcherScroll = Math.max(0, Math.min(
                    root.padAreaHeight - pads.height, root.launcherScroll - event.angleDelta.y / 2))
            }
        }

        Item {
            id: fader

            visible: !root.launcherMode
            anchors.top: balanceBar.bottom
            anchors.topMargin: 6
            anchors.bottom: buttons.top
            anchors.bottomMargin: 4
            anchors.left: parent.left
            anchors.right: parent.right

            Rectangle {
                anchors.bottom: parent.bottom
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width - 8
                height: parent.height * strip.level
                color: Theme.panelHighlight
            }

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                spacing: 2
                Meter {
                    height: parent.height
                    value: strip.lv[4 * strip.meterIndex] || 0
                    hold: strip.lv[4 * strip.meterIndex + 2] || 0
                }
                Meter {
                    height: parent.height
                    value: strip.lv[4 * strip.meterIndex + 1] || 0
                    hold: strip.lv[4 * strip.meterIndex + 3] || 0
                }
            }

            Rectangle {   // fader handle
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width - 4
                height: 6
                y: parent.height * (1 - strip.level) - height / 2
                color: Theme.text
            }

            DragHandler {
                target: null
                xAxis.enabled: Theme.uiSideways
                property real startLevel
                onActiveChanged: if (active) startLevel = strip.level
                onTranslationChanged: strip.stripModel.setLevel(strip.index,
                                          startLevel - Theme.localDrag(parent, centroid).y / fader.height)
            }
        }

        Column {
            id: buttons

            anchors.bottom: parent.bottom
            anchors.bottomMargin: 4
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 4
            StripButton {
                text: "M"; on: strip.mute; onColor: Theme.mute
                onTapped: strip.stripModel.toggleMute(strip.index)
            }
            StripButton {
                // Admin "Mixer Toggle Control" (record by default); the main strip has no solo
                visible: strip.toggleLabel !== "" && !(strip.isMain && strip.toggleLabel === "S")
                text: strip.toggleLabel; on: strip.toggle; onColor: Theme.solo
                onTapped: strip.stripModel.toggleControl(strip.index)
            }
        }
    }

    component StripButton: Panel {
        id: button
        property alias text: t.text
        property bool on
        property color onColor
        signal tapped
        width: root.stripWidth - 8
        height: 36
        color: on ? onColor : Theme.keyBackground
        cut: Theme.cut / 2
        button: true
        Label { id: t; anchors.centerIn: parent; color: Theme.text; size: 16 }
        TapHandler { gesturePolicy: TapHandler.ReleaseWithinBounds; onTapped: button.tapped() }
    }

    component MoveButton: Panel {
        id: moveButton
        property alias text: moveLabel.text
        signal tapped
        width: 90
        height: 60
        radius: 4
        button: true
        color: moveTap.pressed ? Theme.keyText : Theme.overlay
        borderColor: Theme.select
        borderWidth: 2
        Label {
            id: moveLabel
            anchors.centerIn: parent
            color: Theme.text
            size: 24
            title: true
        }
        TapHandler { id: moveTap; gesturePolicy: TapHandler.ReleaseWithinBounds; onTapped: moveButton.tapped() }
    }
}
