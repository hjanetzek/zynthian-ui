// v4: the knob hints (KnobHints.qml) at the screen's edges when the list screen says what its
// knobs do (knobHints: the flat preset list's group and preset knobs); the list and the info pane
// move inwards by a hint column on each side.
import QtQuick
import ".."

Item {
    id: root
    property var texts: []
    readonly property bool shown: texts && texts.length > 0
    readonly property int leftInset: shown ? knobs.edge : 0
    readonly property int rightInset: shown ? knobs.edge : 0

    KnobHints {
        id: knobs
        anchors.fill: parent
        visible: root.shown
        texts: root.shown ? root.texts : ["", "", "", ""]
    }
}
