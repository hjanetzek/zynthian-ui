// classic (and galactica, enterprise): a page of chain control's grid (ControlGrid,
// docs/qt-control-grid.md) around its four cells: the header (the page's title, its section at the
// right) on the section colour's line, or filled in it (controlGridHeaderFilled: enterprise's
// pills with dark text); the selected page's header in the selection colour and the page framed
// in frameActive; a processor without pages says so. Same properties as tk's ControlGridPage.
import QtQuick
import ".."

Item {
    id: root

    property string title
    property string section
    property int sectionIndex: 0
    property bool selected: false
    property bool first: false
    property bool empty: false
    property color accent: Theme.select
    property real headerHeight: 16
    readonly property real textSize: Math.max(8, headerHeight * 0.66) / Theme.fontScale
    readonly property bool filled: Theme.controlGridHeaderFilled

    Panel {
        id: header
        width: parent.width
        height: root.headerHeight
        button: true
        borderWidth: 0
        cut: Math.min(Theme.cut, height / 3)
        color: root.selected ? Theme.select : (root.filled ? root.accent : "transparent")

        // the section's colour as a line under the header (not filled)
        Rectangle {
            visible: !root.filled && !root.selected
            anchors.bottom: parent.bottom
            width: parent.width
            height: Math.max(2, Math.round(root.headerHeight / 8))
            color: root.accent
        }
        Label {
            id: sectionText
            anchors.right: parent.right
            anchors.rightMargin: Math.max(4, header._r / 2 + 2)
            anchors.verticalCenter: parent.verticalCenter
            width: Math.min(implicitWidth, parent.width * 0.45)
            text: root.section
            elide: Text.ElideRight
            color: root.selected ? Theme.selectText : (root.filled ? Theme.selectText : Theme.textOff)
            opacity: 0.8
            size: root.textSize * 0.85
        }
        Label {
            anchors.left: parent.left
            anchors.leftMargin: Math.max(4, header._r / 2 + 2, header._c)
            anchors.right: sectionText.left
            anchors.rightMargin: 4
            anchors.verticalCenter: parent.verticalCenter
            text: root.title
            elide: Text.ElideRight
            color: root.selected || root.filled ? Theme.selectText : Theme.text
            size: root.textSize
            title: true
        }
    }

    Label {
        visible: root.empty
        anchors.centerIn: parent
        anchors.verticalCenterOffset: root.headerHeight / 2
        width: parent.width - 8
        horizontalAlignment: Text.AlignHCenter
        text: "No controllers"
        elide: Text.ElideRight
        color: Theme.textOff
        size: root.textSize
    }

    // The selected page (the encoders turn its controllers): framed above the cells
    Panel {
        anchors.fill: parent
        anchors.margins: -2
        visible: root.selected
        color: "transparent"
        borderColor: Theme.frameActive
        borderWidth: 2
        cut: Theme.cut
    }
}
