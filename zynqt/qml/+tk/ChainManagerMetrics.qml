// tk: zynthian_gui_chain_manager's geometry (update_layout, _draw_graph): blocks 2·(W//12) ×
// 2·(H//16), spacings from the block size, the first node H_SPACING//2 down (sic), the canvas'
// scroll region as margins, columns as high as the longest chain, text in the display
// font at 0.026·H points (wrapped, not shrunk), a white 2 px selection outline.
import QtQuick
import ".."

QtObject {
    property real screenWidth: 800
    property real screenHeight: 480
    property color background: Theme.panel      // the canvas: color_panel_bg

    property int blockWidth: 2 * Math.floor(screenWidth / 12)
    property int blockHeight: 2 * Math.floor(screenHeight / 16)
    property int hSpacing: 2 * Math.floor(blockWidth / 28)
    property int vSpacing: 2 * Math.floor(blockHeight / 8)
    // The scroll region starts at the canvas' bbox (Tk adds ~2 px to it) minus 5 above
    property int marginLeft: 2
    property int marginTop: 7
    property int nodeX: hSpacing / 2
    property int nodeY: Math.floor(hSpacing / 2)
    property bool fullHeight: false
    property real textSize: Theme.tkPx(Math.floor(0.026 * screenHeight))
    property real chainTextSize: textSize
    property bool fitText: false
    property bool boldActiveChain: false
    property bool displayFont: true
    property color selectColor: "#ffffff"
    property int selectWidth: 2
}
