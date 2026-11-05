// Waveform of an audio file processor (AudioFileView): one filled shape per channel, crop and
// loop markers, beat / cue markers, the play cursor and the file info; wheel zooms
import QtQuick
import QtQuick.Shapes

Rectangle {
    id: root

    property var view
    color: "#101418"
    clip: true

    onViewChanged: if (view && wave.width > 0) view.setSize(wave.width, wave.height)

    Item {
        id: wave
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: info.top
        onWidthChanged: if (root.view && width > 0) root.view.setSize(width, height)
        onHeightChanged: if (root.view && width > 0) root.view.setSize(width, height)

        // Outside the crop range darker
        Rectangle {
            width: Math.max(0, Math.min(wave.width, root.view.markers.cropStart || 0))
            height: wave.height
            color: "#181e24"
        }
        Rectangle {
            x: Math.max(0, root.view.markers.cropEnd || wave.width)
            width: Math.max(0, wave.width - x)
            height: wave.height
            color: "#181e24"
        }

        Repeater {
            model: root.view ? root.view.paths : []
            Shape {
                required property var modelData
                anchors.fill: parent
                preferredRendererType: Shape.GeometryRenderer
                ShapePath {
                    strokeWidth: 0
                    strokeColor: "transparent"
                    fillColor: "#4a90d0"
                    PathPolyline { path: modelData }
                }
            }
        }

        // Beat or cue markers
        Repeater {
            model: root.view ? root.view.markers.beats || [] : []
            Rectangle {
                required property var modelData
                x: modelData.x
                width: 1
                height: wave.height
                color: modelData.strong ? "#e0e0e0" : "#707070"
            }
        }
        // Crop markers
        Rectangle { x: (root.view.markers.cropStart || 0) - 1; width: 2; height: wave.height; color: "#e0c000" }
        Rectangle { x: (root.view.markers.cropEnd || 0) - 1; width: 2; height: wave.height; color: "#e0c000" }
        // Loop markers
        Rectangle {
            visible: (root.view.markers.loopStart || -1) >= 0
            x: (root.view.markers.loopStart || 0) - 1; width: 2; height: wave.height; color: "#40c040"
        }
        Rectangle {
            visible: (root.view.markers.loopEnd || -1) >= 0
            x: (root.view.markers.loopEnd || 0) - 1; width: 2; height: wave.height; color: "#40c040"
        }
        // Play cursor
        Rectangle {
            visible: root.view && root.view.cursorX >= 0
            x: root.view ? root.view.cursorX : 0
            width: 2
            height: wave.height
            color: "#ff4040"
        }
        WheelHandler {
            onWheel: (event) => root.view.nudgeZoom(event.angleDelta.y > 0 ? 1 : -1)
        }
    }

    Text {
        id: info
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 4
        text: root.view ? root.view.info : ""
        color: Theme.textOff
        font.pixelSize: 14
        font.family: "DejaVu Sans Mono"
    }
}
