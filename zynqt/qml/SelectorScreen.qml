// A selector screen (zynqt.screens): a list with an info pane (and a category list on the left
// if the screen has categories), or a grid of tiles. Tap selects and activates, long press is a bold press.
import QtQuick
import QtQuick.Effects

Item {
    id: root

    property var screen: null
    readonly property bool isGrid: screen !== null && screen.viewKind === "grid"
    readonly property var entries: screen ? screen.entryModel : null

    // Categories (engine groups) as a second list on the left, as the Tk engine screen's
    // listbox2: the selected one inverted
    Rectangle {
        id: cats

        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: visible ? Math.round(parent.width * 0.2) : 0
        visible: !root.isGrid && root.screen !== null && root.screen.categories.length > 1
        color: Theme.listBackground

        ListView {
            id: catList
            anchors.fill: parent
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            model: root.screen ? root.screen.categories : []
            currentIndex: root.screen ? root.screen.categoryIndex : 0
            onCurrentIndexChanged: positionViewAtIndex(currentIndex, ListView.Contain)
            delegate: Panel {
                required property int index
                required property string modelData
                width: catList.width
                height: 40
                color: index === catList.currentIndex ? Theme.text : Theme.listBackground
                borderColor: "transparent"
                Label {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.leftMargin: 10
                    elide: Text.ElideRight
                    text: modelData
                    color: index === catList.currentIndex ? Theme.listBackground : Theme.text
                    size: 20
                    title: true
                }
                TapHandler { onTapped: root.screen.setCategory(index) }
            }
        }
    }

    // List background: grey also below the last entry
    Rectangle {
        anchors.fill: list
        visible: list.visible
        color: Theme.listBackground
    }

    ListView {
        id: list

        anchors.left: cats.right
        anchors.leftMargin: cats.visible ? 2 : 0
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.right: info.left
        anchors.rightMargin: 2
        visible: !root.isGrid
        clip: true
        model: root.isGrid ? null : root.entries
        currentIndex: root.screen ? root.screen.index : -1
        spacing: Theme.isGalactica ? 2 : 0
        boundsBehavior: Flickable.StopAtBounds
        highlightMoveDuration: 0
        onCurrentIndexChanged: positionViewAtIndex(currentIndex, ListView.Contain)

        delegate: Panel {
            id: row

            required property int index
            required property string title
            required property bool separator
            required property bool entryEnabled
            readonly property bool current: index === list.currentIndex

            width: list.width
            height: 44
            color: separator ? Theme.panelHighlight : (current ? Theme.select : Theme.panel)
            borderColor: separator ? "transparent" : Theme.frame

            Label {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: 10
                elide: Text.ElideRight
                text: row.title
                color: row.separator ? Theme.textOff : (row.current ? Theme.selectText
                                                        : (row.entryEnabled ? Theme.text : Theme.disabled))
                size: 24
                title: true
            }

            TapHandler {
                enabled: !row.separator
                onTapped: root.screen.activate(row.index, "S")
                onLongPressed: root.screen.activate(row.index, "B")
            }
        }
    }

    // Info pane: text and icon of the selected entry
    Panel {
        id: info

        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: root.isGrid ? 0 : parent.width * 0.28
        visible: !root.isGrid
        color: Theme.isGalactica ? Theme.panelHighlight : Theme.background
        cut: Theme.cutLarge

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
            // Galactica: icons (white line art) in the console amber
            layer.enabled: Theme.isGalactica
            layer.effect: MultiEffect { colorization: 1.0; colorizationColor: Theme.text }
        }
        Label {
            anchors.top: infoIcon.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 6
            wrapMode: Text.WordWrap
            text: root.screen ? root.screen.currentInfo : ""
            color: Theme.text
            body: true
            size: 16
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
            required property bool separator   // a placeholder cell: darkened, empty

            width: grid.cellWidth
            height: grid.cellHeight

            Panel {
                anchors.fill: parent
                anchors.margins: Theme.isGalactica ? 3 : 1
                visible: tile.separator
                color: Theme.panelHighlight
                cut: Theme.cutLarge
            }
            Panel {
                anchors.fill: parent
                anchors.margins: Theme.isGalactica ? 3 : 1
                visible: !tile.separator
                color: tile.index === grid.currentIndex ? Theme.select : Theme.panel
                borderColor: tap.pressed ? Theme.frameActive : Theme.frame
                borderWidth: tap.pressed ? Math.max(1, Theme.frameWidth) : Theme.frameWidth
                cut: Theme.cutLarge
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
                    layer.enabled: Theme.isGalactica
                    layer.effect: MultiEffect {
                        colorization: 1.0
                        colorizationColor: tile.index === grid.currentIndex ? Theme.selectText : Theme.text
                    }
                }
                Label {
                    anchors.top: tileIcon.bottom
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: 4
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    wrapMode: Text.WordWrap
                    text: tile.title
                    color: tile.index === grid.currentIndex ? Theme.selectText : Theme.text
                    size: 18
                    title: true
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
