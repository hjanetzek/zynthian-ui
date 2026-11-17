// v4: tk's mixer (MixerScreen.qml of zynqt/qml; keep the two in step) between the knob hints
// (+v4/MixerScreen.qml): 8 strips and the main strip by default (the admin's visible mixer strips,
// which count the main strip as Tk's, set another number), scrolling with the selection.
// Launcher mode: 4 chains x 4 phrases and the main strip's phrase column; the view moves by 4
// chains / 4 phrases when the selection leaves it.
import QtQuick
import ".."

Item {
    id: root

    property bool shown: true
    readonly property bool launcherMode: zyn.currentScreen === "launcher"

    readonly property var launcher: zyn.launcherModel
    // The view: the first chain strip and (launcher) the first phrase shown. Derived from the
    // selection whenever it, the number of chains / phrases or the size changes (syncView), and
    // always clamped to [0, count - shown]: never past the start or the end.
    property int chainOffset: 0
    property int phraseOffset: 0
    readonly property real launcherScroll: phraseOffset * padHeight

    // Geometry as zynthian_gui_mixer.update_layout
    // Strips in the width, the main strip (1.2 strips wide) included, as Tk's
    readonly property int visibleChains: launcherMode ? 5 : zyn.visibleChains > 0 ? zyn.visibleChains : 9
    readonly property int pageChains: visibleChains - 1
    // The launcher's grid: 4 x 4 pads
    readonly property int visiblePads: 4
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
    readonly property int padHeight: Math.floor((legendY - launcherY) / visiblePads)
    readonly property real padAreaHeight: padHeight * launcher.phrases
    // The pads' font size (Tk points) from the pad size: the 4 x 4 pads are about twice tk's,
    // their icons, title and length scale with them (tk: the mixer's fontPt)
    readonly property int padFontPt: Math.floor(0.4 * padHeight)
    // An offset that shows item sel of n with page items shown: unchanged while sel is in view;
    // else the page of 4 (launcher) or the nearest offset (mixer) that shows it; clamped
    function follow(offset, sel, n, page, paged) {
        if (sel >= 0 && sel < n && (sel < offset || sel >= offset + page))
            offset = paged ? Math.floor(sel / page) * page : (sel < offset ? sel : sel - page + 1)
        return Math.max(0, Math.min(offset, n - page))
    }
    function clampOffsets() {
        chainOffset = Math.max(0, Math.min(chainOffset, strips.count - pageChains))
        if (launcher)
            phraseOffset = Math.max(0, Math.min(phraseOffset, launcher.phrases - visiblePads))
    }
    function syncView() {
        const row = typeof mixerStrips.activeRow === "number" ? mixerStrips.activeRow : -1
        chainOffset = follow(chainOffset, row, strips.count, pageChains, launcherMode)
        if (launcher)
            phraseOffset = follow(phraseOffset, launcher.phrase, launcher.phrases, visiblePads, true)
        strips.applyOffset()
    }
    // Another strip width: from the start, then to the selection
    onLauncherModeChanged: { chainOffset = 0; phraseOffset = 0; syncView() }
    onPageChainsChanged: syncView()
    onStripWidthChanged: syncView()
    Connections {
        target: root.launcher
        function onPhraseChanged() { root.syncView() }
        function onPadsChanged() { root.syncView() }
    }
    Connections {
        target: mixerStrips
        function onActiveRowChanged() { root.syncView() }
        function onCountChanged() { root.syncView() }
    }
    onChainOffsetChanged: strips.applyOffset()
    Component.onCompleted: syncView()
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
        width: Math.min(count, root.pageChains) * root.stripWidth
        orientation: ListView.Horizontal
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        interactive: false   // Tk: swipe on the legend scrolls (below)
        highlightMoveDuration: 0
        // No current item: the view only moves with root.chainOffset
        currentIndex: -1
        highlightFollowsCurrentItem: false
        model: mixerStrips
        delegate: TkStrip {
            width: root.stripWidth
            height: strips.height
            stripModel: mixerStrips
            levels: root.stripLevels
            meters: mixerMeters
        }
        // The view at root.chainOffset: from originX, which moves when rows are inserted or
        // removed (contentX alone went past the start or the end after snapshot loads)
        function applyOffset() {
            const x = originX + root.chainOffset * root.stripWidth
            if (Math.abs(contentX - x) > 0.5)
                contentX = x
        }
        onOriginXChanged: applyOffset()
        onCountChanged: Qt.callLater(root.syncView)
        onWidthChanged: applyOffset()
        // Swipe on the legend row scrolls the strips
        DragHandler {
            target: null
            yAxis.enabled: false
            property int start: 0
            onActiveChanged: if (active) start = root.chainOffset
            onTranslationChanged: if (active) {
                root.chainOffset = start - Math.round(translation.x / root.stripWidth)
                root.clampOffsets()
                strips.applyOffset()
            }
        }
    }

    // Black gap left of the main strip, down to the bottom (Tk: the window background between
    // the strips' canvas and the main strip's, also beside the legend row)
    Rectangle {
        anchors.right: mainView.left
        width: 4
        height: parent.height
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
            meters: mainMeters
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
        required property bool activeMidi
        property var stripModel
        property var levels: []
        property var meters: null
        // Tk refresh_status: the clip progress (0..100) and the ZMOP's MIDI activity
        readonly property real clipProgress: meters && meters.progress ? (meters.progress[meterIndex] || 0) : 0
        readonly property bool midiActive: meters && meters.midiActivity ? !!meters.midiActivity[meterIndex] : false
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
            Rectangle { anchors.fill: parent; color: root.panelBg }   // the canvas between the pads
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
                        fontPt: root.padFontPt
                        width: strip.width
                        height: root.padHeight
                    }
                }
            }
            DragHandler {
                target: null
                xAxis.enabled: false
                property int start: 0
                onActiveChanged: if (active) start = root.phraseOffset
                onTranslationChanged: if (active) {
                    root.phraseOffset = start - Math.round(translation.y / root.padHeight)
                    root.clampOffsets()
                }
            }
            WheelHandler {
                onWheel: (event) => { root.phraseOffset -= event.angleDelta.y > 0 ? 1 : -1; root.clampOffsets() }
            }
        }
        // Launcher mode: the peak meters over the buttons' right side (set_launcher_mode: dpm_bg,
        // dpm_a, dpm_b from the top to balance_y, the scale gap between them), vertical
        // zynthian_gui_dpm: #222222 above the level, the tri-colour scale below, the -10 dB line
        Item {
            visible: root.launcherMode && strip.hasMixer
            readonly property int scaleWidth: Math.floor(strip.dpmWidth * 0.7)
            x: strip.width - 2 * strip.dpmWidth - scaleWidth
            width: strip.width - x
            height: root.balanceY
            z: 1
            Rectangle { anchors.fill: parent; color: root.panelBg }
            Repeater {
                model: 2
                Item {
                    id: ldpm
                    required property int index
                    readonly property real v: strip.lvl(index)
                    readonly property real h: strip.lvl(2 + index)
                    x: index * (strip.dpmWidth + parent.scaleWidth)
                    width: strip.dpmWidth
                    height: parent.height
                    Rectangle {
                        anchors.fill: parent
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#c80000" }
                            GradientStop { position: 0.03; color: "#c80000" }
                            GradientStop { position: 0.10; color: "#ffff00" }
                            GradientStop { position: 0.20; color: "#ffff00" }
                            GradientStop { position: 0.27; color: "#00ff00" }
                            GradientStop { position: 1.0; color: "#009600" }
                        }
                    }
                    Rectangle {
                        width: parent.width
                        height: Math.ceil(parent.height * (1 - ldpm.v))
                        color: "#222222"
                    }
                    Rectangle {
                        visible: ldpm.h > 0
                        y: Math.floor(parent.height * (1 - ldpm.h))
                        width: parent.width; height: 1
                        color: ldpm.h >= 0.94 ? "#ff0000" : (ldpm.h >= 0.8 ? "#ffff00" : "#00ff00")
                    }
                    Rectangle {
                        y: Math.floor(parent.height * 0.2)
                        width: parent.width; height: 1
                        color: "#999999"
                    }
                }
            }
        }
        // Tk midi_indicator: MIDI activity, a blue block in the flags row over the meters' column
        Rectangle {
            visible: strip.midiActive
            readonly property int tkFaderWidth: strip.width - 2 * strip.dpmWidth
                - Math.floor(strip.dpmWidth * 0.7) - (strip.isMain ? Math.floor(0.2 * strip.width) : 0)
            x: tkFaderWidth
            y: 2 * root.buttonHeight
            width: strip.wwidth - tkFaderWidth
            height: root.flagsHeight
            z: 2
            color: Theme.tkColor("status_midi", "#19b1f7")
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
            // Tk legend_strip_midi_bg: the bottom 2 px, in the highlight colour on the chain
            // that gets the MIDI input
            Rectangle {
                visible: strip.activeMidi
                y: parent.height - 2
                width: parent.width
                height: 2
                color: root.legendHl
            }
            // Tk clip_progress: the clip's (main: the phrase's) position, a bar on top
            Rectangle {
                visible: width > 0
                width: Math.floor(strip.clipProgress * strip.width / 100)
                height: Math.floor(root.legendHeight * 0.15)
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
