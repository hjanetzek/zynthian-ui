// tk: a launcher pad as zynthian_gui_launcher_pad draws it: a pad without outline (a 2 px yellow one
// when selected), the play mode at the top left, the play state at the top right, the title in
// the middle, the length at the bottom left (phrases: the tempo at the bottom right); the
// phrases' loop indicators in a column left of the pad
import QtQuick
import ".."

Item {
    id: pad

    property var launcher: zyn.launcherModel
    property bool shown: true
    property int chainId
    property int phrase
    property bool isMain
    property bool selected
    property int fontPt: 17          // the mixer's font size (Tk points)
    property var info: ({})

    property bool stale: true
    function reload() { info = pad.launcher.padInfo(chainId, phrase); stale = false }
    function changed() { if (shown) reload(); else stale = true }
    onShownChanged: if (shown && stale) reload()
    onChainIdChanged: changed()
    onPhraseChanged: changed()
    Component.onCompleted: if (shown) reload()
    Connections {
        target: pad.launcher
        function onPadChanged(c, p) { if (c === pad.chainId && p === pad.phrase) pad.changed() }
        function onPadsChanged() { pad.changed() }
    }

    readonly property int loopInfoWidth: isMain ? Math.floor(0.2 * width / 1.2) : 0
    readonly property int lineWidth: Math.floor(0.3 * loopInfoWidth)

    // Loop indicators (phrases)
    Repeater {
        model: pad.isMain ? (pad.info.loops || []) : []
        Item {
            required property var modelData
            required property int index
            x: index * Math.floor(pad.loopInfoWidth / 2)
            width: pad.lineWidth
            height: pad.height
            Rectangle {
                visible: modelData.part !== "bottom"
                width: parent.width; height: parent.height / 2; color: modelData.top
            }
            Rectangle {
                visible: modelData.part !== "top"
                y: parent.height / 2; width: parent.width; height: parent.height / 2; color: modelData.bottom
            }
            Text {
                visible: modelData.text !== ""
                y: parent.height / 2 - 1
                text: modelData.text
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: Theme.tkPx(Math.floor(0.6 * pad.fontPt))
            }
        }
    }

    Rectangle {
        id: body
        // Tk: the rectangle (x, y) .. (x + w - 1, y + h - 1), no outline (outline=""): a 1 px line
        // of the canvas between the pads; the selected one a 2 px yellow outline centred on the edge
        x: pad.loopInfoWidth - (pad.selected ? 1 : 0)
        y: pad.selected ? -1 : 0
        z: pad.selected ? 1 : 0
        width: pad.width - pad.loopInfoWidth - 1 + (pad.selected ? 2 : 0)
        height: pad.height - 1 + (pad.selected ? 2 : 0)
        // Chains without a sequencer: no pads
        visible: pad.info.hasSequence !== false || pad.isMain
        color: pad.info.color || Theme.panel
        border.width: pad.selected ? 2 : 0
        border.color: "#ffff00"

        Text {     // play mode
            x: 4; y: -2
            text: pad.info.mode_text || ""
            color: (pad.isMain ? pad.info.mode_color : pad.info.text_color) || Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.tkPx(Math.floor(0.6 * pad.fontPt))
        }
        Text {     // play state
            anchors.right: parent.right; anchors.rightMargin: 3; y: -3
            // ⏹ would come from the colour emoji font: a plain square
            text: (pad.info.state_text || "").replace("\u23f9", "\u25a0")
            color: pad.info.state_color || Theme.text
            font.family: "DejaVu Sans"
            font.pixelSize: Theme.tkPx(Math.floor(0.6 * pad.fontPt))
        }
        Text {     // title
            anchors.centerIn: parent
            width: parent.width - 4
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            readonly property bool small: (pad.info.title || "").length > 3
            text: pad.info.title || ""
            color: pad.info.text_color || Theme.text
            font.family: small ? "sans-serif" : Theme.fontFamily
            font.pixelSize: Theme.tkPx(Math.floor((small ? 0.65 : 0.8) * pad.fontPt))
        }
        Text {     // length (time signature)
            x: 4; anchors.bottom: parent.bottom
            text: pad.info.timesig_text || ""
            color: pad.info.text_color || Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.tkPx(Math.floor(0.5 * pad.fontPt))
        }
        Text {     // tempo (phrases)
            visible: pad.isMain
            anchors.right: parent.right; anchors.rightMargin: 1; anchors.bottom: parent.bottom
            horizontalAlignment: Text.AlignRight
            text: pad.info.tempo_text || ""
            color: pad.info.text_color || Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.tkPx(Math.floor(0.5 * pad.fontPt))
        }
    }

    TapHandler {
        onTapped: pad.launcher.tapPad(pad.chainId, pad.phrase)
        onLongPressed: pad.launcher.longPressPad(pad.chainId, pad.phrase)
    }
}
