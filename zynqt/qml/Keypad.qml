// V5 touch keypad, layout "v5_keypad_left" of zynthian_gui_touchkeypad_v5: two columns of five
// keys on the left, ten keys along the bottom. Keys send switch events (zynswitch <key+4>,P/R)
// like the Tk keypad and hardware kits, so the wiring configuration maps them to CUIAs.
import QtQuick

Item {
    id: root

    property int keyHeight: 100
    property bool translucent: false   // overlay: the (blurred) screen shows through

    signal keyPressed      // any key (the overlay keypad stays while keys are used)

    // Labels by key index (zynthian_gui_touchkeypad_v5.buttons)
    readonly property var labels: ["OPT\nADMIN", "MIX\nLEVEL", "CTRL\nPRSET", "ZS3\nSHOT",
        "ALT\nHELP", "METRO", "PAD\nSTEP", "F1", "REC", "STOP", "PLAY", "F2", "BACK\nNO", "▲",
        "SEL\nYES", "F3", "◀", "▼", "▶", "F4"]
    // F1-F4 while their LED shows ALT (zynthian_gui_touchkeypad_v5: the ALT labels)
    readonly property var altLabels: ({ 7: "F5", 11: "F6", 15: "F7", 19: "F8" })
    // Layouts v5_keypad_left / v5_keypad_right (rightHanded: the columns on the right, the
    // arrows at the right end of the bottom row)
    property bool rightHanded: false
    readonly property var sideLayout: rightHanded ? [0, 1, 2, 6, 5, 3, 12, 14, 13, 4] : [0, 1, 2, 6, 5, 3, 12, 14, 4, 13]
    readonly property var bottomLayout: rightHanded ? [7, 11, 15, 19, 8, 9, 10, 16, 17, 18]
                                                    : [16, 17, 18, 8, 9, 10, 7, 11, 15, 19]

    Grid {
        id: side

        columns: 2
        width: parent.width
        height: parent.height - root.keyHeight
        Repeater {
            model: root.sideLayout
            Key {
                required property int modelData
                key: modelData
                width: side.width / 2
                height: side.height / 5
            }
        }
    }

    Row {
        id: bottomRow

        y: parent.height - root.keyHeight
        // The whole UI's width (right-handed: from its left edge); Theme.screenWidth is Main.qml's
        // rotated UI item, not the window, when ZYNTHIAN_UI_ROTATION turns it sideways
        x: root.rightHanded ? root.width - width : 0
        width: Theme.screenWidth
        height: root.keyHeight
        Repeater {
            model: root.bottomLayout
            Key {
                required property int modelData
                key: modelData
                width: bottomRow.width / 10
                height: bottomRow.height
            }
        }
    }

    component Key: Item {
        id: k

        property int key
        // Enterprise: filled keys, BACK red, SEL and CTRL green, the others in shades of amber
        readonly property color fill: k.key === 12 ? Theme.keyBack
                                      : (k.key === 14 || k.key === 2 ? Theme.keyYes
                                         : (Theme.keyFills.length ? Theme.keyFills[k.key % Theme.keyFills.length] : Theme.keyBackground))

        KeyPlate {
            anchors.fill: parent
            fill: k.fill
            pressed: tap.pressed
            translucent: root.translucent
        }

        KeyFace {
            anchors.fill: parent
            key: k.key
            label: zyn.keypadLeds.altLabels[k.key] && root.altLabels[k.key] ? root.altLabels[k.key] : root.labels[k.key]
        }

        TapHandler {
            id: tap
            gesturePolicy: TapHandler.ReleaseWithinBounds
            onPressedChanged: { zyn.pushSwitch(k.key, pressed); root.keyPressed() }
        }
    }
}
