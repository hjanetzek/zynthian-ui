// The pattern editor's toolbar: play, record, undo, redo, CC / notes, the note-entry values,
// block selection, menu, and the pattern's title (the edit mode's while one is on).
// +tk/PatternToolbar.qml: none (Tk has the knobs, switches and the menu only)
import QtQuick

Row {
    id: root

    property var pe: zyn.patternEditor

    height: 48
    spacing: 6

    ToolButton { text: root.pe.playing ? "■ Stop" : "▶ Play"; width: 120; on: root.pe.playing; onTapped: root.pe.togglePlayback() }
    ToolButton {
        text: "● Rec"; width: 90; on: root.pe.recording; onColor: Theme.buttonRecord
        onTapped: root.pe.toggleRecording()
    }
    ToolButton { text: "Undo"; onTapped: root.pe.undo() }
    ToolButton { text: "Redo"; onTapped: root.pe.redo() }
    ToolButton { text: root.pe.ccMode ? "Notes" : "CC"; width: 80; onTapped: root.pe.toggleCcMode() }
    ToolButton {
        text: root.pe.ccMode ? root.pe.ccTitle : root.pe.entryText
        width: 230
        onTapped: root.pe.ccMode ? root.pe.pickCc() : root.pe.entryOptions()
    }
    ToolButton { text: "Select"; width: 90; on: root.pe.selectMode; onTapped: root.pe.toggleSelectMode() }
    ToolButton { text: "Copy"; width: 80; visible: root.pe.selectMode; onTapped: root.pe.copyBlock(false) }
    ToolButton { text: "Cut"; width: 70; visible: root.pe.selectMode; onTapped: root.pe.copyBlock(true) }
    ToolButton { text: "Del"; width: 70; visible: root.pe.selectMode; onTapped: root.pe.deleteBlock() }
    ToolButton { text: "Menu"; onTapped: root.pe.menu() }
    Label {
        anchors.verticalCenter: parent.verticalCenter
        width: Math.max(0, root.width - x)
        elide: Text.ElideRight
        text: root.pe.modeTitle !== "" ? root.pe.modeTitle : root.pe.title
        color: Theme.textOff
        body: true
        size: 16
    }

    component ToolButton: Panel {
        id: button
        property alias text: label.text
        property bool on: false
        property color onColor: Theme.buttonOn
        signal tapped
        width: 100
        height: parent.height
        radius: 4
        button: true
        color: tap.pressed ? Theme.keyText : (on ? onColor : Theme.keyBackground)
        Label {
            id: label
            anchors.centerIn: parent
            color: Theme.text
            body: true   // the entry and CC titles keep their case
            size: 16
        }
        TapHandler { id: tap; gesturePolicy: TapHandler.ReleaseWithinBounds; onTapped: button.tapped() }
    }
}
