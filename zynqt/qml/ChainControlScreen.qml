// Chain control as zynthian_gui_chain_control + zynthian_gui_control, for every theme (shared:
// layout, content and touch; themes give its parts their look: ChainNode, ControlPageRow,
// Controller, and the tokens sideChainBackground, controllerColumn, controllerGap). The page list
// (a Tk selector list) and the four controllers in a column of controllerColumn (tk: a quarter)
// of the screen width at the right; the side chain (zynthian_side_chain, a fifth of the width)
// only in select mode. The page's widget below the list (audio file, envelope, filter: half of
// it) or instead of it (the other widgets). The side chain's nodes other than processors open
// their screens (Tk shows them as subscreens in place).
import QtQuick

Rectangle {
    id: root

    readonly property var cc: zyn.chainControl
    readonly property bool chainShown: cc.selectMode && cc.isChain
    readonly property bool widgetHalf: ["audio_file", "envelope", "filter", "drawbar", "unsupported"].indexOf(cc.widgetType) >= 0

    color: Theme.background

    // Side chain (zynthian_side_chain): blocks coloured by kind, lines between them
    Rectangle {
        id: side
        x: 0
        width: root.chainShown ? Math.floor(0.2 * root.width) : 0
        height: root.height
        visible: root.chainShown
        color: Theme.sideChainBackground

        readonly property int blockWidth: 2 * Math.floor(0.45 * width)
        readonly property int blockHeight: Math.floor(0.12 * height)
        readonly property int vSpacing: 2 * Math.floor(blockHeight / 10)

        ListView {
            id: nodes
            anchors.fill: parent
            anchors.topMargin: Math.floor(side.vSpacing / 2)
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            model: root.cc.chainNodes
            currentIndex: root.cc.chainNode
            highlightMoveDuration: 0
            // Tk scrolls only to bring the selected node into view
            highlightFollowsCurrentItem: false
            onCurrentIndexChanged: Qt.callLater(() => positionViewAtIndex(currentIndex, ListView.Contain))
            onModelChanged: { positionViewAtBeginning(); Qt.callLater(() => positionViewAtIndex(currentIndex, ListView.Contain)) }

            delegate: Item {
                id: node
                required property int index
                required property var modelData
                readonly property bool selected: index === nodes.currentIndex
                width: nodes.width
                height: side.blockHeight + side.vSpacing

                ChainNode {
                    node: parent.modelData
                    selected: parent.selected
                    sideWidth: side.width
                    sideHeight: side.height
                    blockWidth: side.blockWidth
                    blockHeight: side.blockHeight
                    vSpacing: side.vSpacing
                }
                TapHandler {
                    longPressThreshold: 0.3
                    onTapped: root.cc.nodeTapped(node.index)
                    onLongPressed: root.cc.nodeLongPressed(node.index)
                }
            }
        }
    }

    // The control subscreen
    Item {
        id: sub
        x: side.visible ? side.width + 2 : 0
        width: root.width - x
        height: root.height

        // Controllers (zynthian_gui_control's sidebar: SHOW/HIDE_SIDEBAR)
        Column {
            id: controllers
            anchors.right: parent.right
            width: root.cc.sidebarShown ? Math.floor(Theme.controllerColumn * root.width) : 0
            visible: root.cc.sidebarShown
            height: parent.height
            spacing: 0
            Repeater {
                model: [root.cc.c0, root.cc.c1, root.cc.c2, root.cc.c3]
                Item {
                    required property var modelData
                    width: controllers.width
                    height: Math.floor(controllers.height / 4)
                    Controller {
                        width: parent.width
                        height: parent.height - Theme.controllerGap
                        ctrl: parent.modelData
                        dimmed: root.cc.selectMode
                    }
                }
            }
        }

        // Page list (a Tk selector list)
        Rectangle {
            id: listArea
            x: 0
            width: parent.width - controllers.width - (controllers.visible ? 1 : 0)
            height: root.widgetHalf ? Math.floor(parent.height / 2) : parent.height
            visible: root.cc.widgetType === "" || root.widgetHalf
            color: Theme.listBackground

            ListView {
                id: pages
                anchors.fill: parent
                anchors.margins: Theme.listPadding
                clip: true
                model: root.cc.pageModel
                currentIndex: root.cc.page
                boundsBehavior: Flickable.StopAtBounds
                highlightFollowsCurrentItem: false
                onCurrentIndexChanged: Qt.callLater(() => positionViewAtIndex(currentIndex, ListView.Contain))
                onCountChanged: { positionViewAtBeginning(); Qt.callLater(() => positionViewAtIndex(currentIndex, ListView.Contain)) }

                spacing: Theme.listSpacing

                delegate: Item {
                    id: row
                    required property int index
                    required property string title
                    required property bool separator
                    required property bool header   // a processor without pages: selectable
                    width: pages.width
                    height: rowLook.height
                    ControlPageRow {
                        id: rowLook
                        width: parent.width
                        current: row.index === pages.currentIndex
                        separator: row.separator
                        header: row.header
                        // Tk's section rows: "> Mixer"
                        text: row.separator || row.header ? "> " + row.title : row.title
                    }
                    TapHandler {
                        enabled: !row.separator
                        onTapped: root.cc.pageTapped(row.index)
                    }
                }
            }
        }

        ControlWidget {
            id: widget
            cc: root.cc
            // Tk grids the widget's canvas over the list's full width (the curve's grid 10 px in)
            x: 0
            y: root.widgetHalf ? listArea.height : 0
            width: listArea.width
            height: parent.height - y
        }

        ControlOverlays {
            anchors.fill: parent
            cc: root.cc
            area: listArea
        }
    }
}
