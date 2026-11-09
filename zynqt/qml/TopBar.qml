// Top bar: screen title, status (xrun, CPU load, MIDI, recorder) and the main mixbus meters
import QtQuick

Rectangle {
    id: root

    property string title
    property bool overlayHint: false   // undocked keypad: the title brings it up
    property real barStart: 0   // enterprise: where the segments start (after the elbow's arm)
    // Enterprise: title and status above the segment bar
    readonly property real _shift: Theme.elbow ? -Theme.elbowBar / 2 : 0

    signal titleTapped
    signal titleSwipedDown
    signal statusTapped

    readonly property var status: zyn.status
    readonly property var mainLevels: mainMeters.levels

    color: Theme.background

    // Decoration along the bottom edge (galactica: a rule; +<theme>/TopBarRule.qml)
    TopBarRule {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
    }

    // The title brings up the overlay keypad, the status area docks / undocks it
    Item {
        id: titleArea
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.right: statusRow.left
        z: 1
        TapHandler { onTapped: root.titleTapped() }
        DragHandler {
            target: null
            xAxis.enabled: false
            onTranslationChanged: if (active && translation.y > 20) root.titleSwipedDown()
        }
    }

    // Enterprise: segments continuing the elbow's arm, the last one with a rounded end
    Row {
        visible: Theme.elbow
        anchors.left: parent.left
        anchors.leftMargin: root.barStart
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: Theme.elbowBar
        spacing: 5
        readonly property var c: Theme.barColors.length ? Theme.barColors : ["transparent"]
        Rectangle { width: parent.width - 3 * parent.spacing - 70 - 34 - 56; height: parent.height; color: parent.c[0 % parent.c.length] }
        Rectangle { width: 70; height: parent.height; color: parent.c[1 % parent.c.length] }
        Rectangle { width: 34; height: parent.height; color: parent.c[2 % parent.c.length] }
        Item {
            width: 56; height: parent.height
            clip: true
            Rectangle {   // rounded on the right only
                x: -parent.height; width: parent.width + parent.height; height: parent.height
                radius: parent.height / 2
                color: parent.parent.c[3 % parent.parent.c.length]
            }
        }
    }

    ScrollingTitle {
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        verticalOffset: root._shift
        anchors.left: parent.left
        anchors.leftMargin: 8
        anchors.right: statusRow.left
        text: (root.overlayHint ? "☰ " : "") + root.title
        color: Theme.text
        size: Theme.titleSize
    }

    // Status area as the Tk UI's: top row the main meters, the mute flag and the heart (its
    // colour the CPU load; a warning sign on xruns, undervoltage, overtemperature; an arrow
    // when updates are available); bottom row the recorder / player / sequencer flags in fixed
    // slots (record \uf111, play \uf04b: audio, MIDI file, sequencer), battery, CPU and MIDI
    // activity ("m", underlined with MIDI clock). Nothing moves when flags come and go.
    Item {
        id: statusRow

        readonly property string iconFont: "forkawesome"
        readonly property var st: root.status

        anchors.right: parent.right
        anchors.rightMargin: 6
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Theme.elbow ? Theme.elbowBar : 0
        width: 300

        TapHandler { onTapped: root.statusTapped() }

        // Main mixbus meters
        Column {
            x: 0
            y: 6
            width: parent.width - 52
            spacing: 3
            Repeater {
                model: 2
                Rectangle {
                    required property int index
                    width: parent.width
                    height: 7
                    color: Theme.panel
                    Rectangle {
                        height: parent.height
                        width: parent.width * (root.mainLevels[parent.index] || 0)
                        color: (root.mainLevels[parent.index] || 0) > 0.94 ? Theme.meterHigh : Theme.meterLow
                    }
                }
            }
        }
        Text {
            id: muteFlag
            anchors.right: heart.left
            anchors.rightMargin: 4
            y: 1
            visible: !!statusRow.st.mainMute
            text: "\uf32f"
            font.family: statusRow.iconFont
            font.pixelSize: 20
            color: Theme.alert
        }
        Text {
            id: heart
            anchors.right: parent.right
            y: 1
            font.family: statusRow.iconFont
            font.pixelSize: 22
            text: {
                const s = statusRow.st
                if (s.xrunLevel > 0) return "\uf071"
                if (s.undervoltage) return "\uf0e7"
                if (s.overtemp) return "\uf769"
                return s.updateAvailable ? "\u21bb" : "\u2665"
            }
            color: {
                const s = statusRow.st
                if (s.xrunLevel === 2 || s.overtemp) return Theme.alert
                if (s.xrunLevel === 1) return Theme.warning
                if (s.undervoltage) return Theme.alert
                // As zynthian_gui_base: green below 50 %, to yellow at 75 %, to red at 100 %
                const load = Math.max(0, Math.min(100, s.cpuLoad || 0))
                const cr = load < 50 ? 0 : (load < 75 ? Math.round((load - 50) * 0xcc / 25) : 0xcc)
                const cg = load < 75 ? 0xcc : Math.round((100 - load) * 0xcc / 25)
                return Qt.rgba(cr / 255, cg / 255, 0, 1)
            }
        }

        // Bottom row
        Row {
            x: 0
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 3
            spacing: 4
            FlagIcon { glyph: "\uf111"; on: !!statusRow.st.audioRecorder; color: Theme.flagRecord }
            FlagIcon { glyph: "\uf04b"; on: !!statusRow.st.audioPlayer; color: Theme.flagPlay }
            FlagIcon { glyph: "\uf111"; on: !!statusRow.st.midiRecorder; color: Theme.flagMidi }
            FlagIcon { glyph: "\uf04b"; on: !!statusRow.st.midiPlayer; color: Theme.flagMidi }
            FlagIcon { glyph: "\uf111"; on: !!statusRow.st.seqRecord; color: Theme.flagSeq }
            FlagIcon { glyph: "\uf04b"; on: !!statusRow.st.seqPlay; color: Theme.flagSeq }
        }
        Row {
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 3
            spacing: 8
            // Battery (battery powered devices): AC when on external power
            StatusSlot {
                anchors.bottom: parent.bottom
                visible: statusRow.st.battery !== undefined
                sample: "BAT 100%"
                label: statusRow.st.batteryAc ? "AC" : "BAT"
                text: (statusRow.st.battery || 0) + "%"
                color: !statusRow.st.batteryAc && (statusRow.st.battery || 0) <= 15 ? Theme.meterHigh : Theme.textOff
            }
            StatusSlot {
                anchors.bottom: parent.bottom
                sample: "CPU 100%"
                label: "CPU"
                text: (statusRow.st.cpuLoad || 0) + "%"
                color: (statusRow.st.cpuLoad || 0) > 80 ? Theme.meterHigh : Theme.textOff
            }
            Item {
                width: 18
                height: 20
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 2
                    visible: !!statusRow.st.midi
                    text: "m"
                    font.family: statusRow.iconFont
                    font.pixelSize: 20
                    color: Theme.midiActivity
                }
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 2
                    visible: !!statusRow.st.midiClock
                    color: Theme.midiActivity
                }
            }
        }
    }

    // A flag icon in a fixed slot: shown when on, blank otherwise
    component FlagIcon: Item {
        id: flag
        property string glyph
        property bool on
        property color color
        width: 18
        height: 18
        Text {
            anchors.centerIn: parent
            visible: flag.on
            text: flag.glyph
            font.family: "forkawesome"
            font.pixelSize: 16
            color: flag.color
        }
    }

    // A status text in a slot as wide as `sample`: an optional label at the left, the text
    // right-aligned after it, so neither moves with the text's length
    component StatusSlot: Item {
        id: slot
        property string sample
        property string label
        property string text
        property color color: Theme.textOff
        width: metrics.width
        height: metrics.height
        // In the font of the Labels below
        TextMetrics {
            id: metrics
            text: slot.sample
            font.pixelSize: Math.round(12 * Theme.fontScale)
            font.family: Theme.textFamily
            font.capitalization: Theme.caps ? Font.AllUppercase : Font.MixedCase
            font.letterSpacing: Theme.letterSpacing
        }
        Label {
            visible: slot.label !== ""
            anchors.left: parent.left
            text: slot.label; color: slot.color; size: 12
        }
        Label {
            anchors.right: parent.right
            text: slot.text; color: slot.color; size: 12
        }
    }
}
