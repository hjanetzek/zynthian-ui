// A plate: the background of keys, list rows, strips, controllers and buttons. With the theme's
// corner cut 0 a rectangle (rounded as the theme says), otherwise an octagon with clipped corners,
// filled and outlined by one ShapePath (default renderer: triangulated once per size change).
import QtQuick
import QtQuick.Shapes

Item {
    id: root

    property color color: Theme.panel
    property color borderColor: Theme.frame
    property real borderWidth: Theme.frameWidth
    property real cut: Theme.cut
    property real radius: 0          // radius in themes without their own (classic)
    property bool button: false      // keys and buttons: pills in themes with pillButtons
    property real cornerRadius: -1   // >= 0: this radius, over the theme's (the keypad's keys)

    readonly property bool cutCorners: cut > 0
    // Keep the outline inside the item
    readonly property real _i: borderWidth / 2
    readonly property real _c: Math.min(cut, width / 2, height / 2)
    readonly property real _r: cornerRadius >= 0 ? Math.min(cornerRadius, width / 2, height / 2)
                               : (Theme.pillButtons && button ? Math.min(width, height) / 2
                                  : (Theme.panelRadius > 0 ? Math.min(Theme.panelRadius, width / 2, height / 2) : radius))

    Rectangle {
        visible: !root.cutCorners
        anchors.fill: parent
        color: root.color
        radius: root._r
        border.color: root.borderWidth > 0 ? root.borderColor : "transparent"
        border.width: root.borderWidth
    }

    Shape {
        visible: root.cutCorners
        anchors.fill: parent
        ShapePath {
            fillColor: root.color
            strokeColor: root.borderWidth > 0 ? root.borderColor : "transparent"
            strokeWidth: root.borderWidth
            joinStyle: ShapePath.MiterJoin
            startX: root._c; startY: root._i
            PathLine { x: root.width - root._c; y: root._i }
            PathLine { x: root.width - root._i; y: root._c }
            PathLine { x: root.width - root._i; y: root.height - root._c }
            PathLine { x: root.width - root._c; y: root.height - root._i }
            PathLine { x: root._c; y: root.height - root._i }
            PathLine { x: root._i; y: root.height - root._c }
            PathLine { x: root._i; y: root._c }
            PathLine { x: root._c; y: root._i }
        }
    }
}
