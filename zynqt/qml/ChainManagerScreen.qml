// Chain manager: one column per chain (zyn.chainManager.graph), top to bottom chain options,
// MIDI input, processors (parallel ones side by side), outputs; the pinned chains (main) on a
// darker background. Tap opens a node, long press moves the chain or processor; flick to scroll.
import QtQuick

Item {
    id: root

    readonly property var cm: zyn.chainManager
    readonly property var sel: cm.selection
    readonly property int blockWidth: 150
    readonly property int blockHeight: 56
    readonly property int hSpacing: 16
    readonly property int vSpacing: 20

    function kindColor(kind) {
        switch (kind) {
        case "midi": return Theme.nodeMidi
        case "synth": return Theme.nodeSynth
        case "audio": return Theme.nodeAudio
        case "special": return Theme.nodeSpecial
        default: return Theme.nodeOther
        }
    }

    Flickable {
        id: flick

        anchors.fill: parent
        anchors.margins: 8
        contentWidth: chains.width
        contentHeight: chains.height
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Row {
            id: chains

            Repeater {
                id: chainRepeater
                model: root.cm.graph

                // One chain
                Rectangle {
                    id: column

                    required property var modelData
                    required property int index
                    readonly property int cols: Math.max(1, ...modelData.rows.map(r => r.length))

                    width: cols * (root.blockWidth + root.hSpacing)
                    height: Math.max(flick.height, nodes.height + root.vSpacing)
                    color: modelData.pinned ? Theme.pinnedBackground : "transparent"
                    border.color: zyn.movingChain && modelData.active ? Theme.marker : "transparent"
                    border.width: 3

                    // Divider between chains
                    Rectangle { width: 1; height: parent.height; color: Theme.divider }

                    Column {
                        id: nodes

                        x: root.hSpacing / 2
                        y: root.vSpacing / 2
                        spacing: root.vSpacing

                        Repeater {
                            model: column.modelData.rows

                            Row {
                                id: nodeRow

                                required property var modelData
                                required property int index
                                spacing: root.hSpacing

                                Repeater {
                                    model: nodeRow.modelData

                                    Panel {
                                        id: node

                                        required property var modelData
                                        required property int index
                                        readonly property bool selected: root.sel[0] === column.index
                                            && root.sel[1] === nodeRow.index && root.sel[2] === index

                                        width: root.blockWidth
                                        height: root.blockHeight
                                        color: root.kindColor(modelData.kind)
                                        borderColor: selected ? (zyn.movingProcessor ? Theme.marker : Theme.select) : color
                                        borderWidth: selected ? 3 : 1

                                        // Connection from the row above (into processors and outputs)
                                        Rectangle {
                                            visible: nodeRow.index > 0 && node.modelData.isDst
                                            x: parent.width / 2 - 1
                                            y: -root.vSpacing
                                            width: 2
                                            height: root.vSpacing
                                            color: Theme.connector
                                        }
                                        // Parallel processors: joined to the first one's line
                                        Rectangle {
                                            visible: node.index > 0 && node.modelData.isDst
                                            x: -root.hSpacing - root.blockWidth / 2
                                            y: -root.vSpacing / 2
                                            width: root.blockWidth + root.hSpacing + 1
                                            height: 2
                                            color: Theme.connector
                                        }

                                        Label {
                                            anchors.fill: parent
                                            anchors.margins: 4
                                            horizontalAlignment: Text.AlignHCenter
                                            verticalAlignment: Text.AlignVCenter
                                            wrapMode: Text.Wrap
                                            elide: Text.ElideRight
                                            fontSizeMode: Text.Fit
                                            minimumPixelSize: 10
                                            text: node.modelData.title
                                            color: node.modelData.bypassed ? Theme.textBypassed : Theme.text
                                            size: node.modelData.kind === "chain" ? 18 : 15
                                            font.weight: node.modelData.kind === "chain" && column.modelData.active ? Font.Bold : Font.Normal
                                        }

                                        TapHandler {
                                            onTapped: root.cm.tapNode(column.index, nodeRow.index, node.index)
                                            onLongPressed: root.cm.longPressNode(column.index, nodeRow.index, node.index)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Keep the selected node in view (keys, a chain made active elsewhere)
    function ensureVisible() {
        if (sel.length < 3)
            return
        const col = chainRepeater.itemAt(sel[0])
        if (!col)
            return
        const x = col.x + sel[2] * (blockWidth + hSpacing)
        const y = vSpacing / 2 + sel[1] * (blockHeight + vSpacing)
        if (x < flick.contentX)
            flick.contentX = x
        else if (x + blockWidth + hSpacing > flick.contentX + flick.width)
            flick.contentX = Math.min(x + blockWidth + hSpacing - flick.width, Math.max(0, flick.contentWidth - flick.width))
        if (y < flick.contentY)
            flick.contentY = Math.max(0, y - vSpacing / 2)
        else if (y + blockHeight > flick.contentY + flick.height)
            flick.contentY = Math.min(y + blockHeight + vSpacing / 2 - flick.height, Math.max(0, flick.contentHeight - flick.height))
    }
    onSelChanged: Qt.callLater(ensureVisible)

    Label {
        anchors.centerIn: parent
        visible: root.cm.graph.length === 0
        text: "No chains"
        color: Theme.textOff
        size: 24
        title: true
    }

    // Moving a chain (left/right) or processor (arrows), as in the mixer and chain control
    Grid {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 20
        columns: 3
        spacing: 8
        visible: zyn.movingProcessor || zyn.movingChain
        z: 10
        Item { width: 80; height: 56 }
        MoveKey { text: "▲"; visible: zyn.movingProcessor; onTapped: zyn.moveProcessor("up") }
        Item { width: 80; height: 56; visible: !zyn.movingProcessor }
        Item { width: 80; height: 56 }
        MoveKey { text: "◀"; onTapped: zyn.movingChain ? zyn.moveChain(-1) : zyn.moveProcessor("left") }
        MoveKey { text: "Done"; onTapped: zyn.movingChain ? zyn.endMoveChain() : zyn.endMoveProcessor() }
        MoveKey { text: "▶"; onTapped: zyn.movingChain ? zyn.moveChain(1) : zyn.moveProcessor("right") }
        Item { width: 80; height: 56 }
        MoveKey { text: "▼"; visible: zyn.movingProcessor; onTapped: zyn.moveProcessor("down") }
        Item { width: 80; height: 56; visible: !zyn.movingProcessor }
    }

    component MoveKey: Panel {
        id: moveKey
        property alias text: moveKeyLabel.text
        signal tapped
        width: 80
        height: 56
        radius: 4
        color: moveKeyTap.pressed ? Theme.keyText : Theme.overlay
        borderColor: Theme.select
        borderWidth: 2
        Label { id: moveKeyLabel; anchors.centerIn: parent; color: Theme.text; size: 22 }
        TapHandler { id: moveKeyTap; gesturePolicy: TapHandler.ReleaseWithinBounds; onTapped: moveKey.tapped() }
    }
}
