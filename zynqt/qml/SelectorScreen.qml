// A selector screen (zynqt.screens): a list with an info pane (and a category list on the left
// if the screen has categories), or a grid of tiles. Tap selects and activates, long press is a bold press.
import QtQuick
import QtQuick.Effects

Item {
    id: root

    property var screen: null
    readonly property bool isGrid: screen !== null && screen.viewKind === "grid"
    readonly property var entries: screen ? screen.entryModel : null

    // Categories (engine groups) as a second list on the left (+<theme>/SelectorCategories.qml)
    SelectorCategories {
        id: cats

        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: visible ? Math.round(parent.width * Theme.categoryWidth) : 0
        visible: !root.isGrid && root.screen !== null && root.screen.categories.length > 1
        screen: visible ? root.screen : null
    }

    // List background: grey also below the last entry
    Rectangle {
        anchors.left: list.left
        anchors.right: list.right
        anchors.top: list.top
        anchors.bottom: parent.bottom
        anchors.leftMargin: -Theme.listPadding
        anchors.rightMargin: -Theme.listPadding
        anchors.topMargin: -Theme.listPadding
        visible: list.visible
        color: Theme.listBackground
    }

    ListView {
        id: list

        anchors.left: cats.right
        anchors.leftMargin: (cats.visible ? 2 : 0) + Theme.listPadding
        anchors.top: parent.top
        anchors.topMargin: Theme.listPadding
        anchors.bottom: statusLine.visible ? statusLine.top : parent.bottom
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

    // Status under the list (zynthian_gui_zs3's waiting label: centred, 0.85 F, color_ml)
    Label {
        id: statusLine
        anchors.left: list.left
        anchors.right: list.right
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 2
        visible: !root.isGrid && text !== ""
        text: root.screen && root.screen.statusLine !== undefined ? root.screen.statusLine : ""
        horizontalAlignment: Text.AlignHCenter
        elide: Text.ElideRight
        title: true
        size: Theme.listTextSize * 0.85
        color: Theme.statusLine
    }

    // Info pane: text and icon of the selected entry (+<theme>/InfoPane.qml)
    InfoPane {
        id: info

        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: controls.top
        width: root.isGrid ? 0 : parent.width * (cats.visible ? Theme.categoryInfoWidth : Theme.infoWidth)
        visible: !root.isGrid
        icon: root.screen ? root.screen.currentIcon : ""
        info: root.screen ? root.screen.currentInfo : ""
        // Engines: quality stars and complexity gears (-1: none)
        quality: root.screen && root.screen.currentQuality !== undefined ? root.screen.currentQuality : -1
        complexity: root.screen && root.screen.currentComplexity !== undefined ? root.screen.currentComplexity : -1
    }
    // Controller widgets under the info pane (+<theme>/SelectorControls.qml; none by default)
    SelectorControls {
        id: controls
        screen: root.isGrid ? null : root.screen
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        width: info.width
        height: implicitHeight
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
        topMargin: sp
        visible: root.isGrid
        clip: true
        model: root.isGrid ? root.entries : null
        readonly property int columns: {
            const name = root.screen ? (root.screen.screenName || "") : ""
            const c = name === "main_menu" ? Theme.mainMenuColumns : (name === "add_chain" ? Theme.addChainColumns : 0)
            return c > 0 ? c : (root.screen ? root.screen.gridColumns : 4)
        }
        function reportLayout() { if (root.isGrid) root.screen.setGridLayout(columns, Theme.gridPlaceholders) }
        onColumnsChanged: reportLayout()
        Connections {
            target: root
            function onScreenChanged() { grid.reportLayout() }
        }
        Component.onCompleted: { reportLayout(); Qt.callLater(showCurrent) }
        cellWidth: sp > 0 ? 2 * Math.floor((root.width - sp) / (columns * 2)) : Math.floor(width / columns)
        cellHeight: sp > 0 ? 2 * Math.floor((root.height - sp) / (columns * 2))
                           : Math.floor(height / Math.max(1, Math.ceil(count / columns)))
        currentIndex: root.screen ? root.screen.index : -1
        // More rows than fit (tk: as many rows shown as columns, as Tk; other aspect ratios than
        // 5:3): the grid scrolls as Tk's canvas (drag, wheel) and keeps the selection in view
        interactive: contentHeight + topMargin > height
        boundsBehavior: Flickable.StopAtBounds
        // the selected tile into view (Tk's _draw_selection), the top spacing shown on the first row
        function showCurrent() {
            if (currentIndex < 0 || count === 0 || cellHeight <= 0)
                return
            forceLayout()
            if (currentIndex < columns)
                contentY = -topMargin
            else
                positionViewAtIndex(currentIndex, GridView.Contain)
        }
        onCurrentIndexChanged: showCurrent()
        // also once the cells have their size and the entries are there (a screen shown again
        // with a selection further down)
        onCountChanged: Qt.callLater(showCurrent)
        onCellHeightChanged: Qt.callLater(showCurrent)

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
