// Chain control's overlays, centred over area (the page list): the MIDI learn banner, the keys
// moving a processor
import QtQuick

Item {
    id: root
    property var cc: zyn.chainControl
    property Item area: root
    z: 10

    // MIDI learn in progress: what to do, and a button to stop (as BACK)
    Panel {
        x: root.area.x + (root.area.width - width) / 2
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 20
        width: Math.min(root.area.width - 16, learnLabel.implicitWidth + stopLearn.width + 48)
        height: 64
        radius: 6
        z: 10
        visible: root.cc.learnText !== ""
        color: Theme.keyBackground
        borderColor: Theme.bindGlobal
        borderWidth: 2
        cut: Theme.cutLarge
        Label {
            id: learnLabel
            anchors.left: parent.left
            anchors.right: stopLearn.left
            anchors.verticalCenter: parent.verticalCenter
            anchors.margins: 16
            text: root.cc.learnText
            color: Theme.text
            wrapMode: Text.WordWrap
            body: true
            size: 18
        }
        MoveKey {
            id: stopLearn
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.rightMargin: 8
            text: "Stop"
            height: 48
            onTapped: root.cc.stopLearn()
        }
    }

    // Moving the current processor (processor options: Move)
    Grid {
        x: root.area.x + (root.area.width - width) / 2
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 20
        columns: 3
        spacing: 8
        visible: zyn.movingProcessor
        z: 10
        Item { width: 80; height: 56 }
        MoveKey { text: "\u25b2"; onTapped: zyn.moveProcessor("up") }
        Item { width: 80; height: 56 }
        MoveKey { text: "\u25c0"; onTapped: zyn.moveProcessor("left") }
        MoveKey { text: "Done"; onTapped: zyn.endMoveProcessor() }
        MoveKey { text: "\u25b6"; onTapped: zyn.moveProcessor("right") }
        Item { width: 80; height: 56 }
        MoveKey { text: "\u25bc"; onTapped: zyn.moveProcessor("down") }
    }

    component MoveKey: Panel {
        id: moveKey
        property alias text: moveKeyLabel.text
        signal tapped
        width: 80
        height: 56
        radius: 4
        button: true
        color: moveKeyTap.pressed ? Theme.keyText : Theme.overlay
        borderColor: Theme.select
        borderWidth: 2
        Label { id: moveKeyLabel; anchors.centerIn: parent; color: Theme.text; size: 22 }
        TapHandler { id: moveKeyTap; gesturePolicy: TapHandler.ReleaseWithinBounds; onTapped: moveKey.tapped() }
    }
}
