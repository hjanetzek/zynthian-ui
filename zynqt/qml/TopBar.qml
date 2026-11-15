import QtQuick

// tk: the Tk top bar (zynthian_gui_base): the title on the left in 1.5F points (the mixer: the
// snapshot and ZS3, with beat | bpb/4 and the tempo), the status area (27 % of the width) on the
// right: the main meters, the heart, the recorder / player / sequencer flags. Title: tap the
// root (on the mixer and launcher: switch between them), bold or long press the main menu.
// Status: tap shows / hides the keypad, long press all sounds off.
Rectangle {
    id: root

    property string title: ""
    property bool overlayHint: false   // not used: Tk has no overlay keypad
    property real barStart: 0
    signal titleTapped
    signal titleSwipedDown
    signal statusTapped

    readonly property var status: zyn.status
    readonly property var mainLevels: mainMeters.levels
    readonly property bool onMixer: zyn.currentScreen === "mixer" || zyn.currentScreen === "launcher"
    readonly property real statusWidth: Math.round(0.27 * width)
    readonly property int statusFontPt: Math.floor(0.25 * height)

    color: Theme.background

    // The pattern editor's edit modes (set_edit_mode): their title inverted (color_header_bg on
    // color_panel_tx)
    readonly property bool onPatternEditor: zyn.currentScreen === "pattern_editor"
    readonly property bool inverted: onPatternEditor && zyn.patternEditor.modeTitle !== ""
    Rectangle {
        anchors.left: parent.left
        anchors.right: statusArea.left
        anchors.rightMargin: Math.floor(0.36 * root.height)   // Tk's title canvas
        height: parent.height
        visible: root.inverted
        color: Theme.text
    }

    ScrollingTitle {
        anchors.left: parent.left
        anchors.leftMargin: 2
        anchors.right: statusArea.left
        // Tk's title canvas ends status_lpad (0.36 of the top bar's height) before the status area
        anchors.rightMargin: Math.floor(0.36 * root.height)
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        // Chain control (and the special processors' control screens): Tk's select path, the
        // processor's preset path; the pattern editor: its title or the edit mode's
        text: root.onMixer && root.status.snapshotTitle ? root.status.snapshotTitle
            : ["chain_control", "audio_player", "tempo", "alsa_mixer"].indexOf(zyn.currentScreen) >= 0
              ? zyn.chainControl.selectPath
            : root.onPatternEditor ? (root.inverted ? zyn.patternEditor.modeTitle : zyn.patternEditor.tkTitle)
            : root.title
        color: root.inverted ? Theme.background : Theme.text
        size: Theme.titleSize
    }

    // Zynthian's tap timing on the title (zynthian_gui_base.cb_topbar_*): short, bold, long
    Item {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.right: statusArea.left
        TapHandler {
            property real t0: 0
            longPressThreshold: 0.8
            onPressedChanged: if (pressed) t0 = Date.now()
            onTapped: {
                if (Date.now() - t0 > 300)   // bold (zynswitch_bold_seconds)
                    zyn.cuia("main_menu", [])
                else if (root.onMixer)
                    zyn.cuia("back", [])
                else
                    zyn.cuia("show_screen", ["root"])
            }
            onLongPressed: zyn.cuia("main_menu", [])
        }
    }

    // Tempo on the mixer: beat | bpb/4 and the bpm, right-aligned left of the status area
    Text {
        visible: root.onMixer
        anchors.right: parent.right
        anchors.rightMargin: Math.round(0.065 * root.width)
        y: 2
        z: 2
        text: root.status.beat + "|" + root.status.bpb + "/4 " + (root.status.tempo || 0).toFixed(1) + "bpm"
        color: Theme.text
        font.family: Theme.textFamily
        font.pixelSize: Theme.tkPx(root.statusFontPt)
    }

    Item {
        id: statusArea
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: root.statusWidth
        z: 1

        // Main meters (init_dpmeter): two horizontal zynthian_gui_dpm along the top, H/4 - 2 high,
        // the status width - 2 rows - 1 wide: the tri-colour scale covered by #222222 above the
        // level, the -10 dB line, the peak hold. Tk's mixer shows the tempo there instead.
        Repeater {
            model: 2
            Item {
                id: dpm
                required property int index
                readonly property int rh: Math.max(2, Math.floor(root.height / 4))
                readonly property real level: root.mainLevels[index] || 0
                readonly property real hold: root.mainLevels[2 + index] || 0
                visible: !root.onMixer
                x: 0
                y: index * (height + 2)
                width: Math.floor(root.statusWidth) - 2 * rh - 1
                height: Math.floor(root.height / 4 - 2)
                clip: true
                // get_bg: dark to light green to 73 %, to yellow at 80 %, yellow to 90 %, to red at 97 %
                Rectangle {
                    width: dpm.height
                    height: dpm.width
                    anchors.centerIn: parent
                    rotation: -90
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "#009600" }
                        GradientStop { position: 0.73; color: "#00ff00" }
                        GradientStop { position: 0.80; color: "#ffff00" }
                        GradientStop { position: 0.90; color: "#ffff00" }
                        GradientStop { position: 0.97; color: "#c80000" }
                        GradientStop { position: 1.0; color: "#c80000" }
                    }
                }
                Rectangle {   // the overlay above the level
                    x: Math.floor(dpm.width * dpm.level)
                    width: dpm.width - x
                    height: dpm.height
                    color: "#222222"
                }
                Rectangle {   // peak hold
                    visible: dpm.hold > 0
                    x: Math.floor(dpm.width * dpm.hold)
                    width: 1
                    height: dpm.height
                    color: dpm.hold >= 0.94 ? "#ff0000" : (dpm.hold >= 0.8 ? "#ffff00" : "#00ff00")
                }
                Rectangle {   // zerodB (-10 dB) line
                    x: Math.floor(dpm.width * 0.8)
                    width: 1
                    height: dpm.height
                    color: "#999999"
                }
            }
        }
        // The main meters run on every screen (Tk refreshes the status on all of them)
        Binding { target: mainMeters; property: "active"; value: true }
        // Heart: CPU load colour, warning sign on xruns, undervoltage, overtemperature
        Text {
            anchors.right: parent.right
            anchors.rightMargin: 2
            y: 0
            font.family: "forkawesome"
            font.pixelSize: Math.floor(0.36 * root.height)
            text: root.status.xrun || root.status.undervoltage || root.status.overtemp ? "" : ""
            color: root.status.xrun || root.status.undervoltage || root.status.overtemp ? Theme.warning
                 : Qt.rgba(Math.min(1, (root.status.cpuLoad || 0) / 50), Math.min(1, (100 - (root.status.cpuLoad || 0)) / 50), 0, 1)
        }
        // Flags: audio recorder, audio / MIDI player, MIDI recorder, sequencer
        Row {
            x: 0
            y: Math.round(root.height * 0.45)
            spacing: 6
            Repeater {
                model: [
                    { on: !!root.status.audioRecorder, glyph: "", color: Theme.flagRecord },
                    { on: !!root.status.audioPlayer, glyph: "", color: Theme.flagPlay },
                    { on: !!root.status.midiRecorder, glyph: "", color: Theme.flagRecord },
                    { on: !!root.status.midiPlayer, glyph: "", color: Theme.flagMidi },
                    { on: !!root.status.seqRecord, glyph: "", color: Theme.flagSeq },
                    { on: !!root.status.seqPlay, glyph: "", color: Theme.flagSeq }
                ]
                Text {
                    required property var modelData
                    visible: modelData.on
                    text: modelData.glyph
                    color: modelData.color
                    font.family: "forkawesome"
                    font.pixelSize: Math.floor(0.36 * root.height)
                }
            }
        }
        Text {
            visible: !!root.status.midi
            anchors.right: parent.right
            anchors.rightMargin: 2
            anchors.bottom: parent.bottom
            text: "m"
            color: Theme.midiActivity
            font.family: Theme.textFamily
            font.pixelSize: Theme.tkPx(root.statusFontPt)
            font.underline: !!root.status.midiClock
        }

        TapHandler {
            onTapped: root.statusTapped()
            onLongPressed: zyn.cuia("all_sounds_off", [])
        }
    }
}
