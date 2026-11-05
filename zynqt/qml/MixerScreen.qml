// Mixer: one strip per chain (mixerStrips), the main mixbus on the right (mainStrip). Faders by
// drag (several at once with multitouch), mute and solo by tap. Meters run while it is shown.
import QtQuick

Item {
    id: root

    property bool shown: true
    // The meters' levels, read once per update: every read of a Python list property converts it
    readonly property var stripLevels: mixerMeters.levels
    readonly property var mainLevels: mainMeters.levels
    readonly property int stripWidth: Math.max(40, Math.min(72, (width - 4) / Math.max(1, mixerStrips.count + 1) - 2))

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

        delegate: Strip {
            lv: root.stripLevels
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
            stripModel: mainStrip
            isMain: true
            width: root.stripWidth
            height: mainStripView.height
        }
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

    Text {
        anchors.centerIn: strips
        visible: mixerStrips.count === 0
        text: zyn.started ? "No chains" : ""
        color: Theme.textOff
        font.pixelSize: 24
        font.family: Theme.fontFamily
    }

    component Strip: Rectangle {
        id: strip

        required property int index
        required property int chainId
        required property string name
        required property int midiChan
        required property real level
        required property real balance
        required property bool mute
        required property bool solo
        required property int meterIndex
        required property bool active
        property var lv: []   // levels of all strips (MixerMeters.levels)
        property var stripModel
        property bool isMain: false

        color: Theme.panel
        // The active chain; red while it is being moved
        border.color: active ? (zyn.movingChain ? Theme.select : Theme.text) : "transparent"
        border.width: active ? 2 : 0

        Text {
            id: title
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 2
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            text: strip.isMain ? "Main" : (strip.midiChan >= 0 ? strip.midiChan + 1 : "")
            color: Theme.text
            font.pixelSize: 16
            font.family: Theme.fontFamily
        }

        Text {
            id: nameText
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: title.bottom
            anchors.margins: 2
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            text: strip.name
            color: Theme.textOff
            font.pixelSize: 12
        }

        // Strip header (number and name): tap opens the chain's controllers, long press its options
        Item {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: nameText.bottom
            TapHandler {
                onTapped: zyn.openChain(strip.chainId)
                onLongPressed: zyn.openChainOptions(strip.chainId)
            }
        }

        // Balance: a bar from the centre
        Item {
            id: balanceBar
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
                yAxis.enabled: false
                property real startBalance
                onActiveChanged: if (active) startBalance = strip.balance
                onTranslationChanged: strip.stripModel.setBalance(strip.index,
                                          startBalance + 2 * translation.x / balanceBar.width)
            }
            TapHandler { onDoubleTapped: strip.stripModel.setBalance(strip.index, 0) }
        }

        Item {
            id: fader

            anchors.top: balanceBar.bottom
            anchors.topMargin: 6
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
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width - 4
                height: 6
                y: parent.height * (1 - strip.level) - height / 2
                color: Theme.text
            }

            DragHandler {
                target: null
                xAxis.enabled: false
                property real startLevel
                onActiveChanged: if (active) startLevel = strip.level
                onTranslationChanged: strip.stripModel.setLevel(strip.index,
                                          startLevel - translation.y / fader.height)
            }
        }

        Column {
            id: buttons

            anchors.bottom: parent.bottom
            anchors.bottomMargin: 4
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 4
            StripButton {
                text: "M"; on: strip.mute; onColor: Theme.mute
                onTapped: strip.stripModel.toggleMute(strip.index)
            }
            StripButton {
                visible: !strip.isMain
                text: "S"; on: strip.solo; onColor: Theme.solo
                onTapped: strip.stripModel.toggleSolo(strip.index)
            }
        }
    }

    component StripButton: Rectangle {
        id: button
        property alias text: t.text
        property bool on
        property color onColor
        signal tapped
        width: root.stripWidth - 8
        height: 36
        color: on ? onColor : Theme.keyBackground
        Text { id: t; anchors.centerIn: parent; color: Theme.text; font.pixelSize: 16 }
        TapHandler { onTapped: button.tapped() }
    }

    component MoveButton: Rectangle {
        id: moveButton
        property alias text: moveLabel.text
        signal tapped
        width: 90
        height: 60
        radius: 4
        color: moveTap.pressed ? Theme.keyText : "#e0202830"
        border.color: Theme.select
        border.width: 2
        Text {
            id: moveLabel
            anchors.centerIn: parent
            color: Theme.text
            font.pixelSize: 24
            font.family: Theme.fontFamily
        }
        TapHandler { id: moveTap; onTapped: moveButton.tapped() }
    }
}
