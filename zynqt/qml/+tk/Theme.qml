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
    statusLine: tkColor("ml", "#f0f000")
    marker: "#ffff00"
    // Controller page widgets (zynthian_widget_filter / _envelope): the canvas in the background
    // colour, the grid color_variant(hl, -60) drawn over the curve in Tk: here the curve's fill is
    // translucent so the grid shows through (the curve stays blue)
    widgetBackground: tkColor("bg", "#000000")
    widgetGrid: "#008400"
    widgetFill: Qt.rgba(0.30, 0.52, 0.85, 0.45)
    frameActive: "#ffff00"   // grid selection: a yellow outline

    // Shapes and type: square plates, Audiowide
    radius: 0
    fontFamily: "Audiowide"

    // Sizes from F (Tk gives points: tkPx)
    // Tk sizes the top bar once at start, without the keypad (it stays 40 px when shown)
    topBarHeight: screenWidth >= 800 ? Math.floor(screenHeight / 12) : Math.floor(screenHeight / 10)
    // Keypad: W / 5 wide, the bottom row the rest below 5/6 of the height
    keypadWidth: Math.floor(screenWidth / 5)
    keypadKeyHeight: screenHeight - Math.floor(5 * screenHeight / 6)
    titleSize: tkPx(screenWidth >= 800 ? Math.floor(1.5 * f) : Math.floor(1.1 * f))
    listRowHeight: Math.ceil(1.8 * f)
    listTextSize: tkPx(f)
    listTextMargin: 1
    listPadding: Math.round(f / 2)
    infoWidth: 0.25
    gridSpacing: 1 / 20
    // zynthian_gui_config.main_menu_columns: configured, else 3 on V5 / Z2 or below 800 px, else 4
    mainMenuColumns: _cfg && _cfg.mainMenuColumns > 0 ? _cfg.mainMenuColumns : (screenWidth < 800 || (_cfg && _cfg.v5) ? 3 : 4)
    addChainColumns: 3
    gridBackground: tkColor("panel_bg", "#3a424d")
    // zynthian_gui_selector_info.update_info: min(max(0.7 F, side width // 16), F) points
    readonly property int _infoSideWidth: Math.floor(infoWidth * (screenWidth - (keypadShown ? keypadWidth : 0)))
    infoTextSize: tkPx(Math.min(Math.max(Math.floor(0.7 * f), Math.floor(_infoSideWidth / 16)), f))
}
