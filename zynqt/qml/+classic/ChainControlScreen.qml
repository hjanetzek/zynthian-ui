// Chain control: the chain's processors (left), the controller pages (middle), the four
// controllers of the selected page (right)
import QtQuick
import ".."

Item {
    id: root

    readonly property var cc: zyn.chainControl

    // Processors of the active chain
    ListView {
        id: procs

        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        // HIDE_SIDEBAR / TOGGLE_SIDEBAR: the pages and controllers use the whole width
        width: root.cc.sidebarShown ? 150 : 0
        visible: root.cc.sidebarShown
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

        delegate: Panel {
            required property int index
            required property var modelData
            width: procs.width
            height: 56
            radius: Theme.radius
            button: true
            color: modelData.current ? Theme.panel : Theme.panelHighlight
            borderColor: modelData.current ? Theme.frameActive : Theme.frame
            borderWidth: modelData.current ? Math.max(1, Theme.frameWidth) : Theme.frameWidth
            Column {
                anchors.centerIn: parent
                width: parent.width - 8
                Label {
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                    text: modelData.name
                    color: Theme.text
                    size: 15
                }
                Label {
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    text: modelData.type
                    color: Theme.textOff
                    size: 11
                }
            }
            TapHandler {
                onTapped: root.cc.selectProcessor(index)
                onLongPressed: { root.cc.selectProcessor(index); zyn.openChainScreen("processor_options") }
            }
        }
    }

    // The page's widget above the pages (zynthian_gui_control's widgets): waveform of audio
    // file processors, envelope, filter
    ControlWidget {
        id: waveform
        cc: root.cc
        anchors.left: procs.right
        anchors.leftMargin: 4
        anchors.right: controllers.left
        anchors.rightMargin: 2
        anchors.top: parent.top
        height: visible ? parent.height * 0.5 : 0
    }

    // Controller pages (grey also below the last page, as the selector lists)
    Rectangle {
        anchors.fill: pages
        color: Theme.listBackground
    }
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
        spacing: Theme.listSpacing
        boundsBehavior: Flickable.StopAtBounds
        highlightMoveDuration: 0
        onCurrentIndexChanged: positionViewAtIndex(currentIndex, ListView.Contain)

        delegate: Panel {
            id: row
            required property int index
            required property string title
            required property bool separator
            required property bool header   // a processor without pages: selectable
            readonly property bool current: index === pages.currentIndex
            readonly property bool sectionLook: separator || (header && !current)
            width: pages.width
            height: 44
            color: sectionLook ? Theme.separator : (current ? Theme.select : Theme.panel)
            borderColor: sectionLook ? "transparent" : Theme.frame
            button: true
            Label {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: 10
                elide: Text.ElideRight
                text: row.title
                color: row.sectionLook ? Theme.separatorText : (row.current ? Theme.selectText : Theme.text)
                size: 22
                title: true
            }
            TapHandler {
                enabled: !row.separator
                onTapped: root.cc.pageTapped(row.index)
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
        // Select mode (SELECT, MENU): the knobs choose page and processor, as Tk's disabled
        // controllers
        opacity: root.cc.selectMode ? 0.5 : 1.0
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

    ControlOverlays {
        anchors.fill: parent
        cc: root.cc
        area: pages
    }

    component SideButton: Panel {
        id: button
        property alias text: label.text
        property string screen
        width: procs.width
        height: visible ? 44 : 0
        radius: Theme.radius
        button: true
        color: Theme.keyBackground
        Label {
            id: label
            anchors.centerIn: parent
            color: Theme.keyText
            size: 15
        }
        TapHandler { onTapped: zyn.openChainScreen(button.screen) }
    }
}
