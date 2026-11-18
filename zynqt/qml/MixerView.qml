// Mixer (classic's look; galactica, enterprise): one strip per chain (mixerStrips), the main
// mixbus on the right (mainStrip). Content and touch as tk's mixer (MixerScreen.qml, Tk's
// zynthian_gui_mixer); keep the two in step:
// - a strip's header shows Tk's legend (the chain's kind and MIDI channel; arrows while the chain
//   is moved), its description (engine and preset), the clip progress, the MIDI activity and the
//   chain that gets the MIDI input; MIDI chains (no mixer) have no fader, balance or buttons;
// - header: tap chain control, long press (400 ms) the chain manager at the chain's options,
//   wheel the arrows; fader: a tap or drag selects the chain (several at once with multitouch),
//   wheel nudges the level; balance: wheel; mute and the toggle control (admin) by tap;
// - the strips scroll to the active chain.
// Classic extras: balance drag and double tap, the move buttons. Meters run while it is shown.
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
        // Keep the active chain in view (as tk's mixer)
        function showActive() {
            for (let i = 0; i < count; i++) {
                const it = itemAtIndex(i)
                if (it && it.active) { positionViewAtIndex(i, ListView.Contain); return }
            }
        }
        Connections {
            target: mixerStrips
            function onDataChanged() { strips.showActive() }
        }

        delegate: Strip {
            lv: root.stripLevels
            meters: mixerMeters
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
            meters: mainMeters
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
        required property string description
        required property string legend
        required property bool hasMixer
        required property bool activeMidi
        property var lv: []   // levels of all strips (MixerMeters.levels)
        property var meters: null
        property var stripModel
        property bool isMain: false
        // Tk refresh_status: the clip progress (0..100) and the ZMOP's MIDI activity
        readonly property real clipProgress: meters && meters.progress ? (meters.progress[meterIndex] || 0) : 0
        readonly property bool midiActive: meters && meters.midiActivity ? !!meters.midiActivity[meterIndex] : false
        function nudge(symbol, steps) {
            if (symbol === "level")
                stripModel.setLevel(index, Math.max(0, Math.min(1, level + steps * 0.01)))
            else
                stripModel.setBalance(index, Math.max(-1, Math.min(1, balance + steps * 0.02)))
        }

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
            // Tk's legend: the chain's kind (forkawesome) and MIDI channel; arrows while moved
            textFormat: Text.RichText
            text: {
                if (zyn.movingChain && strip.active && strip.chainId !== 0)
                    return "⇦⇨"
                let out = ""
                for (const ch of strip.legend) {
                    const c = ch.codePointAt(0)
                    out += c >= 0xf000 ? "<span style=\"font-family:'forkawesome'\">" + ch + "</span>" : ch
                }
                return out
            }
            color: Theme.text
            size: 16
            title: true
        }
        // Clip progress (Tk: the clip's, the main strip's the phrase's, position): a bar on top
        Rectangle {
            visible: width > 0
            x: 2; y: 1
            width: Math.floor(strip.clipProgress * (strip.width - 4) / 100)
            height: 3
            color: Theme.text
        }
        // MIDI activity (Tk's midi_indicator)
        Rectangle {
            visible: strip.midiActive
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 4
            width: 6; height: 6; radius: 3
            color: Theme.midiActivity
        }

        Label {
            id: nameText
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: title.bottom
            anchors.margins: 2
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            // Engine and preset (Tk's vertical strip label)
            text: strip.description
            maximumLineCount: 2
            wrapMode: Text.NoWrap
            lineHeight: 0.95
            color: Theme.textOff
            size: 11
        }
        // The chain that gets the MIDI input (Tk: the legend's bottom line in the highlight colour)
        Rectangle {
            visible: strip.activeMidi
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: nameText.bottom
            anchors.margins: 2
            height: 2
            color: Theme.select
        }

        // Strip header (legend and description): tap chain control, long press (Tk: > 400 ms) the
        // chain manager at the chain's options, wheel the arrows (as tk's legend)
        Item {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: nameText.bottom
            TapHandler {
                longPressThreshold: 0.4
                onTapped: zyn.openChain(strip.chainId)
                onLongPressed: zyn.openChainManagerOptions(strip.chainId)
            }
            WheelHandler {
                onWheel: (ev) => zyn.cuia(ev.angleDelta.y > 0 ? "arrow_right" : "arrow_left", [])
            }
        }

        // Balance: a bar from the centre
        Item {
            id: balanceBar
            visible: strip.hasMixer
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
            WheelHandler { onWheel: (ev) => strip.nudge("balance", ev.angleDelta.y > 0 ? 1 : -1) }
        }

        // Launcher mode: the level as a horizontal bar (drag sideways)
        Item {
            id: levelBar
            visible: root.launcherMode && strip.hasMixer
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

            // The pads (created when the launcher is first shown, or after the first frame)
            Deferred {
                y: -root.launcherScroll
                width: parent.width
                needed: root.launcherMode
                sourceComponent: Component {
                    Column {
                        Repeater {
                            // Kept once created: creating the pads (strips x phrases) on each switch
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
                visible: strip.hasMixer
                anchors.bottom: parent.bottom
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width - 8
                height: parent.height * strip.level
                color: Theme.panelHighlight
            }

            Row {
                visible: strip.hasMixer
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
                visible: strip.hasMixer
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
                // A press on the fader selects the chain, then drags its level (as tk)
                onActiveChanged: if (active) { zyn.selectChain(strip.chainId); startLevel = strip.level }
                onTranslationChanged: if (active && strip.hasMixer) strip.stripModel.setLevel(strip.index,
                                          Math.max(0, Math.min(1, startLevel - Theme.localDrag(parent, centroid).y / fader.height)))
            }
            TapHandler { onTapped: zyn.selectChain(strip.chainId) }
            WheelHandler { onWheel: (ev) => strip.nudge("level", ev.angleDelta.y > 0 ? 1 : -1) }
        }

        Column {
            id: buttons

            visible: strip.hasMixer
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
