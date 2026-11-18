// The pattern editor screen, for every theme: the theme's toolbar (PatternToolbar; tk: none, as
// Tk) above the shared PatternEditorView (layout, content and touch as Tk's; colours from the
// theme's tokens). Themes replace this file only to frame the view (+v4: the knob hints at the
// edges).
import QtQuick

Item {
    id: root
    readonly property bool hasToolbar: toolbar.height > 0

    PatternToolbar {
        id: toolbar
        pe: zyn.patternEditor
        x: root.hasToolbar ? 4 : 0
        y: root.hasToolbar ? 4 : 0
        width: parent.width - 2 * x
    }

    PatternEditorView {
        y: root.hasToolbar ? toolbar.y + toolbar.height + 4 : 0
        width: parent.width
        height: parent.height - y
    }
}
