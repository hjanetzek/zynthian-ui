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

        header: Item {
            width: procs.width
            height: 60
            Rectangle {
                width: parent.width
                height: 56
                radius: 3
                color: Theme.panelHighlight
                Text {
                    anchors.centerIn: parent
                    text: "Chain Options"
                    color: Theme.text
                    font.pixelSize: 15
                }
                TapHandler { onTapped: zyn.openChainOptions(-1) }
            }
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
                onLongPressed: { root.cc.selectProcessor(index); zyn.cuia("bank_preset", []) }
            }
        }
    }

    // Controller pages
    ListView {
        id: pages

        anchors.left: procs.right
        anchors.leftMargin: 4
        anchors.top: parent.top
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
}
