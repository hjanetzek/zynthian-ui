// Plugin widgets (PluginView): bars (1/3 octave spectrum, Guitarix graphic EQ: drag a band to
// set its gain), tuner (note and cents needle), text (NAM model, detected chord), aidax
// (in/out meters, model and cabinet files)
import QtQuick

Rectangle {
    id: root

    property var view
    readonly property var d: view ? view.data : ({})
    color: "#101418"
    clip: true

    // Bars
    Item {
        id: bars
        anchors.fill: parent
        anchors.margins: 4
        visible: root.d.kind === "bars"
        readonly property int n: (root.d.bars || []).length
        readonly property real bw: n ? width / n : 0

        Rectangle {
            visible: (root.d.zero || -1) >= 0
            y: bars.height * (1 - (root.d.zero || 0))
            width: bars.width
            height: 1
            color: "#808080"
        }
        Repeater {
            model: bars.n
            Item {
                required property int index
                readonly property var b: root.d.bars[index]
                x: index * bars.bw
                width: bars.bw
                height: bars.height
                Rectangle {   // level (bottom..top)
                    x: 2
                    width: parent.width - 4
                    y: parent.height * (1 - Math.max(parent.b[0], parent.b[1]))
                    height: parent.height * Math.abs(parent.b[1] - parent.b[0])
                    color: "#3a78c0"
                }
                Rectangle {   // peak / gain tick
                    width: parent.width
                    height: 3
                    y: parent.height * (1 - parent.b[2])
                    color: "#5ad05a"
                }
                Text {
                    // Rotated about its centre: placed so that it ends 2 px above the bottom
                    x: (parent.width - width) / 2
                    y: parent.height - width / 2 - height / 2 - 2
                    text: (root.d.labels || [])[index] || ""
                    rotation: -90
                    transformOrigin: Item.Center
                    color: Theme.textOff
                    font.pixelSize: Math.max(8, Math.min(14, bars.bw * 0.5))
                }
            }
        }
        MouseArea {
            anchors.fill: parent
            enabled: root.d.editable === true
            preventStealing: true
            function set(mouse) {
                root.view.dragBand(Math.floor(mouse.x / bars.bw), 1 - mouse.y / bars.height)
            }
            onPressed: (mouse) => set(mouse)
            onPositionChanged: (mouse) => set(mouse)
        }
    }

    // Tuner
    Item {
        anchors.fill: parent
        visible: root.d.kind === "tuner"
        readonly property real y0: height / 4
        Rectangle { y: parent.y0; width: parent.width; height: 1; color: "#606060" }
        Repeater {
            model: 19
            Rectangle {
                required property int index
                x: root.width / 2 + (index - 9) * root.width / 20
                y: parent.y0 - root.height / 10
                width: 1
                height: root.height / 5
                color: index === 9 ? "#a0a0a0" : "#606060"
            }
        }
        Rectangle {   // cents needle
            visible: root.d.note !== ""
            x: root.width / 2 + (root.d.cents || 0) * root.width / 100 - width / 2
            y: parent.y0 - root.height / 10
            width: Math.max(4, root.width / 30)
            height: root.height / 5
            color: root.d.color || "#00ff00"
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            y: parent.height * 0.5
            text: root.d.note || ""
            color: root.d.color || Theme.text
            font.pixelSize: root.height / 4
            font.family: Theme.fontFamily
        }
    }

    // Text lines (and aidax meters)
    Column {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10
        visible: root.d.kind === "text" || root.d.kind === "aidax"
        Repeater {
            model: root.d.kind === "aidax" ? root.d.meters : []
            Rectangle {
                required property int index
                required property real modelData
                width: parent.width
                height: 24
                color: "#202830"
                Rectangle {
                    width: parent.width * modelData
                    height: parent.height
                    color: modelData > 0.9 ? "#e04040" : (modelData > 0.7 ? "#e0c040" : "#40b040")
                }
                Text {
                    anchors.left: parent.left; anchors.leftMargin: 6; anchors.verticalCenter: parent.verticalCenter
                    text: index === 0 ? "In" : "Out"
                    color: Theme.text
                    font.pixelSize: 14
                }
            }
        }
        Repeater {
            model: root.d.lines || []
            Column {
                required property var modelData
                width: parent.width
                Text {
                    visible: modelData[0] !== ""
                    text: modelData[0]
                    color: Theme.textOff
                    font.pixelSize: 16
                }
                Text {
                    width: parent.width
                    elide: Text.ElideMiddle
                    text: modelData[1]
                    color: Theme.text
                    font.pixelSize: 28
                    font.family: Theme.fontFamily
                }
            }
        }
    }
}
