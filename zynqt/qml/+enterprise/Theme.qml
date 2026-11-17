pragma Singleton
import QtQuick
import ".."

// enterprise: a starship console: orange, blue-gray, mauve and violet pill keys with dark labels,
// pill rows, mauve section headers, a curved frame (the elbow) around the screens.
ThemeBase {
    tintIcons: true
    keyLineHeight: 0.85
    panel: "#16151b"           // dark, cool plates
    panelHighlight: "#000000"
    text: "#fe972c"            // orange
    textOff: "#9aa4a9"         // dim blue-gray
    disabled: "#5b5866"
    select: "#bbc6cb"          // blue-gray pill ...
    selectText: "#000000"      // ... with black type
    keyBackground: "#1f1d27"
    keyText: "#fe972c"
    keyBack: "#cf6660"         // coral red
    keyYes: "#6cc98a"          // green, saturation and lightness of the red
    meterLow: "#6cc98a"
    meterMid: "#e5af46"
    meterHigh: "#cf6660"
    mute: "#cf6660"
    solo: "#7e5edb"            // violet
    overlay: "#f0000000"
    dialogNo: "#cf6660"
    dialogYes: "#6cc98a"
    dialogText: "#000000"
    separator: "#8e6790"       // mauve header bar
    separatorText: "#000000"
    listBackground: "#000000"  // pills on black
    dim: "#d8000000"
    dimBusy: "#c8000000"
    link: "#bbc6cb"
    alert: "#cf6660"
    warning: "#e5af46"
    flagRecord: "#cf6660"
    flagPlay: "#6cc98a"
    flagMidi: "#b08bb2"
    flagSeq: "#fe972c"
    midiActivity: "#a48ae6"
    bindChain: "#6cc98a"
    bindGlobal: "#e5af46"
    bindXy: "#fe972c"
    marker: "#bbc6cb"
    textBypassed: "#5b5866"
    nodeMidi: "#3a2a3b"
    nodeSynth: "#3f2a14"
    nodeAudio: "#2a2540"
    nodeSpecial: "#2b3134"
    nodeOther: "#16151b"
    pinnedBackground: "#0d0c10"
    divider: "#5b5866"
    connector: "#9aa4a9"
    gridRow: "#16151b"
    gridRowDark: "#0d0c10"
    gridRowLine: "#000000"
    gridBar: "#9aa4a9"
    gridBeat: "#5b5866"
    gridStep: "#24222c"
    noteHue: 0.085
    noteFrame: "#ffe0c0"
    selectionFill: "#30bbc6cb"
    selectionFrame: "#bbc6cb"
    ccBar: "#5c4a8c"
    ccBarCurrent: "#7e5edb"
    buttonOn: "#4f9a68"
    buttonRecord: "#a84a45"
    widgetBackground: "#0d0c10"
    widgetLine: "#fe972c"
    widgetFill: "#4a2c10"
    widgetGrid: "#24222c"
    widgetWave: "#bbc6cb"
    widgetOutside: "#16151b"
    frameActive: "#bbc6cb"
    radius: 0
    panelRadius: 14
    pillButtons: true
    keyRadius: 0.25
    keyFilled: true
    keyFills: ["#fe972c", "#bbc6cb", "#8e6790", "#7e5edb", "#ffb366",
                                         "#d9e0e3", "#b08bb2", "#a48ae6", "#e5af46", "#fe972c",
                                         "#7e5edb", "#bbc6cb", "#8e6790", "#ffb366", "#a48ae6",
                                         "#d9e0e3", "#fe972c", "#b08bb2", "#bbc6cb", "#7e5edb"]
    elbow: true
    elbowBar: 14
    elbowColor: "#9a72a0"
    barColors: ["#bbc6cb", "#7e5edb", "#e5af46", "#cf6660"]
    fontFamily: "Khand"
    textFamily: "Khand"
    fontWeight: Font.DemiBold
    caps: true
    letterSpacing: 0.6
    fontScale: 1.2
}
