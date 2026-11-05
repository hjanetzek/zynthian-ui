// Mock selector screen: a long list (kinetic scrolling by touch) and the info pane
import QtQuick

Item {
    id: root

    property int currentIndex: 1

    ListView {
        id: list

        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: parent.width * 0.7
        clip: true
        model: listItems
        currentIndex: root.currentIndex
        boundsBehavior: Flickable.StopAtBounds
        highlightMoveDuration: 0

        delegate: Rectangle {
            id: row

            required property int index
            required property string title
            required property string info
            required property bool separator

            width: list.width
            height: 44
            color: separator ? Theme.panelHighlight : (index === root.currentIndex ? Theme.select : Theme.panel)

            Text {
                anchors.verticalCenter: parent.verticalCenter
                x: 10
                text: row.title
                color: row.separator ? Theme.textOff : Theme.text
                font.pixelSize: 26
                font.family: Theme.fontFamily
            }

            TapHandler {
                enabled: !row.separator
                onTapped: root.currentIndex = row.index
            }
        }
    }

    Rectangle {
        anchors.left: list.right
        anchors.leftMargin: 2
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        color: Theme.background

        Text {
            anchors.fill: parent
            anchors.margins: 6
            wrapMode: Text.WordWrap
            text: list.currentItem ? list.currentItem.info : ""
            color: Theme.text
            font.pixelSize: 18
        }
    }
}
