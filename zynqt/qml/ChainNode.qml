// tk: a node of chain control's side chain as zynthian_side_chain draws it: a block coloured by
// its kind (white text, grey when bypassed; the selected one outlined, yellow while moving), the
// 4 px lines to the next node. The screen (ChainControlScreen) places it and handles its touch;
// themes replace this file for another look (+<theme>/ChainNode.qml, same properties).
import QtQuick

Item {
    id: cn

    property var node: ({})          // title, kind (midi, synth, audio, special, other), bypassed, link
    property bool selected: false
    property real sideWidth: 0       // the side chain's size
    property real sideHeight: 0
    property int blockWidth: 0
    property int blockHeight: 0
    property int vSpacing: 0

    width: sideWidth
    height: blockHeight + vSpacing

    Rectangle {
        id: block
        x: Math.floor((cn.sideWidth - cn.blockWidth) / 2)
        width: cn.blockWidth
        height: cn.blockHeight
        color: {
            switch (cn.node.kind) {
            case "midi": return Theme.nodeMidi
            case "synth": return Theme.nodeSynth
            case "audio": return Theme.nodeAudio
            case "special": return Theme.nodeSpecial
            }
            return Theme.nodeOther
        }
        border.width: cn.selected ? 2 : 0
        border.color: zyn.movingProcessor ? "#ffff00" : "#ffffff"
        Text {
            anchors.centerIn: parent
            width: Math.floor(0.9 * cn.blockWidth)
            height: Math.floor(0.9 * cn.blockHeight)
            text: cn.node.title || ""
            color: cn.node.bypassed ? Theme.textBypassed : "#ffffff"
            font.family: Theme.fontFamily
            font.pixelSize: Theme.tkPx(Math.floor(0.026 * cn.sideHeight))
            minimumPixelSize: Theme.tkPx(6)
            fontSizeMode: Text.VerticalFit
            wrapMode: Text.WordWrap
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }
    // Lines to the next node (4 px, #AAAAAA)
    Repeater {
        model: cn.node.link === "parallel" ? [1 / 8, 7 / 8]
             : cn.node.link ? [1 / 2] : []
        Rectangle {
            required property real modelData
            x: block.x + Math.floor(block.width * modelData) - 2
            y: block.height
            width: 4
            height: cn.node.link === "half" ? Math.floor(cn.vSpacing / 2) : cn.vSpacing
            color: Theme.connector
        }
    }
}
