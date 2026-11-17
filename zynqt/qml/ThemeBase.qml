import QtQuick

// The theme tokens with classic's values (zynthian's colours, as zynthian_gui_config). Theme.qml
// in this directory is the default theme, tk (ThemeBase with tk's values); +classic/Theme.qml is
// classic (ThemeBase as it is). Each other theme has its own directory, +<name>/, with a Theme.qml
// that sets only the tokens it changes, and the components it draws differently
// (QQmlFileSelector: zynthian_qt_main.py adds ZYNTHIAN_QT_THEME as an extra selector, so
// +<name>/X.qml replaces X.qml; galactica and enterprise also get "classic", so they build on
// +classic/). docs/qt-theming.md has the list.
QtObject {
    // Icons (white line art) tinted in the text colour
    property bool tintIcons: false

    // Colours
    property color background: "#000000"
    property color panel: "#3a424d"
    property color panelHighlight: "#2a323d"
    property color text: "#ffffff"
    property color textOff: "#e0e0e0"
    property color disabled: "#808080"
    property color select: "#ff0000"
    property color selectText: "#ffffff"
    property color keyBackground: "#1e2631"
    property color keyText: "#2b7fff"
    property color keyBack: "#ff3030"
    property color keyYes: "#30e030"
    property color meterLow: "#00b000"
    property color meterMid: "#ffff00"
    property color meterHigh: "#ff0000"
    property color mute: "#ff4000"
    property color solo: "#00b0ff"
    property color overlay: "#e0202830"
    property color dialogNo: "#802020"
    property color dialogYes: "#208020"
    property color listBackground: "#3a424d"   // behind list rows, also below the last
    property color dim: "#d0000000"                         // behind dialogs (confirm, value editor)
    property color dimBusy: "#c0000000"                 // behind the busy message
    property color link: "#5ab4f0"                       // links in the help pages

    // Status colours: top bar flags and alerts, MIDI binding of controllers, launcher pads
    property color alert: "#ff0000"
    property color warning: "#ff9000"
    property color flagRecord: "#b00000"
    property color flagPlay: "#00c000"
    property color flagMidi: "#ff00ff"
    property color flagSeq: "#ff9000"
    property color midiActivity: "#19b1f7"
    property color bindChain: "#00c000"    // chain MIDI binding, learning
    property color bindGlobal: "#f0f000"  // global binding, learning globally
    property color bindXy: "#ff9000"          // X-Y touchpad axis
    property color marker: "#ffff00"          // selected launcher pad, what is being moved
    property color textBypassed: "#b0b0b0"

    // Chain manager: processor blocks by kind, the pinned chains' background, lines
    property color nodeMidi: "#805050"
    property color nodeSynth: "#32a893"
    property color nodeAudio: "#505080"
    property color nodeSpecial: "#708050"
    property color nodeOther: "#505050"
    property color pinnedBackground: "#333333"
    property color divider: "#666666"
    property color connector: "#aaaaaa"
    property color statusLine: "#f0f000"    // status text under a list (MIDI learn waiting)

    // Pattern editor: grid rows (black keys darker) and lines, notes (hue; lighter with
    // velocity), the selected block, CC bars; toolbar buttons switched on, recording
    property color gridRow: "#323a45"
    property color gridRowDark: "#262c34"
    property color gridRowLine: "#1c2128"
    property color gridBar: "#8090a0"
    property color gridBeat: "#566270"
    property color gridStep: "#2a3038"
    property real noteHue: 0.58
    property color noteFrame: "#e0f0ff"
    property color selectionFill: "#305a9ef0"
    property color selectionFrame: "#5a9ef0"
    property color ccBar: "#305070"
    property color ccBarCurrent: "#4080c0"
    property color buttonOn: "#206030"
    property color buttonRecord: "#a02020"

    // Controller page widgets (envelope, filter, waveform, plugin meters): background, curve
    // line and fill, grid, waveform fill and the part outside the crop range
    property color widgetBackground: "#101418"
    property color widgetLine: "#5a9ef0"
    property color widgetFill: "#203a58"
    property color widgetGrid: "#2e4a2e"
    property color widgetWave: "#4a90d0"
    property color widgetOutside: "#181e24"
    property color dialogText: "#ffffff"
    // List section headers ("> MIDI")
    property color separator: "#2a323d"
    property color separatorText: "#e0e0e0"

    // Outlines: frame around panels, frameActive around the current/active one
    property color frame: "transparent"
    property color frameActive: "#ffffff"
    property real frameWidth: 0

    // Shapes: corner cut of panels (0: rectangles), of large panels, and their radius when uncut
    property real cut: 0
    property real cutLarge: 0
    property real radius: 3
    // Rounded themes: corner radius of plates (0: as each component draws it), buttons as pills
    property real panelRadius: 0
    property bool pillButtons: false
    // The keypad keys' corner radius, as a part of the smallest key side of the whole keypad (side
    // and bottom keys alike, so all keys get one radius whatever the screen's aspect ratio; 0.5:
    // the smallest key is a pill). 0: as the theme's KeyPlate draws them.
    property real keyRadius: 0

    // Keypad: filled keys (keyFills by key, BACK in keyBack, SEL and CTRL in keyYes) with dark
    // labels (keyFilledText) at the bottom right
    property bool keyFilled: false
    property var keyFills: []
    property color keyFilledText: "#000000"

    // Frame: an elbow from the top bar down the left of the screens, bar colours of the top bar
    property bool elbow: false
    property real elbowBar: 0
    property color elbowColor: "transparent"
    property var barColors: []

    // Type: fontFamily for titles, list entries and keys; textFamily for small and body text
    // ("" in a palette: Qt's default font); caps puts titles and labels in upper case
    property string fontFamily: "Audiowide"
    property string textFamily: Qt.application.font.family
    property int fontWeight: Font.Normal
    property bool caps: false
    property real letterSpacing: 0
    property real fontScale: 1.0

    // The window (Main.qml sets it), and the Tk UI's font size F derived from it as
    // zynthian_gui_config does (ZYNTHIAN_UI_FONT_SIZE, times ZYNTHIAN_UI_SCALE; "auto": the screen
    // height / 600). Tk gives font sizes in points (96 dpi: 4/3 px); tkPx(n) converts.
    property real screenWidth: 800
    property real screenHeight: 480
    property bool keypadShown: false        // the keypad docked beside / below the screens
    property bool keypadEnabled: true       // false: no on-screen keypad (docked or overlay)
    readonly property var _cfg: typeof zynConfig !== "undefined" ? zynConfig : null
    // false: ZYNTHIAN_UI_SCALE=auto counts as 1 (v4: the font size is made for its small panel)
    property bool tkAutoScale: true
    readonly property real _uiScale: {
        const s = _cfg ? _cfg.uiScale : ""
        if (s === "auto")
            return tkAutoScale ? screenHeight / 600 : 1.0
        const f = parseFloat(s)
        return f > 0 ? f : 1.0
    }
    readonly property int tkFontSize: {
        const f = _cfg && _cfg.fontSize ? _cfg.fontSize : Math.floor(screenWidth / 40)
        return _uiScale !== 1.0 ? Math.max(1, Math.round(f * _uiScale)) : f
    }
    function tkPx(points) { return Math.round(points * 4 / 3) }
    // Tk's colours (ZYNTHIAN_UI_COLOR_*, e.g. tkColor("panel_bg"))
    function tkColor(name, fallback) {
        return _cfg && _cfg.colors && _cfg.colors[name] ? _cfg.colors[name] : fallback
    }

    // Sizes (classic's values)
    property real topBarHeight: 50          // without the enterprise frame
    property real keypadWidth: 192          // the touch keypad's side columns
    property real keypadKeyHeight: 100      // its bottom row
    property real titleSize: 28             // the top bar's title
    property real listRowHeight: 44         // list entries
    property real listTextSize: 24
    property real listTextMargin: 10        // left of the entry's text
    property real listPadding: 0            // around the list, inside its background
    property real infoWidth: 0.28           // the selector's info pane, part of the width
    property real categoryWidth: 0.2        // the engine screen's category list, part of the width
    property real categoryInfoWidth: infoWidth   // the info pane beside a category list
    property real infoTextSize: 16
    property int mainMenuColumns: 0          // 0: the screen's (Python) columns
    property int addChainColumns: 0
    property real gridSpacing: 0            // gaps between grid tiles (part of the width per column)
    property bool gridPlaceholders: true    // grids padded with empty placeholder cells
    // The preset list shows all banks, each under a section title, with their presets (engines
    // with cheap preset lists: sfizz, LV2); a knob moves from bank to bank (v4)
    property bool flatPresetList: false
    property color gridBackground: background

    // Spacing and outlines that differ per theme (values only; structural differences are
    // components in the theme's directory)
    property real listSpacing: 0                    // between list rows and controller pages
    property real tileMargin: 1                     // around grid tiles and list rows
    property color infoBackground: background       // the selector's info pane
    property color dialogFrame: "transparent"       // around dialog buttons and the keyboard
    property color xyFrame: panel                   // around the X-Y pad
    property color keyboardBackground: "#f0101418"  // the on-screen keyboard
    property color keyboardHighlight: "#205080"     // its highlighted key ...
    property color keyboardHighlightText: text      // ... and the label on it
    property real keyLineHeight: 1.0                // keypad labels on two lines
    property real dialogScale: 1.0                  // sizes of the dialogs over the screens (confirm, value editor, help, busy, info)

    // UI rotated by 90/270 in QML (Main.qml, ZYNTHIAN_UI_ROTATION): DragHandlers without a target
    // enable their "disabled" axis then (Qt measures them in window coordinates) and read the drag
    // through localDrag, the drag mapped into their item
    property bool uiSideways: false
    function localDrag(item, centroid) {
        const a = item.mapFromItem(null, centroid.scenePressPosition.x, centroid.scenePressPosition.y)
        const b = item.mapFromItem(null, centroid.scenePosition.x, centroid.scenePosition.y)
        return Qt.point(b.x - a.x, b.y - a.y)
    }
}
