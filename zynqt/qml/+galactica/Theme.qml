pragma Singleton
import QtQuick
import ".."

// galactica: a battlestar CIC console: gun-metal plates with clipped corners and steel outlines,
// amber console text in a condensed face (Khand, upper case), an amber selection bar, red alerts.
ThemeBase {
    tintIcons: true
    listSpacing: 2
    tileMargin: 3
    infoBackground: panelHighlight
    dialogFrame: frameActive
    xyFrame: frame
    keyboardBackground: overlay
    keyboardHighlight: select
    keyboardHighlightText: selectText
    keyLineHeight: 0.85
    background: "#0a0b0c"      // deck
    panel: "#2a2c2d"           // gun-metal hull plate
    panelHighlight: "#18191a"  // recessed plate
    text: "#f0ad3c"            // CIC console amber
    textOff: "#a98a55"         // dimmed amber
    disabled: "#5d574c"
    select: "#e09a2c"          // amber bar ...
    selectText: "#140f06"      // ... with dark type
    keyBackground: "#202223"
    keyText: "#e8a73c"
    keyBack: "#e8432e"         // alert red
    keyYes: "#8fc46a"
    meterLow: "#8fc46a"
    meterMid: "#f0b030"
    meterHigh: "#e8432e"
    mute: "#c8321f"
    solo: "#4f9cc8"
    overlay: "#f0161718"
    dialogNo: "#8a2418"
    dialogYes: "#4d6e33"
    listBackground: "#18191a"  // recessed: the plates stand out
    dim: "#d8050506"
    dimBusy: "#c8050506"
    link: "#ffd27a"
    alert: "#e8432e"
    warning: "#f0b030"
    flagRecord: "#e8432e"
    flagPlay: "#8fc46a"
    flagMidi: "#c890c0"
    flagSeq: "#f0b030"
    midiActivity: "#4f9cc8"
    bindChain: "#8fc46a"
    bindGlobal: "#ffd27a"
    bindXy: "#f0b030"
    marker: "#f0ad3c"
    textBypassed: "#7d6a4a"
    nodeMidi: "#5a3a30"
    nodeSynth: "#5c4a24"
    nodeAudio: "#2f3a44"
    nodeSpecial: "#3f4630"
    nodeOther: "#2a2c2d"
    pinnedBackground: "#18191a"
    divider: "#5f5b50"
    connector: "#a98a55"
    gridRow: "#2a2c2d"
    gridRowDark: "#1d1e1f"
    gridRowLine: "#111213"
    gridBar: "#a98a55"
    gridBeat: "#5f5b50"
    gridStep: "#333436"
    noteHue: 0.105                  // amber
    // playhead: a radar sweep, a bright line and a long amber afterglow
    playheadColor: "#ffd27a"
    playheadTailColor: "#f0ad3c"
    playheadTailSteps: 3
    playheadTailOpacity: 0.5
    playheadTailCurve: 2.2
    noteFrame: "#ffe2a8"
    selectionFill: "#30f0ad3c"
    selectionFrame: "#f0ad3c"
    ccBar: "#6a5228"
    ccBarCurrent: "#c08a30"
    buttonOn: "#4d6e33"
    buttonRecord: "#8a2418"
    widgetBackground: "#111213"
    widgetLine: "#f0ad3c"
    widgetFill: "#4a3418"
    widgetGrid: "#3a3832"
    widgetWave: "#d09030"
    widgetOutside: "#1d1e1f"
    dialogText: "#f0ad3c"
    separator: "#18191a"
    separatorText: "#a98a55"
    frame: "#5f5b50"           // steel / khaki edge
    frameActive: "#f0ad3c"
    frameWidth: 1.5
    cut: 7
    cutLarge: 12
    radius: 0
    fontFamily: "Khand"
    textFamily: "Khand"
    fontWeight: Font.Medium
    caps: true
    letterSpacing: 1.2
    fontScale: 1.15             // Khand is condensed, with a small x-height
    // Chain control's grid: console bars in segments, amber and the status colours by section
    controlCellSegments: 12
    controlGridColors: ["#f0ad3c", "#4f9cc8", "#8fc46a", "#e8432e", "#c890c0"]
}
