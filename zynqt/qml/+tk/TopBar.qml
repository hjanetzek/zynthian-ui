import QtQuick
import ".."

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

    Label {
        anchors.left: parent.left
        anchors.leftMargin: 2
        anchors.right: statusArea.left
        anchors.verticalCenter: parent.verticalCenter
        elide: Text.ElideRight
        // Chain control (and the special processors' control screens): Tk's select path, the
        // processor's preset path
        text: root.onMixer && root.status.snapshotTitle ? root.status.snapshotTitle
            : ["chain_control", "audio_player", "tempo", "alsa_mixer"].indexOf(zyn.currentScreen) >= 0
              ? zyn.chainControl.selectPath : root.title
        color: Theme.text
        size: Theme.titleSize
        title: true
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

        // Main meters: two bars along the top (invisible when silent)
        Repeater {
            model: 2
            Rectangle {
                required property int index
                x: 0
                y: 1 + index * 8
                width: statusArea.width - 24
                height: 6
                color: "transparent"   // Tk: nothing when silent
                Rectangle {
                    readonly property real v: root.mainLevels[parent.index] || 0
                    height: parent.height
                    width: parent.width * v
                    color: v > 0.95 ? "#f00000" : (v > 0.8 ? "#c8c800" : "#00c800")
                }
            }
        }
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
