pragma Singleton
import QtQuick

// zynthian's default colours (zynthian_gui_config)
QtObject {
    readonly property color background: "#000000"
    readonly property color panel: "#3a424d"
    readonly property color panelHighlight: "#2a323d"
    readonly property color text: "#ffffff"
    readonly property color textOff: "#e0e0e0"
    readonly property color disabled: "#808080"
    readonly property color select: "#ff0000"
    readonly property color keyBackground: "#1e2631"
    readonly property color keyText: "#2b7fff"
    readonly property color meterLow: "#00b000"
    readonly property color meterMid: "#ffff00"
    readonly property color meterHigh: "#ff0000"
    readonly property color mute: "#ff4000"
    readonly property color solo: "#00b0ff"
    readonly property string fontFamily: "Audiowide"
}
