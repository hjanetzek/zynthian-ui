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

    Column {
        id: statusRow

        TapHandler { onTapped: root.statusTapped() }

        anchors.right: parent.right
        anchors.rightMargin: 6
        anchors.verticalCenter: parent.verticalCenter
        spacing: 3

        // Main mixbus meters, horizontal
        Repeater {
            model: 2
            Rectangle {
                required property int index
                width: 200
                height: 7
                color: Theme.panel
                Rectangle {
                    height: parent.height
                    width: parent.width * (root.mainLevels[parent.index] || 0)
                    color: (root.mainLevels[parent.index] || 0) > 0.94 ? Theme.meterHigh : Theme.meterLow
                }
            }
        }

        // Fixed slots, so nothing moves when values or flags change: from the right CPU, battery,
        // MIDI and XRUN (shown or blank in their slot); recorder / player flags further left
        // (they only shift each other)
        Row {
            spacing: 8
            anchors.right: parent.right
            Text { visible: !!root.status.audioRecorder; text: "\u25cf REC"; color: Theme.meterHigh; font.pixelSize: 12 }
            Text { visible: !!root.status.midiRecorder; text: "\u25cf MIDI REC"; color: Theme.meterHigh; font.pixelSize: 12 }
            Text { visible: !!root.status.audioPlayer; text: "PLAY"; color: Theme.meterLow; font.pixelSize: 12 }
            StatusSlot { sample: "XRUN"; text: root.status.xrun ? "XRUN" : ""; color: Theme.meterHigh }
            StatusSlot { sample: "MIDI"; text: root.status.midi ? "MIDI" : ""; color: Theme.meterLow }
            // Battery (battery powered devices): AC when on external power
            StatusSlot {
                visible: root.status.battery !== undefined
                sample: "BAT 100%"
                label: root.status.batteryAc ? "AC" : "BAT"
                text: (root.status.battery || 0) + "%"
                color: !root.status.batteryAc && (root.status.battery || 0) <= 15 ? Theme.meterHigh : Theme.textOff
            }
            StatusSlot {
                sample: "CPU 100%"
                label: "CPU"
                text: (root.status.cpuLoad || 0) + "%"
                color: (root.status.cpuLoad || 0) > 80 ? Theme.meterHigh : Theme.textOff
            }
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
