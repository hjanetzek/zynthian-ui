// A selector screen (zynqt.screens): a list with an info pane (and category tabs if the screen
// has categories), or a grid of tiles. Tap selects and activates, long press is a bold press.
import QtQuick

Item {
    id: root

    property var screen: null
    readonly property bool isGrid: screen !== null && screen.viewKind === "grid"
    readonly property var entries: screen ? screen.entryModel : null

    // Category tabs (engines)
    ListView {
        id: tabs

        anchors.left: parent.left
        anchors.right: info.left
        anchors.top: parent.top
        height: visible ? 40 : 0
        visible: !root.isGrid && root.screen !== null && root.screen.categories.length > 1
        orientation: ListView.Horizontal
        spacing: 2
        clip: true
        model: root.screen ? root.screen.categories : []
        currentIndex: root.screen ? root.screen.categoryIndex : 0
        onCurrentIndexChanged: positionViewAtIndex(currentIndex, ListView.Contain)

        delegate: Rectangle {
            required property int index
            required property string modelData
            width: Math.max(90, label.implicitWidth + 24)
            height: tabs.height
            color: index === tabs.currentIndex ? Theme.select : Theme.panelHighlight
            Text {
                id: label
                anchors.centerIn: parent
                text: modelData
                color: Theme.text
                font.pixelSize: 18
                font.family: Theme.fontFamily
            }
            TapHandler { onTapped: root.screen.setCategory(index) }
        }
    }

    ListView {
        id: list

        anchors.left: parent.left
        anchors.top: tabs.bottom
        anchors.topMargin: tabs.visible ? 2 : 0
        anchors.bottom: parent.bottom
        anchors.right: info.left
        anchors.rightMargin: 2
        visible: !root.isGrid
        clip: true
        model: root.isGrid ? null : root.entries
        currentIndex: root.screen ? root.screen.index : -1
        boundsBehavior: Flickable.StopAtBounds
        highlightMoveDuration: 0
        onCurrentIndexChanged: positionViewAtIndex(currentIndex, ListView.Contain)

        delegate: Rectangle {
            id: row

            required property int index
            required property string title
            required property bool separator
            required property bool entryEnabled

            width: list.width
            height: 44
            color: separator ? Theme.panelHighlight : (index === list.currentIndex ? Theme.select : Theme.panel)

            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: 10
                elide: Text.ElideRight
                text: row.title
                color: row.separator ? Theme.textOff : (row.entryEnabled ? Theme.text : Theme.disabled)
                font.pixelSize: 24
                font.family: Theme.fontFamily
            }

            TapHandler {
                enabled: !row.separator
                onTapped: root.screen.activate(row.index, "S")
                onLongPressed: root.screen.activate(row.index, "B")
            }
        }
    }

    // Info pane: text and icon of the selected entry
    Rectangle {
        id: info

        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: root.isGrid ? 0 : parent.width * 0.28
        visible: !root.isGrid
        color: Theme.background

        Image {
            id: infoIcon
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.topMargin: 6
            width: Math.min(parent.width - 12, 160)
            height: source != "" ? width : 0
            fillMode: Image.PreserveAspectFit
            asynchronous: true
            source: root.screen ? root.screen.currentIcon : ""
        }
        Text {
            anchors.top: infoIcon.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 6
            wrapMode: Text.WordWrap
            text: root.screen ? root.screen.currentInfo : ""
            color: Theme.text
            font.pixelSize: 16
        }
    }

    GridView {
        id: grid

        anchors.fill: parent
        visible: root.isGrid
        clip: true
        model: root.isGrid ? root.entries : null
        readonly property int columns: root.screen ? root.screen.gridColumns : 4
        cellWidth: Math.floor(width / columns)
        cellHeight: Math.floor(height / Math.max(1, Math.ceil(count / columns)))
        currentIndex: root.screen ? root.screen.index : -1
        interactive: false

        delegate: Item {
            id: tile

            required property int index
            required property string title
            required property string icon
            required property bool entryEnabled

            width: grid.cellWidth
            height: grid.cellHeight

            Rectangle {
                anchors.fill: parent
                anchors.margins: 1
                color: tile.index === grid.currentIndex ? Theme.select : Theme.panel
                border.color: tap.pressed ? Theme.text : "transparent"
                opacity: tile.entryEnabled ? 1 : 0.45

                Image {
                    id: tileIcon
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    anchors.topMargin: 8
                    width: Math.min(parent.width, parent.height) * 0.5
                    height: width
                    fillMode: Image.PreserveAspectFit
                    source: tile.icon
                    sourceSize.width: width
                    sourceSize.height: height
                    asynchronous: true
                }
                Text {
                    anchors.top: tileIcon.bottom
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: 4
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    wrapMode: Text.WordWrap
                    text: tile.title
                    color: Theme.text
                    font.pixelSize: 18
                    font.family: Theme.fontFamily
                }
                TapHandler {
                    id: tap
                    onTapped: root.screen.activate(tile.index, "S")
                    onLongPressed: root.screen.activate(tile.index, "B")
                }
            }
        }
    }
}
