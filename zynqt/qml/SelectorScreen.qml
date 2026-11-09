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
                button: true
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
        anchors.margins: -Theme.listPadding
        visible: list.visible
        color: Theme.listBackground
    }

    ListView {
        id: list

        anchors.left: cats.right
        anchors.leftMargin: (cats.visible ? 2 : 0) + Theme.listPadding
        anchors.top: parent.top
        anchors.topMargin: Theme.listPadding
        anchors.bottom: parent.bottom
        anchors.right: info.left
        anchors.rightMargin: 2 + Theme.listPadding
        visible: !root.isGrid
        clip: true
        model: root.isGrid ? null : root.entries
        currentIndex: root.screen ? root.screen.index : -1
        spacing: Theme.listSpacing
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
            height: Theme.listRowHeight
            color: separator ? Theme.separator : (current ? Theme.select : Theme.panel)
            borderColor: separator ? "transparent" : Theme.frame
            button: true

            Label {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: Theme.listTextMargin
                elide: Text.ElideRight
                text: row.title
                color: row.separator ? Theme.separatorText : (row.current ? Theme.selectText
                                                        : (row.entryEnabled ? Theme.text : Theme.disabled))
                size: Theme.listTextSize
                title: true
            }

            TapHandler {
                enabled: !row.separator
                onTapped: root.screen.activate(row.index, "S")
                onLongPressed: root.screen.activate(row.index, "B")
            }
        }
    }

    // Info pane: text and icon of the selected entry (+<theme>/InfoPane.qml)
    InfoPane {
        id: info

        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: root.isGrid ? 0 : parent.width * Theme.infoWidth
        visible: !root.isGrid
        icon: root.screen ? root.screen.currentIcon : ""
        info: root.screen ? root.screen.currentInfo : ""
    }

    Rectangle {
        anchors.fill: parent
        visible: root.isGrid
        color: Theme.gridBackground
    }

    GridView {
        id: grid

        // gridSpacing: tiles with gaps, as zynthian_gui_selector_grid.update_geometry (the
        // spacing on the left and top, the cells tile + spacing); 0: cells fill the screen
        readonly property real sp: Theme.gridSpacing > 0 ? 2 * Math.floor(root.width * Theme.gridSpacing / columns) : 0
        anchors.fill: parent
        anchors.leftMargin: sp
        anchors.topMargin: sp
        visible: root.isGrid
        clip: true
        model: root.isGrid ? root.entries : null
        readonly property int columns: root.screen ? root.screen.gridColumns : 4
        cellWidth: sp > 0 ? 2 * Math.floor((root.width - sp) / (columns * 2)) : Math.floor(width / columns)
        cellHeight: sp > 0 ? 2 * Math.floor((root.height - sp) / (columns * 2))
                           : Math.floor(height / Math.max(1, Math.ceil(count / columns)))
        currentIndex: root.screen ? root.screen.index : -1
        interactive: false

        delegate: GridTile {
            required property int index
            required property string title
            required property string icon
            required property bool entryEnabled
            required property bool separator   // a placeholder cell: darkened, empty

            width: grid.cellWidth
            height: grid.cellHeight
            tileIndex: index
            tileTitle: title
            tileIcon: icon
            enabledEntry: entryEnabled
            placeholder: separator
            selected: index === grid.currentIndex
            spacing: grid.sp
            onActivated: (t) => root.screen.activate(index, t)
        }
    }
}
