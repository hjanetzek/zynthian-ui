import QtQuick
import QtQuick.Effects

// The selector's info pane: the selected entry's icon above its description
Panel {
    id: pane
    property string icon
    property string info

    color: Theme.infoBackground
    cut: Theme.cutLarge

    Image {
        id: infoIcon
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.topMargin: 6
        width: Math.min(parent.width - 12, 160)
        height: source != "" ? width : 0
        fillMode: Image.PreserveAspectFit
        asynchronous: true
        source: pane.icon
        // Icons (white line art) in the theme's text colour
        layer.enabled: Theme.tintIcons
        layer.effect: MultiEffect { colorization: 1.0; colorizationColor: Theme.text }
    }
    Label {
        anchors.top: infoIcon.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 6
        wrapMode: Text.WordWrap
        text: pane.info
        color: Theme.text
        body: true
        size: Theme.infoTextSize
    }
}
