// Text in the theme's type: size is the size in the classic theme (the theme scales it), title
// selects the display face (Theme.fontFamily) instead of the text face, body keeps mixed case
// (descriptions, messages).
import QtQuick

Text {
    property real size: 16
    property bool title: false
    property bool body: false

    color: Theme.text
    font.pixelSize: Math.round(size * Theme.fontScale)
    font.family: title ? Theme.fontFamily : Theme.textFamily
    font.weight: title ? Theme.fontWeight : Font.Normal
    font.capitalization: Theme.caps && !body ? Font.AllUppercase : Font.MixedCase
    font.letterSpacing: body ? 0 : Theme.letterSpacing
}
