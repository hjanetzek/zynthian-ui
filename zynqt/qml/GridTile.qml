import QtQuick
import QtQuick.Effects

// A tile of the main menu / add chain grid: icon above, title below, the selected one in the
// selection colour; placeholder cells darkened and empty. Themes replace it (+<theme>/).
Item {
    id: tile

    property int tileIndex
    property string tileTitle
    property string tileIcon
    property bool enabledEntry: true
    property bool placeholder: false
    property bool selected: false
    property real spacing: 0     // the gap right and below (themes with gridSpacing)
    signal activated(string t)

    Panel {
        anchors.fill: parent
        anchors.margins: Theme.tileMargin
        visible: tile.placeholder
        color: Theme.panelHighlight
        cut: Theme.cutLarge
    }
    Panel {
        anchors.fill: parent
        anchors.margins: Theme.tileMargin
        visible: !tile.placeholder
        color: tile.selected ? Theme.select : Theme.panel
        borderColor: tap.pressed ? Theme.frameActive : Theme.frame
        borderWidth: tap.pressed ? Math.max(1, Theme.frameWidth) : Theme.frameWidth
        cut: Theme.cutLarge
        opacity: tile.enabledEntry ? 1 : 0.45

        Image {
            id: icon
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 8
            // half the tile, but room for two title lines below it in low tiles
            width: Math.max(Math.min(parent.width, parent.height) * 0.3,
                            Math.min(Math.min(parent.width, parent.height) * 0.5,
                                     parent.height - 16 - 2.4 * Math.round(18 * Theme.fontScale)))
            height: width
            fillMode: Image.PreserveAspectFit
            source: tile.tileIcon
            sourceSize.width: width
            sourceSize.height: height
            asynchronous: true
            layer.enabled: Theme.tintIcons
            layer.effect: MultiEffect {
                colorization: 1.0
                colorizationColor: tile.selected ? Theme.selectText : Theme.text
            }
        }
        Label {
            anchors.top: icon.bottom
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 4
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.WordWrap
            // two-line titles in low tiles (4 rows at 480 px) shrink instead of running into
            // the next row
            fontSizeMode: Text.Fit
            minimumPixelSize: 9
            text: tile.tileTitle
            color: tile.selected ? Theme.selectText : Theme.text
            size: 18
            title: true
        }
        TapHandler {
            id: tap
            onTapped: tile.activated("S")
            onLongPressed: tile.activated("B")
        }
    }
}
