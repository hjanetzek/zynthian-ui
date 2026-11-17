import QtQuick
import QtQuick.Effects

// tk: the Tk V5 keypad's labels (zynthian_gui_touchkeypad_v5): forkawesome icons for the
// transport and arrows, the metronome image, text in 0.9F points (1.3F on one line); the colour
// of the key's LED as zynthian_wsleds_v5 sets it (zyn.keypadLeds: the workflow's key, ALT, the
// transport, the screen's own LEDs).
Item {
    id: face
    property int key
    property string label
    property string subLabel     // F1-F4 with a function label: their name, small in the corner
    property real radius: 0      // the plate's corner radius with Theme.keyRadius (Keypad.qml)

    readonly property var glyphs: ({ 8: "", 9: "", 10: "", 13: "",
                                     16: "", 17: "", 18: "" })
    readonly property string glyph: glyphs[key] || ""
    // The LED (zynthian_wsleds_v5 via KeypadLeds)
    readonly property color ledColor: zyn.keypadLeds.colors[key] || Theme.keyText
    readonly property int fontPt: Theme.tkFontSize

    Image {
        id: metro
        visible: false
        anchors.centerIn: parent
        width: Math.min(parent.width, parent.height) * 0.6
        height: width
        source: face.key === 5 ? Qt.resolvedUrl("../../icons/metronome.png") : ""
        fillMode: Image.PreserveAspectFit
    }
    MultiEffect {
        visible: face.key === 5
        anchors.fill: metro
        source: metro
        colorization: 1.0
        colorizationColor: face.ledColor
    }
    Text {
        id: main
        visible: face.key !== 5
        anchors.centerIn: parent
        // Shrunk to fit the key (function labels, large fonts), clear of the secondary label
        width: parent.width - 4
        height: parent.height - 2 * (face.subLabel ? sub.y + sub.height : 2)
        fontSizeMode: Text.Fit
        minimumPixelSize: 6
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        text: face.glyph || face.label
        color: face.ledColor
        font.family: face.glyph ? "forkawesome" : Theme.fontFamily
        font.pixelSize: Theme.tkPx(face.glyph ? Math.floor(1.5 * face.fontPt)
                                              : (face.subLabel || face.label.indexOf("\n") >= 0 ? Math.floor(0.9 * face.fontPt) : Math.floor(1.3 * face.fontPt)))
        lineHeight: 0.95
    }
    Text {
        id: sub
        visible: face.subLabel !== ""
        x: 4; y: 2
        text: face.subLabel
        color: face.ledColor
        opacity: 0.8
        font.family: Theme.fontFamily
        font.pixelSize: Math.min(Theme.tkPx(Math.floor(0.6 * face.fontPt)), main.fontInfo.pixelSize)
    }
}
