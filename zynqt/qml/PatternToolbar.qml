// The pattern editor's toolbar: play, record, undo, redo, CC / notes, the note-entry values,
// block selection, menu, and the pattern's title (the edit mode's while one is on).
// +tk/PatternToolbar.qml: none (Tk has the knobs, switches and the menu only)
import QtQuick

Row {
    id: root

    property var pe: zyn.patternEditor

    height: 48
    spacing: 6 * k
    // Narrower windows (800 px): the buttons shrink with the width (made for 960)
    readonly property real k: Math.min(1, width / 1000)

    ToolButton { text: root.pe.playing ? "■ Stop" : "▶ Play"; baseWidth: 120; on: root.pe.playing; onTapped: root.pe.togglePlayback() }
    ToolButton {
        text: "● Rec"; baseWidth: 90; on: root.pe.recording; onColor: Theme.buttonRecord
        onTapped: root.pe.toggleRecording()
    }
    ToolButton { text: "Undo"; onTapped: root.pe.undo() }
    ToolButton { text: "Redo"; onTapped: root.pe.redo() }
    ToolButton { text: root.pe.ccMode ? "Notes" : "CC"; baseWidth: 80; onTapped: root.pe.toggleCcMode() }
    ToolButton {
        text: root.pe.ccMode ? root.pe.ccTitle : root.pe.entryText
        baseWidth: 230
        onTapped: root.pe.ccMode ? root.pe.pickCc() : root.pe.entryOptions()
    }
    ToolButton { text: "Select"; baseWidth: 90; on: root.pe.selectMode; onTapped: root.pe.toggleSelectMode() }
    ToolButton { text: "Copy"; baseWidth: 80; visible: root.pe.selectMode; onTapped: root.pe.copyBlock(false) }
    ToolButton { text: "Cut"; baseWidth: 70; visible: root.pe.selectMode; onTapped: root.pe.copyBlock(true) }
    ToolButton { text: "Del"; baseWidth: 70; visible: root.pe.selectMode; onTapped: root.pe.deleteBlock() }
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
        property real baseWidth: 100
        signal tapped
        width: baseWidth * root.k
        height: parent.height
        radius: 4
        button: true
        color: tap.pressed ? Theme.keyText : (on ? onColor : Theme.keyBackground)
        Label {
            id: label
            anchors.centerIn: parent
            color: Theme.text
            body: true   // the entry and CC titles keep their case
            size: 16 * Math.max(0.8, root.k)
            width: Math.min(implicitWidth, button.width - 6)
            elide: Text.ElideRight
        }
        TapHandler { id: tap; gesturePolicy: TapHandler.ReleaseWithinBounds; onTapped: button.tapped() }
    }
}
