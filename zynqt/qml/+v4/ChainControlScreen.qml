// v4: chain control as tk's (zynthian_gui_chain_control + zynthian_gui_control), in Tk's V4
// layout: the four controllers next to their knobs, two in a column on each side (23 % of the
// screen width each, half the height each: slot i at ctrl_pos[i], knob i turns it: 0 top left,
// 1 bottom left, 2 top right, 3 bottom right), the page list in the middle column; the side chain
// (a fifth of the width) left of them only in select mode. The page's widget below the list
// (audio file, envelope, filter: half of it) or instead of it, in the middle column.
import QtQuick
import ".."

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
        color: Theme.panel

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

                Rectangle {
                    id: block
                    x: Math.floor((side.width - side.blockWidth) / 2)
                    width: side.blockWidth
                    height: side.blockHeight
                    color: {
                        switch (node.modelData.kind) {
                        case "midi": return Theme.nodeMidi
                        case "synth": return Theme.nodeSynth
                        case "audio": return Theme.nodeAudio
                        case "special": return Theme.nodeSpecial
                        }
                        return Theme.nodeOther
                    }
                    border.width: node.selected ? 2 : 0
                    border.color: zyn.movingProcessor ? "#ffff00" : "#ffffff"
                    Text {
                        anchors.centerIn: parent
                        width: Math.floor(0.9 * side.blockWidth)
                        height: Math.floor(0.9 * side.blockHeight)
                        text: node.modelData.title
                        color: node.modelData.bypassed ? Theme.textBypassed : "#ffffff"
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.tkPx(Math.floor(0.026 * side.height))
                        minimumPixelSize: Theme.tkPx(6)
                        fontSizeMode: Text.VerticalFit
                        wrapMode: Text.WordWrap
                        elide: Text.ElideRight
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                // Lines to the next node (4 px, #AAAAAA)
                Repeater {
                    model: node.modelData.link === "parallel" ? [1 / 8, 7 / 8]
                         : node.modelData.link !== "" ? [1 / 2] : []
                    Rectangle {
                        required property real modelData
                        x: block.x + Math.floor(block.width * modelData) - 2
                        y: block.height
                        width: 4
                        height: node.modelData.link === "half" ? Math.floor(side.vSpacing / 2) : side.vSpacing
                        color: Theme.connector
                    }
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

        // Controllers (zynthian_gui_control's sidebar: SHOW/HIDE_SIDEBAR): Tk's ctrl_width 0.23 of
        // the screen width, a 1 px gap below each and beside the list
        readonly property int ctrlWidth: root.cc.sidebarShown ? Math.floor(0.23 * Theme.screenWidth - 1) : 0
        Repeater {
            model: [root.cc.c0, root.cc.c1, root.cc.c2, root.cc.c3]
            Controller {
                required property var modelData
                required property int index
                visible: root.cc.sidebarShown
                x: index < 2 ? 0 : sub.width - sub.ctrlWidth
                y: index % 2 === 0 ? 0 : Math.floor(sub.height / 2)
                width: sub.ctrlWidth
                height: Math.floor(sub.height / 2) - 1
                ctrl: modelData
                dimmed: root.cc.selectMode
            }
        }

        // Page list (a Tk selector list)
        Rectangle {
            id: listArea
            x: sub.ctrlWidth > 0 ? sub.ctrlWidth + 1 : 0
            width: parent.width - 2 * x
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

                delegate: Rectangle {
                    id: row
                    required property int index
                    required property string title
                    required property bool separator
                    required property bool header   // a processor without pages: selectable
                    readonly property bool current: index === pages.currentIndex
                    readonly property bool sectionLook: separator || (header && !current)
                    width: pages.width
                    height: Theme.listRowHeight
                    color: sectionLook ? Theme.separator : (current ? Theme.select : Theme.listBackground)
                    Label {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.leftMargin: Theme.listTextMargin
                        elide: Text.ElideRight
                        text: row.separator || row.header ? "> " + row.title : row.title
                        color: row.sectionLook ? Theme.separatorText : Theme.text
                        size: Theme.listTextSize
                        title: true
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
            x: listArea.x
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
