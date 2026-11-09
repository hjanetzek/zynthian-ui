// The top bar's title as Tk's (zynthian_gui_base.dscroll_select_path): a title wider than its
// space scrolls back and forth, 2 px every 50 ms, resting 1 s at each end; a new title starts
// at the left again. Fills its space vertically, the text centred (plus verticalOffset).
import QtQuick

Item {
    id: root
    property string text
    property color color: Theme.text
    property real size: Theme.titleSize
    property bool title: true
    property real verticalOffset: 0

    readonly property real overflow: label.implicitWidth - width
    property real offset: 0
    property int dir: 2

    clip: true
    onTextChanged: { offset = 0; dir = 2; scroller.interval = 50; scroller.restart() }
    onOverflowChanged: if (overflow <= 0) offset = 0

    Label {
        id: label
        x: -root.offset
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: root.verticalOffset
        text: root.text
        color: root.color
        size: root.size
        title: root.title
    }

    Timer {
        id: scroller
        running: root.visible && root.overflow > 0 && root.width > 0
        repeat: true
        interval: 50
        onTriggered: {
            root.offset += root.dir
            interval = 50
            if (root.offset > root.overflow) {
                root.dir = -2
                interval = 1000
            } else if (root.offset <= 0) {
                root.dir = 2
                interval = 1000
            }
        }
        onRunningChanged: if (!running) interval = 50
    }
}
