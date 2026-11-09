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
    readonly property var sideLayout: [0, 1, 2, 6, 5, 3, 12, 14, 4, 13]
    readonly property var bottomLayout: [16, 17, 18, 8, 9, 10, 7, 11, 15, 19]

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
        width: Window.window ? Window.window.width : 960
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

        // Classic: square keys with a 1 px gap; galactica: plates with clipped corners;
        // enterprise: filled pills (wide keys) or rounded plates. In the overlay translucent,
        // the blurred screen showing through.
        Panel {
            anchors.fill: parent
            anchors.margins: Theme.isGalactica ? 2 : (Theme.keyFilled ? 3 : 0)
            button: Theme.keyFilled && width > height
            color: {
                const c = Theme.keyFilled ? (tap.pressed ? Qt.lighter(k.fill, 1.25) : k.fill)
                                          : (tap.pressed ? Qt.lighter(Theme.keyBackground, 1.8) : Theme.keyBackground)
                return root.translucent ? Qt.rgba(c.r, c.g, c.b, tap.pressed ? 0.85 : (Theme.keyFilled ? 0.7 : 0.55)) : c
            }
            borderColor: Theme.isGalactica ? (tap.pressed ? Theme.frameActive : Theme.frame)
                                           : (Theme.keyFilled ? "transparent"
                                              : (root.translucent ? Qt.rgba(1, 1, 1, 0.15) : Theme.background))
            borderWidth: Theme.isGalactica ? Theme.frameWidth : (Theme.keyFilled ? 0 : 1)
        }

        Label {
            anchors.centerIn: Theme.keyFilled ? undefined : parent
            anchors.right: Theme.keyFilled ? parent.right : undefined
            anchors.bottom: Theme.keyFilled ? parent.bottom : undefined
            anchors.rightMargin: Theme.keyFilled ? (parent.width > parent.height ? parent.height / 2 : 12) : 0
            anchors.bottomMargin: Theme.keyFilled ? 8 : 0
            horizontalAlignment: Theme.keyFilled ? Text.AlignRight : Text.AlignHCenter
            text: root.labels[k.key]
            color: Theme.keyFilled ? Theme.keyFilledText
                                   : (k.key === 12 ? Theme.keyBack : (k.key === 14 || k.key === 2 ? Theme.keyYes : Theme.keyText))
            size: 20
            title: true
            lineHeight: Theme.isGalactica || Theme.keyFilled ? 0.85 : 1.0
        }

        TapHandler {
            id: tap
            gesturePolicy: TapHandler.ReleaseWithinBounds
            onPressedChanged: { zyn.pushSwitch(k.key, pressed); root.keyPressed() }
        }
    }
}
