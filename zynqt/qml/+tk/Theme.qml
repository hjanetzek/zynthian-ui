pragma Singleton
import QtQuick
import ".."

// tk: upstream zynthian's Tk UI. Colours from the ZYNTHIAN_UI_COLOR_* environment (defaults as
// zynthian_gui_config), sizes from its font size F (ZYNTHIAN_UI_FONT_SIZE x ZYNTHIAN_UI_SCALE),
// Audiowide. Values measured in the Tk UI: zynthian-stuff ui-parity/REPORT.md, section 5.
ThemeBase {
    id: t
    readonly property int f: tkFontSize

    // Colours
    background: tkColor("bg", "#000000")
    panel: tkColor("panel_bg", "#3a424d")
    panelHighlight: tkColor("panel_hl", "#2a323d")
    text: tkColor("tx", "#ffffff")
    textOff: tkColor("tx_off", "#e0e0e0")
    select: tkColor("on", "#ff0000")
    selectText: tkColor("tx", "#ffffff")
    separator: tkColor("panel_hl", "#2a323d")
    separatorText: tkColor("tx_off", "#e0e0e0")
    listBackground: tkColor("panel_bg", "#3a424d")
    infoBackground: tkColor("bg", "#000000")
    meterLow: "#00c800"
    meterMid: "#c8c800"
    meterHigh: "#f00000"
    mute: "#cc0000"
    solo: "#d0d000"          // the mixer's toggle button
    alert: tkColor("error", "#ff0000")
    warning: tkColor("warn", "#ff9000")
    flagRecord: tkColor("low_on", "#b00000")
    flagPlay: tkColor("hl", "#00c000")
    flagMidi: tkColor("alt", "#ff00ff")
    flagSeq: tkColor("alt2", "#ff9000")
    midiActivity: tkColor("midi", "#19b1f7")
    bindChain: tkColor("hl", "#00c000")
    bindGlobal: tkColor("ml", "#f0f000")
    marker: "#ffff00"
    frameActive: "#ffff00"   // grid selection: a yellow outline

    // Shapes and type: square plates, Audiowide
    radius: 0
    fontFamily: "Audiowide"

    // Sizes from F (Tk gives points: tkPx)
    topBarHeight: screenWidth >= 800 ? Math.floor(screenHeight / 12) : Math.floor(screenHeight / 10)
    titleSize: tkPx(screenWidth >= 800 ? Math.floor(1.5 * f) : Math.floor(1.1 * f))
    listRowHeight: Math.ceil(1.8 * f)
    listTextSize: tkPx(f)
    listTextMargin: 1
    listPadding: Math.round(f / 2)
    infoWidth: 0.25
    gridSpacing: 1 / 20
    gridBackground: tkColor("panel_bg", "#3a424d")
    infoTextSize: tkPx(f)
}
