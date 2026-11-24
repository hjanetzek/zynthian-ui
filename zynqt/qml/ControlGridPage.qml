// tk: a page of chain control's grid (ControlGrid, docs/qt-control-grid.md) around its four
// cells: a header with the page's title (and its section, the processor or "Chain", at the
// right), the selected page's header in the selection colour (as Tk's selected list row) and
// the page framed in frameActive; a processor without pages says so below its header. ControlGrid
// places it and the cells, and handles the header's touch; themes replace this file for another
// look (+<theme>/ControlGridPage.qml, same properties).
import QtQuick

Item {
    id: root

    property string title
    property string section
    property int sectionIndex: 0
    property bool selected: false
    property bool first: false         // the first page of its section
    property bool empty: false         // a processor without pages
    property color accent: Theme.select   // the section's colour
    property real headerHeight: 16
    readonly property int textSize: Math.max(Theme.tkPx(6), Math.round(headerHeight * 0.62))

    Rectangle {
        id: header
        width: parent.width
        height: root.headerHeight
        color: root.selected ? Theme.select : Theme.separator
        // the section's colour at the left
        Rectangle {
            width: Math.max(3, Math.round(root.headerHeight / 4))
            height: parent.height
            color: root.accent
            visible: !root.selected
        }
        Text {
            id: sectionText
            anchors.right: parent.right
            anchors.rightMargin: 4
            anchors.verticalCenter: parent.verticalCenter
            width: Math.min(implicitWidth, parent.width * 0.45)
            text: root.section
            elide: Text.ElideRight
            color: root.selected ? Theme.selectText : Theme.separatorText
            opacity: 0.75
            font.family: Theme.fontFamily
            font.pixelSize: Math.round(root.textSize * 0.85)
        }
        Text {
            anchors.left: parent.left
            anchors.leftMargin: Math.max(6, Math.round(root.headerHeight / 2))
            anchors.right: sectionText.left
            anchors.rightMargin: 4
            anchors.verticalCenter: parent.verticalCenter
            text: root.title
            elide: Text.ElideRight
            color: root.selected ? Theme.selectText : Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: root.textSize
        }
    }

    Text {
        visible: root.empty
        anchors.centerIn: parent
        anchors.verticalCenterOffset: root.headerHeight / 2
        width: parent.width - 8
        horizontalAlignment: Text.AlignHCenter
        text: "No controllers"
        elide: Text.ElideRight
        color: Theme.textOff
        font.family: Theme.fontFamily
        font.pixelSize: root.textSize
        z: 3
    }

    // The selected page (the encoders turn its controllers): framed above the cells
    Rectangle {
        anchors.fill: parent
        visible: root.selected
        color: "transparent"
        border.color: Theme.frameActive
        border.width: 2
        z: 3
    }
}
