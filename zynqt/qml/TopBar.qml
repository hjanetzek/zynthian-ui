// Top bar: screen title, status (xrun, CPU load, MIDI, recorder) and the main mixbus meters
import QtQuick

Rectangle {
    id: root

    property string title

    readonly property var status: zyn.status
    readonly property var mainLevels: mainMeters.levels

    color: Theme.background

    Text {
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: 8
        anchors.right: statusRow.left
        elide: Text.ElideRight
        text: root.title
        color: Theme.text
        font.pixelSize: 28
        font.family: Theme.fontFamily
    }

    Column {
        id: statusRow

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

        Row {
            spacing: 8
            anchors.right: parent.right
            Text {
                text: "CPU " + (root.status.cpuLoad || 0) + "%"
                color: (root.status.cpuLoad || 0) > 80 ? Theme.meterHigh : Theme.textOff
                font.pixelSize: 12
            }
            Text { visible: !!root.status.xrun; text: "XRUN"; color: Theme.meterHigh; font.pixelSize: 12 }
            Text { visible: !!root.status.midi; text: "MIDI"; color: Theme.meterLow; font.pixelSize: 12 }
            Text { visible: !!root.status.audioRecorder; text: "\u25cf REC"; color: Theme.meterHigh; font.pixelSize: 12 }
            Text { visible: !!root.status.midiRecorder; text: "\u25cf MIDI REC"; color: Theme.meterHigh; font.pixelSize: 12 }
            Text { visible: !!root.status.audioPlayer; text: "PLAY"; color: Theme.meterLow; font.pixelSize: 12 }
        }
    }
}
