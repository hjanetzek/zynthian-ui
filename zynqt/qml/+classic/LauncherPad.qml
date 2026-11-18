import QtQuick
import ".."

// A launcher pad (zynthian_gui_launcher_pad): sequence name, play state, repeat mode, length;
// the main strip's pads are the phrases (with tempo, time signature, loops)
Rectangle {
    id: pad

    property var launcher: zyn.launcherModel
    // Reloaded on a change while the launcher is shown, else when it is shown next
    property bool shown: true

    property int chainId
    property int phrase
    property bool isMain
    property bool selected
    property int fontPt: 17     // the mixer's font size (tk)
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

    // Chains without a sequencer: no pads (as tk)
    visible: info.hasSequence !== false || isMain
    color: info.color || Theme.panelHighlight
    border.color: selected ? Theme.marker : Theme.panel
    border.width: selected ? 2 : 1

    // Phrase loops (main strip)
    Repeater {
        model: pad.info.loops || []
        Item {
            required property var modelData
            required property int index
            x: 2 + index * 7
            width: 5
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
                x: 7; y: 2; text: modelData.text; color: Theme.text; font.pixelSize: 11
            }
        }
    }
    Text {
        anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 3
        anchors.leftMargin: (pad.info.loops || []).length ? 3 + 7 * pad.info.loops.length : 3
        // ⏹ / ▶ as forkawesome glyphs (the text faces would take them from the colour emoji font)
        readonly property string st: pad.info.state_text || ""
        readonly property string glyph: st === "\u23f9" ? "\uf04d" : (st === "\u25b6" ? "\uf04b" : "")
        text: glyph || st; color: pad.info.state_color || Theme.text; font.pixelSize: glyph ? 11 : 13
        font.family: glyph ? "forkawesome" : Qt.application.font.family
    }
    Text {
        anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 3
        visible: pad.isMain   // the phrases' tempo (as tk)
        text: pad.info.tempo_text || ""; color: pad.info.text_color || Theme.text; font.pixelSize: 11
    }
    Text {
        anchors.centerIn: parent
        width: parent.width - 8
        horizontalAlignment: Text.AlignHCenter
        elide: Text.ElideRight
        text: pad.info.title || ""
        color: pad.info.text_color || Theme.text
        font.pixelSize: (pad.info.title || "").length > 3 ? 14 : 18
        font.family: Theme.fontFamily
    }
    Text {
        anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: 3
        text: pad.info.mode_text || ""; color: pad.info.mode_color || Theme.text; font.pixelSize: 12
    }
    Text {
        anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 3
        text: pad.info.timesig_text || ""; color: pad.info.text_color || Theme.text; font.pixelSize: 12
    }
    TapHandler {
        onTapped: pad.launcher.tapPad(pad.chainId, pad.phrase)
        onLongPressed: pad.launcher.longPressPad(pad.chainId, pad.phrase)
    }
}
