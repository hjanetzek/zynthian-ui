import QtQuick
import ".."

// Tk: the icon in a square as wide as the pane (zynthian_gui_selector's info canvas), the text
// below it
Rectangle {
    id: pane
    property string icon
    property string info

    color: Theme.infoBackground

    Item {
        id: iconBox
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: width
        Image {
            anchors.centerIn: parent
            width: parent.width
            height: width
            fillMode: Image.PreserveAspectFit
            asynchronous: true
            source: pane.icon
        }
    }
    Label {
        anchors.top: iconBox.bottom
        anchors.topMargin: -8
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 4
        anchors.rightMargin: 4
        wrapMode: Text.WordWrap
        text: pane.info
        color: Theme.text
        body: true
        size: Theme.infoTextSize
        lineHeight: 0.84
    }
}
