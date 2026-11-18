import QtQuick
import ".."

// The label of a keypad key (classic: its text in the key colours; enterprise: dark text at the
// bottom right of filled keys) and its LED as a light (tk colours the label with it instead).
// Themes replace it (+<theme>/KeyFace.qml).
Item {
    id: face
    property int key
    property string label
    property string subLabel     // F1-F4 with a function label: their name, small in the corner
    property real radius: 0      // the plate's corner radius with Theme.keyRadius (Keypad.qml)

    // The key's LED (zynthian_wsleds_v5 via zyn.keypadLeds, as tk): lit when it shows a state
    // (the workflow's key, ALT, REC / PLAY, the screen's LEDs; the arrows, SEL and BACK), blinking
    // where Tk's LED blinks. A bar at the top centre; filled keys: a dot at the top left, clear of
    // the corner and of the key's name at the top right.
    readonly property bool ledLit: !!(zyn.keypadLeds.lit || [])[key]
    readonly property color ledColor: zyn.keypadLeds.colors[key] || Theme.keyText
    Rectangle {
        visible: face.ledLit
        readonly property real inset: Theme.keyFilled ? Math.max(6, 0.3 * face.radius) : 0
        x: Theme.keyFilled ? inset : Math.round((face.width - width) / 2)
        y: Theme.keyFilled ? inset : 3
        width: Theme.keyFilled ? 8 : Math.round(Math.min(32, 0.3 * face.width))
        height: Theme.keyFilled ? 8 : 4
        radius: height / 2
        color: face.ledColor
        border.width: Theme.keyFilled ? 1 : 0
        border.color: Theme.keyFilledText
    }

    Label {
        id: main
        anchors.centerIn: Theme.keyFilled ? undefined : parent
        anchors.right: Theme.keyFilled ? parent.right : undefined
        anchors.bottom: Theme.keyFilled ? parent.bottom : undefined
        // Filled keys: clear of the rounded corner (keyRadius: inside its arc; else pills)
        anchors.rightMargin: !Theme.keyFilled ? 0 : (face.radius > 0 ? Math.max(8, 0.35 * face.radius)
                                                     : (parent.width > parent.height ? parent.height / 2 : 12))
        anchors.bottomMargin: !Theme.keyFilled ? 0 : (face.radius > 0 ? Math.max(8, 0.3 * face.radius) : 8)
        // Shrunk to fit the key (function labels, small keys), below the secondary label
        width: parent.width - (Theme.keyFilled ? anchors.rightMargin + 6 : 6)
        height: Theme.keyFilled ? parent.height - anchors.bottomMargin - (face.subLabel ? sub.y + sub.height : 4)
                                : parent.height - 2 * (face.subLabel ? sub.y + sub.height : 2)
        fontSizeMode: Text.Fit
        minimumPixelSize: 6
        horizontalAlignment: Theme.keyFilled ? Text.AlignRight : Text.AlignHCenter
        verticalAlignment: Theme.keyFilled ? Text.AlignBottom : Text.AlignVCenter
        text: face.label
        color: Theme.keyFilled ? Theme.keyFilledText
                               : (face.key === 12 ? Theme.keyBack : (face.key === 14 || face.key === 2 ? Theme.keyYes : Theme.keyText))
        size: 20
        title: true
        lineHeight: Theme.keyLineHeight
    }
    // The key's name beside its function label: top left; filled keys top right, clear of the corner
    Label {
        id: sub
        visible: face.subLabel !== ""
        x: Theme.keyFilled ? parent.width - width - Math.max(8, 0.35 * face.radius) : 4
        y: Theme.keyFilled ? Math.max(4, 0.3 * face.radius) : 2
        text: face.subLabel
        color: main.color
        opacity: Theme.keyFilled ? 1 : 0.8
        // Not above the function label shrunk into a narrow key
        size: Math.min(12, main.fontInfo.pixelSize / Theme.fontScale)
        title: true
    }
}
