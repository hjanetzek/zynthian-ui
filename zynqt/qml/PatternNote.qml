// A note in the pattern editor's grid (an event of PatternEditor.events): the note brighter with
// velocity, faded if it never plays, its stutter (ticks: retriggers, rising or falling with its
// velocity effect) and its play / stutter frequency or chance as a label
import QtQuick

Rectangle {
    id: noteItem
    required property var modelData
    property real stepWidth: 30
    property real rowHeight: 34
    property int nRows: 1
    // The fill (classic: a hue, lighter with velocity; tk: grey by velocity as Tk)
    property color fill: Qt.hsla(Theme.noteHue, 0.8, 0.25 + 0.45 * modelData.velocity / 127, 1)
    readonly property color decoColor: modelData.velocity >= 58 ? "#101010" : "#e0e0e0"
    x: modelData.step * noteItem.stepWidth + 1
    y: (noteItem.nRows - 1 - modelData.row) * noteItem.rowHeight + 2
    width: Math.max(6, modelData.duration * noteItem.stepWidth - 2)
    height: noteItem.rowHeight - 4
    radius: 3
    opacity: modelData.muted ? 0.35 : 1
    color: fill
    // Selected notes (block selection, all): a selection frame
    border.color: modelData.selected ? Theme.selectionFrame : Theme.noteFrame
    border.width: modelData.selected ? 3 : 1
    Repeater {
        id: ticks
        model: noteItem.modelData.stutter > 0
               ? Math.max(1, Math.min(Math.floor(noteItem.width / 4),
                                      Math.round(noteItem.modelData.duration * noteItem.modelData.stutter)))
               : 0
        Rectangle {
            required property int index
            readonly property real level: {
                const n = Math.max(1, ticks.count - 1)
                const fx = noteItem.modelData.stutterFx
                return fx === 1 ? 0.3 + 0.7 * index / n : (fx === 2 ? 1 - 0.7 * index / n : 0.5)
            }
            x: index * noteItem.width / ticks.count + 1
            width: Math.max(1, noteItem.width / ticks.count / 2)
            // Lower half with a label, so it stays readable
            height: (noteItem.height - 4) * level * (noteItem.modelData.label ? 0.4 : 1)
            y: noteItem.height - 2 - height
            color: noteItem.decoColor
            opacity: noteItem.modelData.stutterMuted ? 0.3 : 0.6
        }
    }
    Text {
        visible: text !== ""
        anchors.centerIn: parent
        width: parent.width - 2
        horizontalAlignment: Text.AlignHCenter
        elide: Text.ElideRight
        text: noteItem.modelData.label
        color: noteItem.decoColor
        font.pixelSize: Math.min(13, noteItem.height - 2)
    }
}
