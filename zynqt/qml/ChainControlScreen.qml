// Chain control: the chain's processors (left), the controller pages (middle), the four
// controllers of the selected page (right)
import QtQuick

Item {
    id: root

    readonly property var cc: zyn.chainControl

    // Processors of the active chain
    ListView {
        id: procs

        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 150
        spacing: 4
        clip: true
        model: root.cc.processors

        // As the Tk chain sidebar: chain options and MIDI input before the processors, MIDI
        // and audio outputs after them
        header: Column {
            width: procs.width
            bottomPadding: 4
            spacing: 4
            SideButton { text: "Chain Options"; screen: "chain_options"; visible: root.cc.isChain }
            SideButton { text: "MIDI Input"; screen: "midi_in"; visible: root.cc.isMidi }
            SideButton { text: "Audio Input"; screen: "audio_in"; visible: root.cc.hasAudioIn }
        }
        footer: Column {
            width: procs.width
            topPadding: 4
            spacing: 4
            SideButton { text: "MIDI Output"; screen: "midi_out"; visible: root.cc.isMidi }
            SideButton { text: "Audio Output"; screen: "audio_out"; visible: root.cc.isAudio }
        }

        delegate: Rectangle {
            required property int index
            required property var modelData
            width: procs.width
            height: 56
            radius: 3
            color: modelData.current ? Theme.panel : Theme.panelHighlight
            border.color: modelData.current ? Theme.text : "transparent"
            Column {
                anchors.centerIn: parent
                width: parent.width - 8
                Text {
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                    text: modelData.name
                    color: Theme.text
                    font.pixelSize: 15
                }
                Text {
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    text: modelData.type
                    color: Theme.textOff
                    font.pixelSize: 11
                }
            }
            TapHandler {
                onTapped: root.cc.selectProcessor(index)
                onLongPressed: { root.cc.selectProcessor(index); zyn.openChainScreen("processor_options") }
            }
        }
    }

    // Audio file processors: the waveform above the pages
    WaveformView {
        id: waveform
        visible: root.cc.hasWaveform
        view: root.cc.waveform
        anchors.left: procs.right
        anchors.leftMargin: 4
        anchors.right: controllers.left
        anchors.rightMargin: 2
        anchors.top: parent.top
        height: visible ? parent.height * 0.5 : 0
    }

    // Controller pages
    ListView {
        id: pages

        anchors.left: procs.right
        anchors.leftMargin: 4
        anchors.top: waveform.bottom
        anchors.topMargin: waveform.visible ? 4 : 0
        anchors.bottom: parent.bottom
        anchors.right: controllers.left
        anchors.rightMargin: 2
        clip: true
        model: root.cc.pageModel
        currentIndex: root.cc.page
        boundsBehavior: Flickable.StopAtBounds
        highlightMoveDuration: 0
        onCurrentIndexChanged: positionViewAtIndex(currentIndex, ListView.Contain)

        delegate: Rectangle {
            id: row
            required property int index
            required property string title
            required property bool separator
            width: pages.width
            height: 44
            color: separator ? Theme.panelHighlight : (index === pages.currentIndex ? Theme.select : Theme.panel)
            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: 10
                elide: Text.ElideRight
                text: row.title
                color: row.separator ? Theme.textOff : Theme.text
                font.pixelSize: 22
                font.family: Theme.fontFamily
            }
            TapHandler {
                enabled: !row.separator
                onTapped: root.cc.setPage(row.index)
            }
        }
    }

    Column {
        id: controllers

        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: parent.width * 0.3
        spacing: 2
        Repeater {
            model: [root.cc.c0, root.cc.c1, root.cc.c2, root.cc.c3]
            Controller {
                required property var modelData
                ctrl: modelData
                width: controllers.width
                height: (controllers.height - 6) / 4
            }
        }
    }

    // Moving the current processor (processor options: Move)
    Grid {
        anchors.horizontalCenter: pages.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 20
        columns: 3
        spacing: 8
        visible: zyn.movingProcessor
        z: 10
        Item { width: 80; height: 56 }
        MoveKey { text: "\u25b2"; onTapped: zyn.moveProcessor("up") }
        Item { width: 80; height: 56 }
        MoveKey { text: "\u25c0"; onTapped: zyn.moveProcessor("left") }
        MoveKey { text: "Done"; onTapped: zyn.endMoveProcessor() }
        MoveKey { text: "\u25b6"; onTapped: zyn.moveProcessor("right") }
        Item { width: 80; height: 56 }
        MoveKey { text: "\u25bc"; onTapped: zyn.moveProcessor("down") }
    }

    component MoveKey: Rectangle {
        id: moveKey
        property alias text: moveKeyLabel.text
        signal tapped
        width: 80
        height: 56
        radius: 4
        color: moveKeyTap.pressed ? Theme.keyText : "#e0202830"
        border.color: Theme.select
        border.width: 2
        Text { id: moveKeyLabel; anchors.centerIn: parent; color: Theme.text; font.pixelSize: 22 }
        TapHandler { id: moveKeyTap; gesturePolicy: TapHandler.ReleaseWithinBounds; onTapped: moveKey.tapped() }
    }

    component SideButton: Rectangle {
        id: button
        property alias text: label.text
        property string screen
        width: procs.width
        height: visible ? 44 : 0
        radius: 3
        color: Theme.keyBackground
        Text {
            id: label
            anchors.centerIn: parent
            color: Theme.keyText
            font.pixelSize: 15
        }
        TapHandler { onTapped: zyn.openChainScreen(button.screen) }
    }
}
