// Chain control's grid layouts (ZYNTHIAN_QT_CONTROL_LAYOUT grid4x6 / grid8x6,
// docs/qt-control-grid.md), shared by every theme with the grid (looks: ControlCell,
// ControlGridPage, ControlPageRow and the controlGrid* tokens). Six rows of pages, one page (4x6)
// or two (8x6) a row, each page its four controllers in order under a header; the selected page
// (the one the encoders turn) framed. Left of it the page list (when there is room and the side
// chain isn't shown: select mode), the rows the grid shows marked; right of it the window's place
// in the pages (a tap above / below scrolls by a screen, a drag moves it). Cells and pages are
// created once per layout: only their content changes.
import QtQuick

Item {
    id: grid

    property var cc: zyn.chainControl
    readonly property var gm: cc.gridModel
    readonly property var cells: gm.cells
    readonly property var blocks: gm.blocks
    readonly property int columns: gm.columns
    readonly property int rows: gm.rows
    readonly property int perRow: gm.pagesPerRow

    readonly property real gap: Theme.controlGridGap
    readonly property real scrollWidth: Math.max(8, Math.round(width * 0.012))
    readonly property bool listShown: cc.sidebarShown && !cc.selectMode
        && (width * (1 - Theme.controlGridList) - scrollWidth) / columns >= Theme.controlCellMinWidth
    readonly property real listWidth: listShown ? Math.floor(Theme.controlGridList * width) : 0

    function accent(sectionIndex) {
        const c = Theme.controlGridColors
        return c.length ? c[sectionIndex % c.length] : Theme.select
    }

    // Page list (as the v5 layout's), the grid's rows marked at the left
    Rectangle {
        id: listArea
        visible: grid.listShown
        width: grid.listWidth
        height: parent.height
        color: Theme.listBackground

        ListView {
            id: pages
            anchors.fill: parent
            anchors.margins: Theme.listPadding
            clip: true
            model: grid.listShown ? grid.cc.pageModel : null
            currentIndex: grid.cc.page
            boundsBehavior: Flickable.StopAtBounds
            highlightFollowsCurrentItem: false
            spacing: Theme.listSpacing
            onCurrentIndexChanged: Qt.callLater(() => positionViewAtIndex(currentIndex, ListView.Contain))
            onCountChanged: Qt.callLater(() => positionViewAtIndex(currentIndex, ListView.Contain))

            delegate: Item {
                id: row
                required property int index
                required property string title
                required property bool separator
                required property bool header
                width: pages.width
                height: rowLook.height
                ControlPageRow {
                    id: rowLook
                    width: parent.width
                    current: row.index === pages.currentIndex
                    separator: row.separator
                    header: row.header
                    text: row.separator || row.header ? "> " + row.title : row.title
                }
                Rectangle {
                    visible: row.index >= grid.gm.firstEntry && row.index <= grid.gm.lastEntry
                    width: Math.max(3, Math.round(Theme.listRowHeight / 10))
                    height: parent.height + pages.spacing
                    color: Theme.frameActive
                }
                TapHandler {
                    enabled: !row.separator
                    onTapped: grid.cc.pageTapped(row.index)
                }
            }
        }
    }

    // The pages and their cells
    Item {
        id: area
        x: grid.listShown ? grid.listWidth + 1 : 0
        width: grid.width - x - grid.scrollWidth - grid.gap
        height: grid.height

        readonly property real rowHeight: Math.floor((height + grid.gap) / grid.rows)
        readonly property real pageWidth: Math.floor((width + grid.gap) / grid.perRow)
        readonly property real headerHeight: Math.max(12, Math.min(28, Math.round(rowHeight * 0.2)))

        WheelHandler {
            // the wheel over headers and gaps scrolls (over a cell it changes the cell)
            onWheel: event => grid.gm.scrollRows(event.angleDelta.y > 0 ? -1 : 1)
        }

        Repeater {
            model: grid.rows * grid.perRow
            Item {
                id: page
                required property int index
                readonly property int row: Math.floor(index / grid.perRow)
                readonly property int part: index % grid.perRow
                readonly property var info: grid.blocks[index] || ({})
                x: part * area.pageWidth
                y: row * area.rowHeight
                width: area.pageWidth - grid.gap
                height: area.rowHeight - grid.gap

                ControlGridPage {
                    anchors.fill: parent
                    z: 1
                    visible: page.info.valid === true
                    title: page.info.title || ""
                    section: page.info.section || ""
                    sectionIndex: page.info.sectionIndex || 0
                    selected: page.info.selected === true
                    first: page.info.first === true
                    empty: page.info.empty === true
                    accent: grid.accent(sectionIndex)
                    headerHeight: area.headerHeight
                }
                Item {
                    width: parent.width
                    height: area.headerHeight
                    TapHandler { onTapped: grid.gm.tapPage(page.index) }
                }
                Repeater {
                    model: 4
                    Item {
                        id: slot
                        required property int index
                        readonly property var ctrl: grid.cells[page.row * grid.columns + page.part * 4 + index]
                        x: index * Math.floor((page.width + grid.gap) / 4)
                        y: area.headerHeight + grid.gap
                        width: Math.floor((page.width + grid.gap) / 4) - grid.gap
                        height: page.height - y
                        ControlCell {
                            anchors.fill: parent
                            ctrl: slot.ctrl
                            dimmed: grid.cc.selectMode
                            accent: grid.accent(slot.ctrl ? slot.ctrl.sectionIndex : 0)
                        }
                        ControlCellTouch { ctrl: slot.ctrl }
                    }
                }
            }
        }

        // The selected page's widget (envelope, filter, waveform, plugin widgets, ...) over its
        // header and cells for controlGridWidgetMs after a change of one of its values or its
        // selection (ChainControl.gridWidgetPoke), the changed value on top. Not interactive
        // (enabled false): touch goes to the cells beneath, so a drag keeps changing the value.
        Item {
            id: widgetOverlay
            readonly property int row: grid.gm.selectedRow
            readonly property int part: grid.gm.selectedPart
            readonly property real textSize: Math.max(12, Math.min(30, height * 0.22)) / Theme.fontScale
            property string name
            property string value
            property bool used: false
            x: part * area.pageWidth
            y: row * area.rowHeight
            width: area.pageWidth - grid.gap
            height: area.rowHeight - grid.gap
            z: 5
            enabled: false
            opacity: 0
            visible: opacity > 0 && row >= 0 && grid.cc.widgetType !== ""
            Behavior on opacity { NumberAnimation { duration: 200 } }

            function poke(n, v) {
                name = n
                value = v
                used = true
                opacity = 1
                hideTimer.restart()
            }
            Timer {
                id: hideTimer
                interval: Theme.controlGridWidgetMs
                onTriggered: widgetOverlay.opacity = 0
            }
            Connections {
                target: grid.cc
                function onGridWidgetPoke(n, v) { widgetOverlay.poke(n, v) }
            }

            Rectangle {
                anchors.fill: parent
                color: Theme.widgetBackground
                border.color: Theme.frameActive
                border.width: 2
            }
            // created when first needed; then only the views shown (lazy)
            Loader {
                anchors.fill: parent
                anchors.margins: 2
                active: widgetOverlay.used
                sourceComponent: Component { ControlWidget { cc: grid.cc; lazy: true } }
            }
            Rectangle {
                visible: widgetOverlay.name !== ""
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 4
                width: valueRow.width + 16
                height: valueRow.height + 6
                color: Qt.rgba(Theme.background.r, Theme.background.g, Theme.background.b, 0.75)
                radius: Theme.panelRadius > 0 ? height / 2 : 0
                Row {
                    id: valueRow
                    anchors.centerIn: parent
                    spacing: 10
                    Label {
                        anchors.baseline: valueText.baseline
                        width: Math.min(implicitWidth, widgetOverlay.width * 0.5)
                        elide: Text.ElideRight
                        text: widgetOverlay.name
                        color: Theme.textOff
                        size: widgetOverlay.textSize * 0.75
                    }
                    Label {
                        id: valueText
                        width: Math.min(implicitWidth, widgetOverlay.width * 0.4)
                        elide: Text.ElideRight
                        text: widgetOverlay.value
                        color: Theme.text
                        size: widgetOverlay.textSize
                        title: true
                        body: true
                    }
                }
            }
        }
    }

    // The window's place in the pages
    Item {
        id: scroll
        anchors.right: parent.right
        width: grid.scrollWidth
        height: parent.height
        visible: grid.gm.totalRows > grid.rows
        readonly property real thumbY: grid.gm.totalRows > 0 ? height * grid.gm.firstRow / grid.gm.totalRows : 0
        readonly property real thumbHeight: grid.gm.totalRows > 0 ? Math.max(12, height * grid.rows / grid.gm.totalRows) : height

        Rectangle {
            anchors.fill: parent
            color: Theme.panelHighlight
        }
        Rectangle {
            y: scroll.thumbY
            width: parent.width
            height: scroll.thumbHeight
            color: Theme.textOff
        }
        TapHandler {
            onTapped: (point) => {
                if (point.position.y < scroll.thumbY)
                    grid.gm.scrollRows(-grid.rows)
                else if (point.position.y > scroll.thumbY + scroll.thumbHeight)
                    grid.gm.scrollRows(grid.rows)
            }
        }
        DragHandler {
            target: null
            xAxis.enabled: Theme.uiSideways
            yAxis.enabled: !Theme.uiSideways
            property int startRow: 0
            onActiveChanged: if (active) startRow = grid.gm.firstRow
            onTranslationChanged: {
                const d = Theme.localDrag(scroll, centroid).y
                grid.gm.scrollTo(startRow + Math.round(d * grid.gm.totalRows / Math.max(1, scroll.height)))
            }
        }
    }
}
