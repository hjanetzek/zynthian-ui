// Mock mixer: one strip per chain with two meters, a fader (drag; several at once with
// multitouch), mute and solo
import QtQuick

Rectangle {
    id: screen

    // Read the levels once per update: every read of meters.levels converts the Python list
    readonly property var levels: meters.levels

    color: Theme.background

    ListView {
        id: stripList

        anchors.fill: parent
        orientation: ListView.Horizontal
        model: strips
        interactive: false
        spacing: 1

        delegate: Rectangle {
            id: strip

            required property int index
            required property string name
            required property real level
            required property bool mute
            required property bool solo

            width: stripList.width / 16 - 1
            height: stripList.height
            color: Theme.panel

            Text {
                id: label
                anchors.horizontalCenter: parent.horizontalCenter
                y: 4
                text: strip.index + 1
                color: Theme.text
                font.pixelSize: 16
                font.family: Theme.fontFamily
            }

            // Fader: the whole middle of the strip, with the meters on top
            Item {
                id: fader

                anchors.top: label.bottom
                anchors.topMargin: 4
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
                    Meter { height: parent.height; value: screen.levels[2 * strip.index] || 0 }
                    Meter { height: parent.height; value: screen.levels[2 * strip.index + 1] || 0 }
                }

                Rectangle {   // fader knob
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: parent.width - 4
                    height: 6
                    y: parent.height * (1 - strip.level) - height / 2
                    color: Theme.text
                }

                DragHandler {
                    id: drag
                    target: null
                    xAxis.enabled: false
                    property real startLevel
                    onActiveChanged: if (active) startLevel = strip.level
                    onTranslationChanged: strips.setLevel(strip.index,
                                                          startLevel - translation.y / fader.height)
                }
            }

            Column {
                id: buttons

                anchors.bottom: parent.bottom
                anchors.bottomMargin: 4
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 4
                StripButton { text: "M"; on: strip.mute; onColor: Theme.mute; onTapped: strips.toggleMute(strip.index) }
                StripButton { text: "S"; on: strip.solo; onColor: Theme.solo; onTapped: strips.toggleSolo(strip.index) }
            }
        }
    }

    component StripButton: Rectangle {
        id: button
        property alias text: t.text
        property bool on
        property color onColor
        signal tapped
        width: stripList.width / 16 - 8
        height: 36
        color: on ? onColor : Theme.keyBackground
        Text { id: t; anchors.centerIn: parent; color: Theme.text; font.pixelSize: 16 }
        TapHandler { onTapped: button.tapped() }
    }
}
