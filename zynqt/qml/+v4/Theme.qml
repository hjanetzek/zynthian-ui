pragma Singleton
import QtQuick
import ".."

// v4: the zynthian V4 kits (3.5" ZynScreen, 480x320, two knobs on each side of the screen), on
// top of tk (a copy of zynqt/qml/Theme.qml, Theme.qml files don't extend each other; keep the
// two in step). docs/qt-theme-v4.md has the design.
ThemeBase {
    id: t
    // F as Tk on a V4 kit: ZYNTHIAN_UI_FONT_SIZE (14 in zynthian_envars_V4.sh) unscaled. Nura's
    // session sets ZYNTHIAN_UI_SCALE=auto (the height / 600, for HDMI screens and desktops), which
    // would halve it at 320 px; a number given as the scale still applies.
    tkAutoScale: false
    // The dialogs over the screens (Main.qml: confirm, value editor, help, busy, info; the keyboard) are sized for
    // 800 px and more
    dialogScale: 0.6
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
    // Controller page widgets in Tk's colours: envelope / filter outline color_on, filled
    // color_variant(on, -90), the filter grid color_variant(hl, -60) over the curve; spectrum and
    // graphic EQ bars color_hl with color_on ticks; the chord in color_ml; the waveform color_hl
    // with a color_on cursor, color_ml loop markers, color_variant(panel_bg, 25) outside the crop
    // range (no crop lines); AIDA-X meters with green / yellow / red zones
    widgetBackground: tkColor("bg", "#000000")
    widgetLine: tkColor("on", "#ff0000")
    widgetFill: tkVariant(tkColor("on", "#ff0000"), -90)
    widgetGrid: tkVariant(tkColor("hl", "#00c000"), -60)
    widgetGridOnTop: true
    widgetBar: tkColor("hl", "#00c000")
    widgetPeak: tkColor("on", "#ff0000")
    widgetBarInset: 0.5   // Tk: the bars' black outlines
    widgetZero: tkColor("tx_off", "#e0e0e0")
    widgetLabel: tkColor("tx", "#ffffff")
    widgetAxis: tkColor("tx_off", "#e0e0e0")
    widgetAxisCentre: tkColor("tx_off", "#e0e0e0")
    widgetHighlight: tkColor("ml", "#f0f000")
    widgetWave: tkColor("hl", "#00c000")
    widgetOutside: tkVariant(tkColor("panel_bg", "#3a424d"), 25)
    widgetCursor: tkColor("on", "#ff0000")
    widgetCrop: "transparent"
    widgetLoop: tkColor("ml", "#f0f000")
    widgetBeat: tkVariant(tkColor("tx", "#ffffff"), -80)
    widgetBeatStrong: tkColor("tx", "#ffffff")
    widgetMeterZones: true
    widgetMeterLow: "#008000"    // Tk's "green", "yellow", "red", "grey"
    widgetMeterMid: "#ffff00"
    widgetMeterHigh: "#ff0000"
    widgetMeterOff: "#bebebe"
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
    infoWidth: 0.23           // Tk's V4 ctrl_width
    // zynthian_gui_engine's layout: categories 0.21, list 0.5, info 0.29 of the width
    categoryWidth: 0.21
    categoryInfoWidth: 0.29
    gridSpacing: 1 / 20
    gridPlaceholders: false
    // One preset list with all banks under section titles; the BACK knob moves from bank to
    // bank (docs/qt-theme-v4.md)
    flatPresetList: true
    // zynthian_gui_config.main_menu_columns: configured, else 3 on V5 / Z2 or below 800 px, else 4
    mainMenuColumns: _cfg && _cfg.mainMenuColumns > 0 ? _cfg.mainMenuColumns : (screenWidth < 800 || (_cfg && _cfg.v5) ? 3 : 4)
    addChainColumns: 3
    gridBackground: tkColor("panel_bg", "#3a424d")
    // zynthian_gui_selector_info.update_info: min(max(0.7 F, side width // 16), F) points
    readonly property int _infoSideWidth: Math.floor(infoWidth * (screenWidth - (keypadShown ? keypadWidth : 0)))
    infoTextSize: tkPx(Math.min(Math.max(Math.floor(0.7 * f), Math.floor(_infoSideWidth / 16)), f))
    // Pattern editor (zynthian_gui_pated_notes): no row bands, row lines GRID_LINE_WEAK, the tonic's
    // GRID_LINE_STRONG; step lines: bars white, beats grey, steps dark; notes grey by velocity
    // (noteHue -1), the block a red frame
    gridRow: "transparent"
    gridRowDark: "transparent"
    gridRowLine: "#505050"
    gridRowLineTonic: "#a0a0a0"
    gridBar: "#ffffff"
    gridBeat: "#a0a0a0"
    gridStep: "#505050"
    gridBarWidth: 1
    noteHue: -1
    selectionFill: "transparent"
    selectionFrame: select
}
