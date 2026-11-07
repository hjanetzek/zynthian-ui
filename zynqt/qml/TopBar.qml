// Top bar: screen title, status (xrun, CPU load, MIDI, recorder) and the main mixbus meters
import QtQuick

Rectangle {
    id: root

    property string title
    property bool overlayHint: false   // undocked keypad: the title brings it up

    signal titleTapped
    signal titleSwipedDown
    signal statusTapped

    readonly property var status: zyn.status
    readonly property var mainLevels: mainMeters.levels

    color: Theme.background

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

    Text {
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: 8
        anchors.right: statusRow.left
        elide: Text.ElideRight
        text: (root.overlayHint ? "☰ " : "") + root.title
        color: Theme.text
        font.pixelSize: 28
        font.family: Theme.fontFamily
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
            color: "#ff0000"
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
                if (s.xrunLevel === 2 || s.overtemp) return "#ff0000"
                if (s.xrunLevel === 1) return "#ff9000"
                if (s.undervoltage) return "#ff0000"
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
            FlagIcon { glyph: "\uf111"; on: !!statusRow.st.audioRecorder; color: "#b00000" }
            FlagIcon { glyph: "\uf04b"; on: !!statusRow.st.audioPlayer; color: "#00c000" }
            FlagIcon { glyph: "\uf111"; on: !!statusRow.st.midiRecorder; color: "#ff00ff" }
            FlagIcon { glyph: "\uf04b"; on: !!statusRow.st.midiPlayer; color: "#ff00ff" }
            FlagIcon { glyph: "\uf111"; on: !!statusRow.st.seqRecord; color: "#ff9000" }
            FlagIcon { glyph: "\uf04b"; on: !!statusRow.st.seqPlay; color: "#ff9000" }
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
                    color: "#19b1f7"
                }
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 2
                    visible: !!statusRow.st.midiClock
                    color: "#19b1f7"
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
        TextMetrics { id: metrics; text: slot.sample; font.pixelSize: 12 }
        Text {
            visible: slot.label !== ""
            anchors.left: parent.left
            text: slot.label; color: slot.color; font.pixelSize: 12
        }
        Text {
            anchors.right: parent.right
            text: slot.text; color: slot.color; font.pixelSize: 12
        }
    }
}
