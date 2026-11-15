import QtQuick
import ".."

// The engine screen's categories as a second list on the left of the selector, as the Tk engine
// screen's listbox2: the selected one inverted. Themes replace it (+<theme>/SelectorCategories.qml).
Rectangle {
    id: cats

    property var screen: null

    color: Theme.listBackground

    ListView {
        id: catList
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        model: cats.screen ? cats.screen.categories : []
        currentIndex: cats.screen ? cats.screen.categoryIndex : 0
        onCurrentIndexChanged: positionViewAtIndex(currentIndex, ListView.Contain)
        delegate: Panel {
            required property int index
            required property string modelData
            width: catList.width
            height: 40
            button: true
            color: index === catList.currentIndex ? Theme.text : Theme.listBackground
            borderColor: "transparent"
            Label {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: 10
                elide: Text.ElideRight
                text: modelData
                color: index === catList.currentIndex ? Theme.listBackground : Theme.text
                size: 20
                title: true
            }
            TapHandler { onTapped: cats.screen.setCategory(index) }
        }
    }
}
