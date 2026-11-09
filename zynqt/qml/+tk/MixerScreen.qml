import QtQuick
import ".."

// tk: the Tk mixer (zynthian_gui_mixer): fixed-width strips (W / (visible + 0.2)), from the top a
// toggle button, a mute button (speaker icon), a flags row, the balance bar, the fader (a fill
// from the bottom, no handle) with two peak meters and a vertical two-line label, and the legend
// (chain kind and MIDI channel; red when selected, dark red main, dark blue mixbus). The main
// strip on the right, the others scroll. Launcher mode (zynthian_gui_mixer.set_launcher_mode):
// the same strips, the fader replaced by the level as a horizontal bar and a column of pads (the
// main strip: the phrases).
Item {
    id: root

    property bool shown: true
    readonly property bool launcherMode: zyn.currentScreen === "launcher"

    readonly property var launcher: zyn.launcherModel
    property real launcherScroll: 0

    // Geometry as zynthian_gui_mixer.update_layout
    readonly property int visibleChains: zyn.visibleChains > 0 ? zyn.visibleChains
        : (width <= 400 ? 6 : width <= 600 ? 8 : width <= 800 ? 10 : width <= 1024 ? 12 : width <= 1280 ? 14 : 16)
    readonly property int stripWidth: Math.floor(width / (visibleChains + 0.2))
    readonly property int mainWidth: stripWidth + Math.floor(0.2 * stripWidth)
    readonly property int buttonHeight: Math.floor(height * 0.07)
    readonly property int legendHeight: Math.floor(height * 0.08)
    readonly property int balanceHeight: Math.floor(height * 0.03)
    readonly property int flagsHeight: Math.floor(height * 0.015)
    readonly property int balanceY: 2 * buttonHeight + flagsHeight
    readonly property int faderY: balanceY + balanceHeight
    readonly property int legendY: height - legendHeight
    readonly property int faderHeight: legendY - faderY
    readonly property int launcherY: faderY + balanceHeight
    readonly property int padHeight: Math.floor((legendY - launcherY) / (launcher.visiblePads + 0.2))
    readonly property real padAreaHeight: padHeight * launcher.phrases
    function showPhrase(phrase) {
        const top = phrase * padHeight
        const view = legendY - launcherY
        if (top < launcherScroll)
            launcherScroll = Math.max(0, top)
        else if (top + padHeight > launcherScroll + view)
            launcherScroll = Math.max(0, top + padHeight - view)
    }
    Connections {
        target: root.launcher
        function onPhraseChanged() { root.showPhrase(root.launcher.phrase) }
    }
    // Fonts in Tk points: min(legend / 2, W / 4); labels 0.9, icons 1.2 of it
    readonly property int fontPt: Math.min(Math.floor(0.5 * legendHeight), Math.floor(0.25 * width))

    readonly property color panelBg: Theme.tkColor("panel_bg", "#3a424d")
    readonly property color faderColor: Theme.tkColor("off", "#5a626d")
    readonly property color faderColorHl: "#6a727d"
    readonly property color legendHl: Theme.tkColor("on", "#ff0000")
    // The strips' meters run while the mixer is shown (MixerView does the same)
    Binding { target: mixerMeters; property: "active"; value: root.visible }
    readonly property var stripLevels: mixerMeters.levels
    readonly property var mainLevels: mainMeters.levels
    property int activeMidiChan: -1   // the selected chain's MIDI channel: its strips underlined

    visible: true
    Rectangle {
        anchors.fill: parent
        color: root.panelBg
    }

    ListView {
        id: strips
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: Math.min(count, root.visibleChains) * root.stripWidth
        orientation: ListView.Horizontal
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        interactive: false   // Tk: swipe on the legend scrolls (below)
        highlightMoveDuration: 0
        model: mixerStrips
        delegate: TkStrip {
            width: root.stripWidth
            height: strips.height
            stripModel: mixerStrips
            levels: root.stripLevels
        }
        function showActive() {
            for (let i = 0; i < count; i++) {
                const it = itemAtIndex(i)
                if (it && it.isActive) { positionViewAtIndex(i, ListView.Contain); return }
            }
        }
        Connections {
            target: mixerStrips
            function onDataChanged() { strips.showActive() }
        }
        // Swipe on the legend row scrolls the strips
        DragHandler {
            target: null
            yAxis.enabled: false
            property real startX: 0
            onActiveChanged: startX = strips.contentX
            onTranslationChanged: strips.contentX = Math.max(0, Math.min(strips.contentWidth - strips.width, startX - translation.x))
        }
    }

    // Black gap left of the main strip
    Rectangle {
        anchors.right: mainView.left
        width: 4
        height: root.faderY + root.faderHeight
        color: "#000000"
    }

    ListView {
        id: mainView
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: root.mainWidth
        interactive: false
        model: mainStrip
        delegate: TkStrip {
            width: root.mainWidth
            height: mainView.height
            stripModel: mainStrip
            levels: root.mainLevels
            isMain: true
        }
    }

    component TkStrip: Item {
        id: strip

        required property int index
        required property int chainId
        required property string description
        required property string legend
        required property real level
        required property real balance
        required property bool mute
        required property bool toggle
        required property string toggleLabel
        required property bool isMixbus
        required property bool active
        required property bool hasMixer
        required property int meterIndex
        required property int midiChan
        onActiveChanged: if (active) root.activeMidiChan = midiChan
        Component.onCompleted: if (active) root.activeMidiChan = midiChan
        property var stripModel
        property var levels: []
        property bool isMain: false
        readonly property bool isActive: active
        readonly property int sepWidth: 1
        readonly property int wwidth: width - sepWidth
        readonly property int dpmWidth: Math.floor(width / 13)
        readonly property int faderWidth: width - 2 * dpmWidth - 4

        function lvl(i) { return levels[4 * meterIndex + i] || 0 }
        function nudge(symbol, steps) {
            if (symbol === "level")
                stripModel.setLevel(index, Math.max(0, Math.min(1, level + steps * 0.01)))
            else
                stripModel.setBalance(index, Math.max(-1, Math.min(1, balance + steps * 0.02)))
        }

        // Toggle button
        Rectangle {
            visible: strip.hasMixer
            width: strip.wwidth; height: root.buttonHeight
            color: strip.toggle ? "#d0d000" : root.panelBg
            Text {
                anchors.centerIn: parent
                text: strip.toggleLabel
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: Theme.tkPx(root.fontPt)
            }
            TapHandler { onTapped: strip.stripModel.toggleControl(strip.index) }
        }
        // Mute button
        Rectangle {
            visible: strip.hasMixer
            y: root.buttonHeight
            width: strip.wwidth; height: root.buttonHeight
            color: strip.mute ? "#cc0000" : root.panelBg
            Text {
                anchors.centerIn: parent
                text: strip.mute ? "" : ""
                color: Theme.text
                font.family: "forkawesome"
                font.pixelSize: Theme.tkPx(Math.floor(1.2 * root.fontPt))
            }
            TapHandler { onTapped: strip.stripModel.toggleMute(strip.index) }
        }
        // Separator between strips (black), over the buttons and the balance (launcher mode:
        // also the level bar)
        Rectangle {
            x: strip.wwidth; width: strip.sepWidth
            height: root.launcherMode ? root.launcherY : root.faderY
            color: "#000000"
        }
        // Balance
        Rectangle {
            id: balanceBar
            visible: strip.hasMixer
            x: 1; y: root.balanceY
            width: strip.width - 2; height: root.balanceHeight
            color: "#888888"
            readonly property real centre: strip.width / 2 - 1
            readonly property real bw: strip.width / 2
            Rectangle {
                x: strip.balance >= 0 ? balanceBar.centre - 1 : balanceBar.centre + strip.balance * balanceBar.bw - 1
                width: Math.abs(strip.balance) * balanceBar.bw + 2
                height: parent.height
                color: "#00ee00"
            }
            WheelHandler {
                onWheel: (ev) => strip.nudge("balance", ev.angleDelta.y > 0 ? 1 : -1)
            }
        }
        // Launcher mode: the level as a horizontal bar, the pads
        Rectangle {
            visible: root.launcherMode && strip.hasMixer
            y: root.faderY
            width: strip.wwidth * strip.level
            height: root.balanceHeight
            color: strip.active ? root.faderColorHl : root.faderColor
        }
        Item {
            visible: root.launcherMode
            y: root.launcherY
            width: strip.width
            height: root.legendY - root.launcherY
            clip: true
            Column {
                y: -root.launcherScroll
                Repeater {
                    model: root.launcher.phrases
                    LauncherPad {
                        required property int index
                        launcher: root.launcher
                        shown: root.launcherMode
                        chainId: strip.chainId
                        phrase: index
                        isMain: strip.isMain
                        selected: strip.active && index === root.launcher.phrase
                        fontPt: root.fontPt
                        width: strip.width
                        height: root.padHeight
                    }
                }
            }
            DragHandler {
                target: null
                xAxis.enabled: false
                property real startScroll: 0
                onActiveChanged: if (active) startScroll = root.launcherScroll
                onTranslationChanged: root.launcherScroll = Math.max(0, Math.min(
                    root.padAreaHeight - parent.height, startScroll - translation.y))
            }
            WheelHandler {
                onWheel: (event) => root.launcherScroll = Math.max(0, Math.min(
                    root.padAreaHeight - parent.height, root.launcherScroll - event.angleDelta.y / 2))
            }
        }
        // Fader
        Item {
            id: fader
            visible: !root.launcherMode
            y: root.faderY
            width: strip.width
            height: root.faderHeight
            Rectangle {
                visible: strip.hasMixer
                y: parent.height * (1 - strip.level)
                width: strip.faderWidth
                height: parent.height - y
                color: strip.active ? root.faderColorHl : root.faderColor
            }
            // Peak meters (A, B) on the right
            Repeater {
                model: strip.hasMixer ? 2 : 0
                Rectangle {
                    required property int index
                    x: strip.wwidth - (2 - index) * strip.dpmWidth - (1 - index) * 2
                    width: strip.dpmWidth
                    height: fader.height
                    color: "#1a1a1a"
                    Rectangle {
                        readonly property real v: strip.lvl(parent.index)
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: parent.height * v
                        color: v > 0.95 ? "#f00000" : (v > 0.8 ? "#c8c800" : "#00c800")
                    }
                }
            }
            // 0 dB line
            Rectangle {
                visible: strip.hasMixer
                x: strip.faderWidth; y: Math.round(fader.height * 0.2)
                width: strip.wwidth - strip.faderWidth; height: 1
                color: "#c8c8c8"
            }
            // dB scale on the main strip (0 dB at 80 % of the fader, 2 % per dB)
            Repeater {
                model: strip.isMain ? [9, 6, 3, 0, -3, -6, -10, -20, -30] : []
                Text {
                    required property int modelData
                    anchors.right: parent.right
                    anchors.rightMargin: 2 * strip.dpmWidth + 6
                    y: fader.height * (1 - (0.8 + modelData * 0.02)) - height / 2
                    text: (modelData > 0 ? "+" : "") + modelData
                    color: modelData > 6 ? "#f00000" : (modelData > 0 ? "#c8c800" : (modelData === 0 ? "#c8c8c8" : "#00c800"))
                    font.family: "DejaVu Sans"
                    font.pixelSize: Math.max(8, Math.round(root.fontPt * 0.55))
                }
            }
            // Label: engine and preset, vertical, bottom to top
            Text {
                x: 0
                y: fader.height - 6
                width: fader.height * 0.95
                transformOrigin: Item.TopLeft
                rotation: -90
                text: strip.description
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: Theme.tkPx(Math.floor(0.9 * root.fontPt))
                lineHeight: 0.95
                elide: Text.ElideRight
                maximumLineCount: 2
            }
            property real pressY: 0
            property real pressLevel: 0
            DragHandler {
                target: null
                xAxis.enabled: false
                onActiveChanged: if (active) {
                    zyn.selectChain(strip.chainId)
                    fader.pressLevel = strip.level
                }
                onTranslationChanged: if (active && strip.hasMixer)
                    strip.stripModel.setLevel(strip.index, Math.max(0, Math.min(1, fader.pressLevel - translation.y / root.faderHeight)))
            }
            TapHandler { onTapped: zyn.selectChain(strip.chainId) }
            WheelHandler {
                onWheel: (ev) => strip.nudge("level", ev.angleDelta.y > 0 ? 1 : -1)
            }
        }
        // Separator on the fader: black between strips
        Rectangle {
            x: strip.wwidth; y: root.faderY; width: strip.sepWidth
            height: root.faderHeight
            color: "#000000"
            visible: strip.isMain
        }
        // Legend
        Rectangle {
            y: root.legendY
            width: strip.width
            height: root.legendHeight
            color: strip.active ? root.legendHl
                                : (strip.chainId === 0 ? "#550000" : (strip.isMixbus ? "#000055" : root.panelBg))
            Text {
                anchors.centerIn: parent
                anchors.verticalCenterOffset: 2
                textFormat: Text.RichText
                text: {
                    // Tk: the chain being moved shows arrows
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
                font.family: Theme.fontFamily
                font.pixelSize: Theme.tkPx(root.fontPt)
            }
            // MIDI chains on the selected chain's channel: a white line on top
            Rectangle {
                visible: strip.midiChan >= 0 && strip.midiChan === root.activeMidiChan && !strip.isMain
                width: strip.wwidth
                height: 4
                color: Theme.text
            }
            // Tap: chain control; long press (Tk: > 400 ms): the chain manager at its options
            TapHandler {
                longPressThreshold: 0.4
                onTapped: zyn.openChain(strip.chainId)
                onLongPressed: zyn.openChainManagerOptions(strip.chainId)
            }
            WheelHandler {
                onWheel: (ev) => zyn.cuia(ev.angleDelta.y > 0 ? "arrow_right" : "arrow_left", [])
            }
        }
    }
}
