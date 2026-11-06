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

    Text {
        anchors.centerIn: strips
        visible: mixerStrips.count === 0
        text: zyn.started ? "No chains" : ""
        color: Theme.textOff
        font.pixelSize: 24
        font.family: Theme.fontFamily
    }

    component Strip: Rectangle {
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
        // The active chain; red while it is being moved
        border.color: active ? (zyn.movingChain ? Theme.select : Theme.text) : "transparent"
        border.width: active ? 2 : 0

        Text {
            id: title
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 2
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            text: strip.isMain ? "Main" : (strip.midiChan >= 0 ? strip.midiChan + 1 : "")
            color: Theme.text
            font.pixelSize: 16
            font.family: Theme.fontFamily
        }

        Text {
            id: nameText
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: title.bottom
            anchors.margins: 2
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            text: strip.name
            color: Theme.textOff
            font.pixelSize: 12
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
                yAxis.enabled: false
                property real startBalance
                onActiveChanged: if (active) startBalance = strip.balance
                onTranslationChanged: strip.stripModel.setBalance(strip.index,
                                          startBalance + 2 * translation.x / balanceBar.width)
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
                yAxis.enabled: false
                property real startLevel
                onActiveChanged: if (active) startLevel = strip.level
                onTranslationChanged: strip.stripModel.setLevel(strip.index,
                                          startLevel + translation.x / levelBar.width)
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
                    Pad {
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
                xAxis.enabled: false
                property real startScroll
                onActiveChanged: if (active) startScroll = root.launcherScroll
                onTranslationChanged: root.launcherScroll = Math.max(0, Math.min(
                    root.padAreaHeight - pads.height, startScroll - translation.y))
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
                xAxis.enabled: false
                property real startLevel
                onActiveChanged: if (active) startLevel = strip.level
                onTranslationChanged: strip.stripModel.setLevel(strip.index,
                                          startLevel - translation.y / fader.height)
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

    // A launcher pad (zynthian_gui_launcher_pad): sequence name, play state, repeat mode, length;
    // the main strip's pads are the phrases (with tempo, time signature, loops)
    component Pad: Rectangle {
        id: pad

        property int chainId
        property int phrase
        property bool isMain
        property bool selected
        property var info: ({})

        // Reloaded on a change while the launcher is shown, else when it is shown next
        readonly property bool shown: root.launcherMode
        property bool stale: true
        function reload() { info = root.launcher.padInfo(chainId, phrase); stale = false }
        function changed() { if (shown) reload(); else stale = true }
        onShownChanged: if (shown && stale) reload()
        onChainIdChanged: changed()
        onPhraseChanged: changed()
        Component.onCompleted: if (shown) reload()
        Connections {
            target: root.launcher
            function onPadChanged(c, p) { if (c === pad.chainId && p === pad.phrase) pad.changed() }
            function onPadsChanged() { pad.changed() }
        }

        color: info.color || Theme.panelHighlight
        border.color: selected ? "yellow" : Theme.panel
        border.width: selected ? 2 : 1

        // Phrase loops (main strip)
        Repeater {
            model: pad.info.loops || []
            Item {
                required property var modelData
                required property int index
                x: 2 + index * 7
                width: 5
                height: pad.height
                Rectangle {
                    visible: modelData.part !== "bottom"
                    width: parent.width; height: parent.height / 2; color: modelData.top
                }
                Rectangle {
                    visible: modelData.part !== "top"
                    y: parent.height / 2; width: parent.width; height: parent.height / 2; color: modelData.bottom
                }
                Text {
                    visible: modelData.text !== ""
                    x: 7; y: 2; text: modelData.text; color: Theme.text; font.pixelSize: 11
                }
            }
        }
        Text {
            anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 3
            anchors.leftMargin: (pad.info.loops || []).length ? 3 + 7 * pad.info.loops.length : 3
            text: pad.info.state_text || ""; color: pad.info.state_color || Theme.text; font.pixelSize: 13
        }
        Text {
            anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 3
            text: pad.info.tempo_text || ""; color: pad.info.text_color || Theme.text; font.pixelSize: 11
        }
        Text {
            anchors.centerIn: parent
            width: parent.width - 8
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            text: pad.info.title || ""
            color: pad.info.text_color || Theme.text
            font.pixelSize: (pad.info.title || "").length > 3 ? 14 : 18
            font.family: Theme.fontFamily
        }
        Text {
            anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: 3
            text: pad.info.mode_text || ""; color: pad.info.mode_color || Theme.text; font.pixelSize: 12
        }
        Text {
            anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 3
            text: pad.info.timesig_text || ""; color: pad.info.text_color || Theme.text; font.pixelSize: 12
        }
        TapHandler {
            onTapped: root.launcher.tapPad(pad.chainId, pad.phrase)
            onLongPressed: root.launcher.longPressPad(pad.chainId, pad.phrase)
        }
    }

    component StripButton: Rectangle {
        id: button
        property alias text: t.text
        property bool on
        property color onColor
        signal tapped
        width: root.stripWidth - 8
        height: 36
        color: on ? onColor : Theme.keyBackground
        Text { id: t; anchors.centerIn: parent; color: Theme.text; font.pixelSize: 16 }
        TapHandler { gesturePolicy: TapHandler.ReleaseWithinBounds; onTapped: button.tapped() }
    }

    component MoveButton: Rectangle {
        id: moveButton
        property alias text: moveLabel.text
        signal tapped
        width: 90
        height: 60
        radius: 4
        color: moveTap.pressed ? Theme.keyText : "#e0202830"
        border.color: Theme.select
        border.width: 2
        Text {
            id: moveLabel
            anchors.centerIn: parent
            color: Theme.text
            font.pixelSize: 24
            font.family: Theme.fontFamily
        }
        TapHandler { id: moveTap; gesturePolicy: TapHandler.ReleaseWithinBounds; onTapped: moveButton.tapped() }
    }
}
