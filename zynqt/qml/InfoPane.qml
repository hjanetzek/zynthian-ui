import QtQuick

// Tk: the icon in a square as wide as the pane (zynthian_gui_selector's info canvas), the text
// below it. Engines (quality >= 0): zynthian_gui_engine's info canvas instead: big quality stars
// and complexity gears (color_on over color_off), the description below in sans-serif 0.8 F.
Rectangle {
    id: pane
    property string icon
    property string info
    property int quality: -1
    property int complexity: -1
    readonly property bool engine: quality >= 0

    color: Theme.infoBackground
    clip: true

    // zynthian_gui_engine.__init__: star_fs = ctrl_width * 0.16 points, x = 0.1 star_fs,
    // y = -0.3 star_fs, the gears 1.2 star_fs lower, the description 1.6 star_fs below them
    readonly property int starPt: Math.floor(width * 0.16)
    readonly property int starX: Math.floor(0.1 * starPt)
    readonly property int starY: Math.trunc(-0.3 * starPt)
    readonly property int gearY: starY + Math.floor(1.2 * starPt)
    readonly property int descrY: gearY + Math.floor(1.6 * starPt)
    // Tk draws the glyphs (from a fallback font) on the line of the theme font (Audiowide):
    // DejaVu Sans' line here, moved down by the difference of the ascents
    FontMetrics {
        id: themeMetrics
        font.family: Theme.fontFamily
        font.pixelSize: Theme.tkPx(pane.starPt)
    }
    FontMetrics {
        id: glyphMetrics
        font.family: "DejaVu Sans"
        font.pixelSize: Theme.tkPx(pane.starPt)
    }
    component Stars: Item {
        property string glyph
        property int count
        x: pane.starX
        Text {
            y: Math.round(themeMetrics.ascent - glyphMetrics.ascent)
            text: parent.glyph.repeat(5)
            color: Theme.tkColor("off", "#5a626d")
            font.family: "DejaVu Sans"
            font.pixelSize: Theme.tkPx(pane.starPt)
        }
        Text {
            y: Math.round(themeMetrics.ascent - glyphMetrics.ascent)
            text: parent.glyph.repeat(Math.max(0, Math.min(5, parent.count)))
            color: Theme.tkColor("on", "#ff0000")
            font.family: "DejaVu Sans"
            font.pixelSize: Theme.tkPx(pane.starPt)
        }
    }
    Stars {
        visible: pane.engine
        y: pane.starY
        glyph: "★"
        count: pane.quality
    }
    Stars {
        visible: pane.engine
        y: pane.gearY
        glyph: "⚙"
        count: pane.complexity
    }
    Text {
        visible: pane.engine
        x: pane.starX
        y: pane.descrY
        width: pane.width - pane.starX
        wrapMode: Text.WordWrap
        text: pane.info
        color: Theme.tkColor("panel_tx", "#ffffff")
        font.family: "DejaVu Sans"
        font.pixelSize: Theme.tkPx(Math.floor(0.8 * Theme.tkFontSize))
    }

    Item {
        id: iconBox
        visible: !pane.engine
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: width
        Image {
            anchors.centerIn: parent
            width: parent.width
            height: width
            fillMode: Image.PreserveAspectFit
            asynchronous: true
            source: pane.icon
        }
    }
    Label {
        visible: !pane.engine
        anchors.top: iconBox.bottom
        anchors.topMargin: 2
        anchors.left: parent.left
        anchors.right: parent.right
        // Tk: the text at the canvas' left edge, wrapped at side_width - 2
        anchors.leftMargin: 2
        anchors.rightMargin: 0
        wrapMode: Text.WordWrap
        text: pane.info
        color: Theme.text
        body: true
        size: Theme.infoTextSize
    }
}
