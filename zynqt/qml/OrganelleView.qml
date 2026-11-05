// Organelle patches (OrganelleView): the 128x64 OLED (tap a menu line to select it), the LED,
// AUX and FS buttons (held while pressed) and the encoder (up, select, down)
import QtQuick
import Zynthian 1.0

Rectangle {
    id: root

    property var view
    color: Theme.panel
    clip: true

    OledDisplay {
        id: oled
        view: root.view
        anchors.horizontalCenter: parent.horizontalCenter
        y: 6
        width: Math.min(parent.width - 12, 2 * (parent.height - controls.height - 18))
        height: width / 2
        TapHandler {
            onTapped: (eventPoint) => root.view.touch(eventPoint.position.y / oled.height * 64)
        }
    }

    Row {
        id: controls
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 6
        height: 56
        spacing: 12
        Rectangle {   // LED
            anchors.verticalCenter: parent.verticalCenter
            width: 18; height: 18; radius: 9
            color: root.view && root.view.led ? "#00e000" : "#204020"
        }
        HoldButton { text: "AUX"; path: "/aux" }
        HoldButton { text: "FS"; path: "/fs"; visible: root.view ? root.view.fsButton : true }
        Row {
            spacing: 4
            visible: root.view ? root.view.selector : true
            PressButton { text: "▲"; onTapped: root.view.encoder(-1) }
            PressButton { text: "SEL"; onTapped: root.view.encoderPress() }
            PressButton { text: "▼"; onTapped: root.view.encoder(1) }
        }
    }

    component HoldButton: Rectangle {
        id: hb
        property alias text: hbl.text
        property string path
        width: 70; height: 56; radius: 28
        color: hbTap.pressed ? "#00a000" : "#b07000"
        Text { id: hbl; anchors.centerIn: parent; color: "white"; font.pixelSize: 16; font.bold: true }
        TapHandler {
            id: hbTap
            gesturePolicy: TapHandler.WithinBounds
            onPressedChanged: root.view.button(hb.path, pressed)
        }
    }

    component PressButton: Rectangle {
        id: pb
        property alias text: pbl.text
        signal tapped
        width: 60; height: 56; radius: 6
        color: pbTap.pressed ? Theme.keyText : Theme.keyBackground
        Text { id: pbl; anchors.centerIn: parent; color: "white"; font.pixelSize: 18 }
        TapHandler { id: pbTap; gesturePolicy: TapHandler.ReleaseWithinBounds; onTapped: pb.tapped() }
    }
}
