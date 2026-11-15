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
        visible: face.key !== 5
        anchors.centerIn: parent
        horizontalAlignment: Text.AlignHCenter
        text: face.glyph || face.label
        color: face.ledColor
        font.family: face.glyph ? "forkawesome" : Theme.fontFamily
        font.pixelSize: Theme.tkPx(face.glyph ? Math.floor(1.5 * face.fontPt)
                                              : (face.label.indexOf("\n") >= 0 ? Math.floor(0.9 * face.fontPt) : Math.floor(1.3 * face.fontPt)))
        lineHeight: 0.95
    }
}
