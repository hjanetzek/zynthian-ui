import QtQuick
import ".."

// tk: zynthian_gui_engine's listbox2: a Tk listbox (7 px border, list font and rows), the
// selected category inverted (panel text colour as background)
Rectangle {
    id: cats

    property var screen: null

    color: Theme.listBackground

    ListView {
        id: catList
        anchors.fill: parent
        anchors.margins: Theme.listPadding
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        model: cats.screen ? cats.screen.categories : []
        currentIndex: cats.screen ? cats.screen.categoryIndex : 0
        onCurrentIndexChanged: positionViewAtIndex(currentIndex, ListView.Contain)
        delegate: Rectangle {
            required property int index
            required property string modelData
            readonly property bool current: index === catList.currentIndex
            width: catList.width
            height: Theme.listRowHeight
            color: current ? Theme.text : Theme.listBackground
            Label {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: Theme.listTextMargin
                elide: Text.ElideRight
                text: parent.modelData
                color: parent.current ? Theme.listBackground : Theme.text
                size: Theme.listTextSize
                title: true
            }
            TapHandler { onTapped: cats.screen.setCategory(parent.index) }
        }
    }
}
