// tk: a row of chain control's page list as a Tk selector list row: section rows ("> Mixer", a
// processor without pages while not selected) in the section colours, the current page in the
// selection colour. The screen (ChainControlScreen) gives it its text and handles its touch;
// themes replace this file for another look (+<theme>/ControlPageRow.qml, same properties).
import QtQuick

Rectangle {
    id: row

    property string text
    property bool current: false
    property bool separator: false
    property bool header: false      // a processor without pages (selectable)
    readonly property bool sectionLook: separator || (header && !current)

    height: Theme.listRowHeight
    color: sectionLook ? Theme.separator : (current ? Theme.select : Theme.listBackground)
    Label {
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: Theme.listTextMargin
        elide: Text.ElideRight
        text: row.text
        color: row.sectionLook ? Theme.separatorText : Theme.text
        size: Theme.listTextSize
        title: true
    }
}
