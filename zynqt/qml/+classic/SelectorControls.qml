// The controller widgets under a selector's info pane (split out: themes override it, e.g.
// the base SelectorControls.qml (tk) draws Tk's selector counter). By default none: the info pane keeps the
// whole height.
import QtQuick
import ".."

Item {
    property var screen: null
    implicitHeight: 0
    visible: false
}
