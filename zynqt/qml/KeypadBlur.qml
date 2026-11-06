// Blurred copy of the screens under the overlay keypad (two areas: the side columns and the
// bottom row). Loaded through a Loader: without the QtQuick.Effects module only this fails and
// the keys stay translucent without blur.
import QtQuick
import QtQuick.Effects

Item {
    id: root

    property Item source             // the screens item, at (0, 0) of this item
    property real sideWidth
    property real bottomHeight

    component BlurArea: Item {
        id: area
        ShaderEffectSource {
            id: snap
            anchors.fill: parent
            sourceItem: root.source
            sourceRect: Qt.rect(area.x, area.y, area.width, area.height)
            live: true
            visible: false
        }
        MultiEffect {
            anchors.fill: parent
            source: snap
            blurEnabled: true
            blur: 1.0
            blurMax: 64
            blurMultiplier: 1.0
            autoPaddingEnabled: false
            brightness: -0.2
        }
    }

    BlurArea { x: 0; y: 0; width: root.sideWidth; height: root.height - root.bottomHeight }
    BlurArea { x: 0; y: root.height - root.bottomHeight; width: root.width; height: root.bottomHeight }
}
