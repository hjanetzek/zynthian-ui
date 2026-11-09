pragma Singleton
import QtQuick

// UI theme: colours, fonts and shapes. The theme is chosen at start with ZYNTHIAN_QT_THEME
// (zynthian_qt_main.py sets the context property zynThemeName): "classic" (zynthian's default
// colours, as zynthian_gui_config) or "galactica" (a battlestar CIC console: gun-metal panels with
// clipped corners, amber console text in a condensed face, red alerts).
QtObject {
    id: theme

    property string name: typeof zynThemeName !== "undefined" && zynThemeName ? zynThemeName : "classic"
    readonly property QtObject p: name === "galactica" ? galactica : classic
    readonly property bool isGalactica: name === "galactica"

    // Colours
    readonly property color background: p.background
    readonly property color panel: p.panel
    readonly property color panelHighlight: p.panelHighlight
    readonly property color text: p.text
    readonly property color textOff: p.textOff
    readonly property color disabled: p.disabled
    readonly property color select: p.select
    readonly property color selectText: p.selectText
    readonly property color keyBackground: p.keyBackground
    readonly property color keyText: p.keyText
    readonly property color keyBack: p.keyBack
    readonly property color keyYes: p.keyYes
    readonly property color meterLow: p.meterLow
    readonly property color meterMid: p.meterMid
    readonly property color meterHigh: p.meterHigh
    readonly property color mute: p.mute
    readonly property color solo: p.solo
    readonly property color overlay: p.overlay
    readonly property color dialogNo: p.dialogNo
    readonly property color dialogYes: p.dialogYes
    readonly property color listBackground: p.listBackground   // behind list rows, also below the last
    readonly property color dim: p.dim                         // behind dialogs (confirm, value editor)
    readonly property color dimBusy: p.dimBusy                 // behind the busy message
    readonly property color link: p.link                       // links in the help pages

    // Status colours: top bar flags and alerts, MIDI binding of controllers, launcher pads
    readonly property color alert: p.alert
    readonly property color warning: p.warning
    readonly property color flagRecord: p.flagRecord
    readonly property color flagPlay: p.flagPlay
    readonly property color flagMidi: p.flagMidi
    readonly property color flagSeq: p.flagSeq
    readonly property color midiActivity: p.midiActivity
    readonly property color bindChain: p.bindChain    // chain MIDI binding, learning
    readonly property color bindGlobal: p.bindGlobal  // global binding, learning globally
    readonly property color bindXy: p.bindXy          // X-Y touchpad axis
    readonly property color marker: p.marker          // selected launcher pad, what is being moved
    readonly property color textBypassed: p.textBypassed

    // Chain manager: processor blocks by kind, the pinned chains' background, lines
    readonly property color nodeMidi: p.nodeMidi
    readonly property color nodeSynth: p.nodeSynth
    readonly property color nodeAudio: p.nodeAudio
    readonly property color nodeSpecial: p.nodeSpecial
    readonly property color nodeOther: p.nodeOther
    readonly property color pinnedBackground: p.pinnedBackground
    readonly property color divider: p.divider
    readonly property color connector: p.connector

    // Pattern editor: grid rows (black keys darker) and lines, notes (hue; lighter with
    // velocity), the selected block, CC bars; toolbar buttons switched on, recording
    readonly property color gridRow: p.gridRow
    readonly property color gridRowDark: p.gridRowDark
    readonly property color gridRowLine: p.gridRowLine
    readonly property color gridBar: p.gridBar
    readonly property color gridBeat: p.gridBeat
    readonly property color gridStep: p.gridStep
    readonly property real noteHue: p.noteHue
    readonly property color noteFrame: p.noteFrame
    readonly property color selectionFill: p.selectionFill
    readonly property color selectionFrame: p.selectionFrame
    readonly property color ccBar: p.ccBar
    readonly property color ccBarCurrent: p.ccBarCurrent
    readonly property color buttonOn: p.buttonOn
    readonly property color buttonRecord: p.buttonRecord

    // Controller page widgets (envelope, filter, waveform, plugin meters): background, curve
    // line and fill, grid, waveform fill and the part outside the crop range
    readonly property color widgetBackground: p.widgetBackground
    readonly property color widgetLine: p.widgetLine
    readonly property color widgetFill: p.widgetFill
    readonly property color widgetGrid: p.widgetGrid
    readonly property color widgetWave: p.widgetWave
    readonly property color widgetOutside: p.widgetOutside

    // Outlines: frame around panels, frameActive around the current/active one
    readonly property color frame: p.frame
    readonly property color frameActive: p.frameActive
    readonly property real frameWidth: p.frameWidth

    // Shapes: corner cut of panels (0: rectangles), of large panels, and their radius when uncut
    readonly property real cut: p.cut
    readonly property real cutLarge: p.cutLarge
    readonly property real radius: p.radius

    // Type: fontFamily for titles, list entries and keys; textFamily for small and body text
    // ("" in a palette: Qt's default font); caps puts titles and labels in upper case
    readonly property string fontFamily: p.fontFamily
    readonly property string textFamily: p.textFamily !== "" ? p.textFamily : Qt.application.font.family
    readonly property int fontWeight: p.fontWeight
    readonly property bool caps: p.caps
    readonly property real letterSpacing: p.letterSpacing
    readonly property real fontScale: p.fontScale

    property QtObject classic: QtObject {
        readonly property color background: "#000000"
        readonly property color panel: "#3a424d"
        readonly property color panelHighlight: "#2a323d"
        readonly property color text: "#ffffff"
        readonly property color textOff: "#e0e0e0"
        readonly property color disabled: "#808080"
        readonly property color select: "#ff0000"
        readonly property color selectText: "#ffffff"
        readonly property color keyBackground: "#1e2631"
        readonly property color keyText: "#2b7fff"
        readonly property color keyBack: "#ff3030"
        readonly property color keyYes: "#30e030"
        readonly property color meterLow: "#00b000"
        readonly property color meterMid: "#ffff00"
        readonly property color meterHigh: "#ff0000"
        readonly property color mute: "#ff4000"
        readonly property color solo: "#00b0ff"
        readonly property color overlay: "#e0202830"
        readonly property color dialogNo: "#802020"
        readonly property color dialogYes: "#208020"
        readonly property color listBackground: "#3a424d"
        readonly property color dim: "#d0000000"
        readonly property color dimBusy: "#c0000000"
        readonly property color link: "#5ab4f0"
        readonly property color alert: "#ff0000"
        readonly property color warning: "#ff9000"
        readonly property color flagRecord: "#b00000"
        readonly property color flagPlay: "#00c000"
        readonly property color flagMidi: "#ff00ff"
        readonly property color flagSeq: "#ff9000"
        readonly property color midiActivity: "#19b1f7"
        readonly property color bindChain: "#00c000"
        readonly property color bindGlobal: "#f0f000"
        readonly property color bindXy: "#ff9000"
        readonly property color marker: "#ffff00"
        readonly property color textBypassed: "#b0b0b0"
        readonly property color nodeMidi: "#805050"
        readonly property color nodeSynth: "#32a893"
        readonly property color nodeAudio: "#505080"
        readonly property color nodeSpecial: "#708050"
        readonly property color nodeOther: "#505050"
        readonly property color pinnedBackground: "#333333"
        readonly property color divider: "#666666"
        readonly property color connector: "#aaaaaa"
        readonly property color gridRow: "#323a45"
        readonly property color gridRowDark: "#262c34"
        readonly property color gridRowLine: "#1c2128"
        readonly property color gridBar: "#8090a0"
        readonly property color gridBeat: "#566270"
        readonly property color gridStep: "#2a3038"
        readonly property real noteHue: 0.58
        readonly property color noteFrame: "#e0f0ff"
        readonly property color selectionFill: "#305a9ef0"
        readonly property color selectionFrame: "#5a9ef0"
        readonly property color ccBar: "#305070"
        readonly property color ccBarCurrent: "#4080c0"
        readonly property color buttonOn: "#206030"
        readonly property color buttonRecord: "#a02020"
        readonly property color widgetBackground: "#101418"
        readonly property color widgetLine: "#5a9ef0"
        readonly property color widgetFill: "#203a58"
        readonly property color widgetGrid: "#2e4a2e"
        readonly property color widgetWave: "#4a90d0"
        readonly property color widgetOutside: "#181e24"
        readonly property color frame: "transparent"
        readonly property color frameActive: "#ffffff"
        readonly property real frameWidth: 0
        readonly property real cut: 0
        readonly property real cutLarge: 0
        readonly property real radius: 3
        readonly property string fontFamily: "Audiowide"
        readonly property string textFamily: ""
        readonly property int fontWeight: Font.Normal
        readonly property bool caps: false
        readonly property real letterSpacing: 0
        readonly property real fontScale: 1.0
    }

    property QtObject galactica: QtObject {
        readonly property color background: "#0a0b0c"      // deck
        readonly property color panel: "#2a2c2d"           // gun-metal hull plate
        readonly property color panelHighlight: "#18191a"  // recessed plate
        readonly property color text: "#f0ad3c"            // CIC console amber
        readonly property color textOff: "#a98a55"         // dimmed amber
        readonly property color disabled: "#5d574c"
        readonly property color select: "#e09a2c"          // amber bar ...
        readonly property color selectText: "#140f06"      // ... with dark type
        readonly property color keyBackground: "#202223"
        readonly property color keyText: "#e8a73c"
        readonly property color keyBack: "#e8432e"         // alert red
        readonly property color keyYes: "#8fc46a"
        readonly property color meterLow: "#8fc46a"
        readonly property color meterMid: "#f0b030"
        readonly property color meterHigh: "#e8432e"
        readonly property color mute: "#c8321f"
        readonly property color solo: "#4f9cc8"
        readonly property color overlay: "#f0161718"
        readonly property color dialogNo: "#8a2418"
        readonly property color dialogYes: "#4d6e33"
        readonly property color listBackground: "#18191a"  // recessed: the plates stand out
        readonly property color dim: "#d8050506"
        readonly property color dimBusy: "#c8050506"
        readonly property color link: "#ffd27a"
        readonly property color alert: "#e8432e"
        readonly property color warning: "#f0b030"
        readonly property color flagRecord: "#e8432e"
        readonly property color flagPlay: "#8fc46a"
        readonly property color flagMidi: "#c890c0"
        readonly property color flagSeq: "#f0b030"
        readonly property color midiActivity: "#4f9cc8"
        readonly property color bindChain: "#8fc46a"
        readonly property color bindGlobal: "#ffd27a"
        readonly property color bindXy: "#f0b030"
        readonly property color marker: "#f0ad3c"
        readonly property color textBypassed: "#7d6a4a"
        readonly property color nodeMidi: "#5a3a30"
        readonly property color nodeSynth: "#5c4a24"
        readonly property color nodeAudio: "#2f3a44"
        readonly property color nodeSpecial: "#3f4630"
        readonly property color nodeOther: "#2a2c2d"
        readonly property color pinnedBackground: "#18191a"
        readonly property color divider: "#5f5b50"
        readonly property color connector: "#a98a55"
        readonly property color gridRow: "#2a2c2d"
        readonly property color gridRowDark: "#1d1e1f"
        readonly property color gridRowLine: "#111213"
        readonly property color gridBar: "#a98a55"
        readonly property color gridBeat: "#5f5b50"
        readonly property color gridStep: "#333436"
        readonly property real noteHue: 0.105                  // amber
        readonly property color noteFrame: "#ffe2a8"
        readonly property color selectionFill: "#30f0ad3c"
        readonly property color selectionFrame: "#f0ad3c"
        readonly property color ccBar: "#6a5228"
        readonly property color ccBarCurrent: "#c08a30"
        readonly property color buttonOn: "#4d6e33"
        readonly property color buttonRecord: "#8a2418"
        readonly property color widgetBackground: "#111213"
        readonly property color widgetLine: "#f0ad3c"
        readonly property color widgetFill: "#4a3418"
        readonly property color widgetGrid: "#3a3832"
        readonly property color widgetWave: "#d09030"
        readonly property color widgetOutside: "#1d1e1f"
        readonly property color frame: "#5f5b50"           // steel / khaki edge
        readonly property color frameActive: "#f0ad3c"
        readonly property real frameWidth: 1.5
        readonly property real cut: 7
        readonly property real cutLarge: 12
        readonly property real radius: 0
        readonly property string fontFamily: "Khand"
        readonly property string textFamily: "Khand"
        readonly property int fontWeight: Font.Medium
        readonly property bool caps: true
        readonly property real letterSpacing: 1.2
        readonly property real fontScale: 1.15             // Khand is condensed, with a small x-height
    }
}
