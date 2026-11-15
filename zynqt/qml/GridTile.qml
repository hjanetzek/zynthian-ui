import QtQuick

// Tk's grid node (zynthian_gui_selector_grid._draw_node): a grey block, the icon at its left
// edge (block height - spacing / 2), the title centred at 2/3 of the width in 0.06 x the block
// width points; the selected one outlined yellow. No placeholder cells.
Item {
    id: tile

    property int tileIndex
    property string tileTitle
    property string tileIcon
    property bool enabledEntry: true
    property bool placeholder: false
    property bool selected: false
    property real spacing: 0
    signal activated(string t)

    readonly property real bw: width - spacing
    readonly property real bh: height - spacing

    Rectangle {
        visible: !tile.placeholder
        width: tile.bw
        height: tile.bh
        color: tile.enabledEntry ? "#666666" : "#444444"
        border.color: tile.selected ? "#ffff00" : "transparent"
        border.width: tile.selected ? 2 : 0

        Image {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            width: tile.bh - Math.floor(0.5 * tile.spacing)
            height: width
            fillMode: Image.PreserveAspectFit
            source: tile.tileIcon
            sourceSize.width: width
            sourceSize.height: height
            asynchronous: true
        }
        Label {
            x: 2 * tile.bw / 3 - width / 2
            anchors.verticalCenter: parent.verticalCenter
            // Tk wraps at BLOCK_WIDTH // 2; Qt's Audiowide lines run a few px wider at the same
            // size, so a little slack keeps Tk's line breaks ("Start Audio / Recording")
            width: Math.floor(tile.bw / 2) + 6
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            text: tile.tileTitle
            color: tile.enabledEntry ? "#ffffff" : "#aaaaaa"
            size: Theme.tkPx(Math.floor(0.06 * tile.bw))
            title: true
        }
        TapHandler {
            onTapped: tile.activated("S")
            onLongPressed: tile.activated("B")
        }
    }
}
