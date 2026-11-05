// Euclidean sequencer (EuclidSeqView, EuclidSeq6 patch): six channel circles with their steps,
// hits and play position; tap a circle to select its channel, drag it up/down for its note.
// The panel changes the selected channel (mode, length, hits, offset, interval, mute).
import QtQuick
import QtQuick.Shapes

Rectangle {
    id: root

    property var view
    readonly property var p: view ? view.panel : ({})
    color: "#000000"
    clip: true

    Grid {
        id: circles
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.right: panel.left
        anchors.margins: 6
        columns: 3
        readonly property real cell: Math.min(width / 3, height / 2)
        Repeater {
            model: root.view ? root.view.channels : []
            Item {
                id: chan
                required property var modelData
                required property int index
                width: circles.cell
                height: circles.cell
                readonly property real r: width * 0.38
                function px(u) { return width / 2 + u * r }
                function py(u) { return height / 2 + u * r }

                Rectangle {   // selected channel
                    visible: chan.modelData.selected
                    anchors.centerIn: parent
                    width: parent.r * 0.55; height: width
                    color: "#555500"; border.color: "yellow"; border.width: 2
                }
                Repeater {   // steps
                    model: chan.modelData.dots
                    Rectangle {
                        required property var modelData
                        x: chan.px(modelData[0]) - 1.5; y: chan.py(modelData[1]) - 1.5
                        width: 3; height: 3; color: "white"
                    }
                }
                Shape {   // hits joined
                    anchors.fill: parent
                    visible: chan.modelData.hits.length > 0
                    preferredRendererType: Shape.GeometryRenderer
                    ShapePath {
                        strokeColor: "white"; strokeWidth: 1; fillColor: "transparent"
                        PathPolyline {
                            path: {
                                const h = chan.modelData.hits
                                if (h.length === 1)
                                    return [Qt.point(chan.width / 2, chan.height / 2), Qt.point(chan.px(h[0][0]), chan.py(h[0][1]))]
                                const pts = h.map(q => Qt.point(chan.px(q[0]), chan.py(q[1])))
                                if (pts.length > 1) pts.push(pts[0])
                                return pts
                            }
                        }
                    }
                }
                Repeater {   // hits
                    model: chan.modelData.hits
                    Rectangle {
                        required property var modelData
                        x: chan.px(modelData[0]) - 4; y: chan.py(modelData[1]) - 4
                        width: 8; height: 8; radius: 4
                        color: chan.modelData.selected ? "yellow" : "deepskyblue"
                    }
                }
                Rectangle {   // play position: filled on a hit
                    readonly property var pp: chan.modelData.play
                    visible: pp.length === 3
                    x: chan.px(pp[0] || 0) - width / 2; y: chan.py(pp[1] || 0) - height / 2
                    width: pp[2] ? 16 : 12; height: width; radius: width / 2
                    color: pp[2] ? "white" : "transparent"
                    border.color: "white"; border.width: 2
                }
                Text {
                    anchors.centerIn: parent
                    text: chan.modelData.note
                    color: chan.modelData.muted ? "#606060" : "#00ff00"
                    font.pixelSize: chan.r * 0.35
                    font.bold: true
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    text: "Ch " + (chan.index + 1)
                    color: "red"
                    font.pixelSize: 14
                    font.bold: true
                }
                MouseArea {
                    anchors.fill: parent
                    property real lastY
                    property bool dragged
                    onPressed: (mouse) => { lastY = mouse.y; dragged = false }
                    onPositionChanged: (mouse) => {
                        const dy = mouse.y - lastY
                        if (Math.abs(dy) >= 15) {
                            root.view.nudgeNote(chan.index, dy > 0 ? -1 : 1)
                            lastY = mouse.y
                            dragged = true
                        }
                    }
                    onReleased: if (!dragged) root.view.selectChannel(chan.index)
                }
            }
        }
    }

    Column {
        id: panel
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 6
        width: 230
        spacing: 6
        ValueRow { label: "Mode"; value: root.p.mode || ""; key: "mode" }
        Text {
            text: "Channel " + (root.p.channel || 1)
            color: "white"; font.pixelSize: 18; font.bold: true
        }
        ValueRow { label: "Length"; value: root.p.length; key: "length" }
        ValueRow { label: "Hits"; value: root.p.hits; key: "hits" }
        ValueRow { label: "Offset"; value: root.p.offset; key: "offset" }
        ValueRow { label: "Interval"; value: root.p.interval; key: "interval"; visible: root.p.showInterval === true }
        Rectangle {
            width: parent.width; height: 40; radius: 4
            color: root.p.mute ? "#225522" : "#552222"
            Text { anchors.centerIn: parent; text: root.p.mute ? "Unmute" : "Mute"; color: "white"; font.pixelSize: 16 }
            TapHandler { gesturePolicy: TapHandler.ReleaseWithinBounds; onTapped: root.view.toggleMute() }
        }
    }

    component ValueRow: Row {
        id: vrow
        property string label
        property var value
        property string key
        spacing: 4
        height: 40
        Text { width: 70; height: parent.height; verticalAlignment: Text.AlignVCenter; text: vrow.label; color: "#cccccc"; font.pixelSize: 15 }
        StepButton { text: "−"; onTapped: root.view.adjust(vrow.key, -1) }
        Text {
            width: 80; height: parent.height
            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
            text: vrow.value === undefined ? "--" : vrow.value
            color: "#00ff00"; font.pixelSize: 16; font.bold: true
        }
        StepButton { text: "+"; onTapped: root.view.adjust(vrow.key, 1) }
    }

    component StepButton: Rectangle {
        id: sb
        property alias text: sbl.text
        signal tapped
        width: 34; height: 40; radius: 4
        color: sbTap.pressed ? "#555555" : "#333333"
        Text { id: sbl; anchors.centerIn: parent; color: "white"; font.pixelSize: 20 }
        TapHandler { id: sbTap; gesturePolicy: TapHandler.ReleaseWithinBounds; onTapped: sb.tapped() }
    }
}
