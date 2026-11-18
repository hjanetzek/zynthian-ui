// Classic: a row of chain control's page list as a plate (section rows in the section colours,
// the current page in the selection colour). Look only: the screen (ChainControlScreen, shared)
// gives it its text and handles its touch.
import QtQuick
import ".."

Panel {
    id: row

    property string text
    property bool current: false
    property bool separator: false
    property bool header: false
    readonly property bool sectionLook: separator || (header && !current)

    height: 44
    color: sectionLook ? Theme.separator : (current ? Theme.select : Theme.panel)
    borderColor: sectionLook ? "transparent" : Theme.frame
    button: true
    Label {
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 10
        elide: Text.ElideRight
        text: row.text
        color: row.sectionLook ? Theme.separatorText : (row.current ? Theme.selectText : Theme.text)
        size: 22
        title: true
    }
}
