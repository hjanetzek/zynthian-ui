// Classic: a node of chain control's side chain as a plate in its kind's colour (the chain
// manager's), the selected one outlined (marker colour while moving), lines to the next node.
// Look only: the screen (ChainControlScreen, shared) places it and handles its touch.
import QtQuick
import ".."

Item {
    id: cn

    property var node: ({})
    property bool selected: false
    property real sideWidth: 0
    property real sideHeight: 0
    property int blockWidth: 0
    property int blockHeight: 0
    property int vSpacing: 0

    width: sideWidth
    height: blockHeight + vSpacing

    Panel {
        id: block
        x: Math.floor((cn.sideWidth - cn.blockWidth) / 2)
        width: cn.blockWidth
        height: cn.blockHeight
        radius: Theme.radius
        button: true
        color: {
            switch (cn.node.kind) {
            case "midi": return Theme.nodeMidi
            case "synth": return Theme.nodeSynth
            case "audio": return Theme.nodeAudio
            case "special": return Theme.nodeSpecial
            }
            return Theme.nodeOther
        }
        borderColor: cn.selected ? (zyn.movingProcessor ? Theme.marker : Theme.frameActive) : Theme.frame
        borderWidth: cn.selected ? Math.max(2, Theme.frameWidth) : Theme.frameWidth
        Label {
            anchors.centerIn: parent
            width: parent.width - 8
            height: parent.height - 4
            text: cn.node.title || ""
            color: cn.node.bypassed ? Theme.textBypassed : Theme.text
            size: 14
            fontSizeMode: Text.Fit
            minimumPixelSize: 8
            wrapMode: Text.WordWrap
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }
    Repeater {
        model: cn.node.link === "parallel" ? [1 / 8, 7 / 8]
             : cn.node.link ? [1 / 2] : []
        Rectangle {
            required property real modelData
            x: block.x + Math.floor(block.width * modelData) - 1
            y: block.height
            width: 2
            height: cn.node.link === "half" ? Math.floor(cn.vSpacing / 2) : cn.vSpacing
            color: Theme.connector
        }
    }
}
