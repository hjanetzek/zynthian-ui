// v4: tk's pattern editor (PatternEditorView) between the knob hints: what the knobs do in the
// current edit mode (zoom, note, step; the edit modes' and the CC view's functions), as
// zynthian_gui_pated_base / _notes / _cc with Tk's V4 layout.
import QtQuick
import ".."

Rectangle {
    id: root
    color: Theme.background

    KnobHints {
        id: hints
        anchors.fill: parent
        texts: zyn.patternEditor.knobHints(zyn.patternEditor.editMode, zyn.patternEditor.ccMode)
    }

    PatternEditorView {
        x: hints.edge
        width: parent.width - 2 * hints.edge
        height: parent.height
    }
}
