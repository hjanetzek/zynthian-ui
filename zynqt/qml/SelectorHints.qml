// What the knobs do on a list screen (the screen's knobHints, by knob index), for themes that
// show it beside the list (+v4). None by default: the insets keep the list where it is.
import QtQuick

Item {
    property var texts: []
    readonly property int leftInset: 0
    readonly property int rightInset: 0
}
