import QtQuick
import QtQuick.Effects
import ".."

// tk: the Tk V5 keypad's labels (zynthian_gui_touchkeypad_v5): forkawesome icons for the
// transport and arrows, the metronome image, text in 0.9F points (1.3F on one line); the colour
// of the key's LED as zynthian_wsleds_v5 shows it: the key of the screen shown green, ALT in ALT
// mode, recording red, playing green, BACK red, SEL green, arrows yellow.
Item {
    id: face
    property int key
    property string label

    readonly property var glyphs: ({ 8: "", 9: "", 10: "", 13: "",
                                     16: "", 17: "", 18: "" })
    readonly property var screens: ({ 0: ["admin"], 1: ["mixer"], 2: ["chain_control", "preset", "bank"],
                                      3: ["zs3", "snapshot"], 5: ["tempo"], 6: ["launcher", "pattern_editor"] })
    readonly property string glyph: glyphs[key] || ""
    readonly property var st: zyn.status
    readonly property color ledColor: {
        const scr = screens[key]
        if (scr && scr.indexOf(zyn.currentScreen) >= 0)
            return Theme.tkColor("hl", "#00c000")
        if (key === 4 && zyn.altMode)
            return Theme.tkColor("alt", "#ff00ff")
        if (key === 8 && st && (st.audioRecorder || st.midiRecorder))
            return Theme.tkColor("low_on", "#b00000")
        if (key === 10 && st && (st.audioPlayer || st.midiPlayer || st.seqPlay))
            return Theme.tkColor("hl", "#00c000")
        if (key === 12)
            return "#ff3030"
        if (key === 14)
            return "#30e030"
        if (key === 13 || key >= 16 && key <= 18)
            return "#ffff00"
        return Theme.keyText
    }
    readonly property int fontPt: Theme.tkFontSize

    Image {
        id: metro
        visible: false
        anchors.centerIn: parent
        width: Math.min(parent.width, parent.height) * 0.6
        height: width
        source: face.key === 5 ? Qt.resolvedUrl("../../../icons/metronome.png") : ""
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
