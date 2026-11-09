// The chain manager's geometry and node look (split out of ChainManagerScreen: a theme overrides
// it, e.g. +tk/ChainManagerMetrics.qml). screenWidth / screenHeight: the screen's area.
import QtQuick

QtObject {
    property real screenWidth: 800
    property real screenHeight: 480
    property color background: "transparent"

    property int blockWidth: 150
    property int blockHeight: 56
    property int hSpacing: 16
    property int vSpacing: 20
    // The view's margins, and the first node's position in its chain's column
    property int marginLeft: 8
    property int marginTop: 8
    property int nodeX: hSpacing / 2
    property int nodeY: vSpacing / 2
    // Columns (dividers, the pinned chains' background) down to the bottom of the view; else as
    // high as the longest chain
    property bool fullHeight: true
    // Node text: Label sizes, shrunk to fit the block (fitText), the active chain's title bold
    property real textSize: 15
    property real chainTextSize: 18
    property bool fitText: true
    property bool boldActiveChain: true
    property bool displayFont: false     // Theme.fontFamily (Label title) instead of the text face
    property color selectColor: Theme.select
    property int selectWidth: 3
}
