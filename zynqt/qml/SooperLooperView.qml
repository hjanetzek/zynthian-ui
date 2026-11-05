// SooperLooper (SooperLooperView): the selected loop's buttons (lit by its state, flashing while
// pending), a row per loop (position, state; tap selects, long press removes, "mute" toggles
// its mute), add loop, and sliders: input level (bar) with threshold (line, drag) and gain
// (marker), feedback, wet, dry (drag)
import QtQuick

Rectangle {
    id: root

    property var view
    readonly property var d: view ? view.data : ({})
    readonly property var loops: d.loops || []
    readonly property real rowH: Math.max(24, (height - 3 * 36 - 8) / 9)
    readonly property color asserted: "#b00000"
    color: "#000000"
    clip: true

    Column {
        anchors.fill: parent
        anchors.margins: 2
        spacing: 1

        // Buttons
        Grid {
            columns: 4
            spacing: 1
            width: parent.width
            Repeater {
                model: root.view ? root.view.buttons : []
                Rectangle {
                    required property string modelData
                    readonly property bool lit: modelData === "reverse" ? root.d.reverse === true : root.d.button === modelData
                    width: (parent.width - 3) / 4
                    height: 36
                    color: tap.pressed ? Theme.keyText : (lit ? root.asserted : Theme.panel)
                    Text {
                        anchors.centerIn: parent
                        text: modelData
                        color: Theme.textOff
                        font.pixelSize: modelData === "substitute" ? 13 : 15
                        font.family: Theme.fontFamily
                    }
                    TapHandler { id: tap; gesturePolicy: TapHandler.ReleaseWithinBounds; onTapped: root.view.press(modelData) }
                }
            }
        }

        // Loops
        Repeater {
            model: root.loops.length
            Row {
                id: loopRow
                required property int index
                readonly property var l: root.loops[index]
                spacing: 1
                width: parent.width
                Rectangle {
                    width: (parent.width - 1) * 0.75
                    height: root.rowH
                    color: ({ pending: "#cc9900", record: root.asserted, off: "#444444", play: "#009900" })[loopRow.l.kind] || "#444444"
                    border.color: index === root.d.selected ? Theme.text : "transparent"
                    border.width: 2
                    Rectangle {   // position
                        x: loopRow.l.len > 0 ? parent.width * loopRow.l.pos / loopRow.l.len : 0
                        width: 2; height: parent.height; color: "#ffff00"
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        x: 6
                        text: loopRow.l.pos.toFixed(1) + "/" + loopRow.l.len.toFixed(1) + " " + loopRow.l.state
                        color: Theme.text
                        font.pixelSize: 15
                    }
                    TapHandler {
                        onTapped: root.view.selectLoop(index)
                        onLongPressed: root.view.askRemove(index)
                    }
                }
                Rectangle {
                    width: (parent.width - 1) * 0.25
                    height: root.rowH
                    color: loopRow.l.mute === "on" || (loopRow.l.mute === "flash" && root.d.flashOn) ? root.asserted : Theme.panel
                    Text { anchors.centerIn: parent; text: "mute"; color: Theme.textOff; font.pixelSize: 15; font.family: Theme.fontFamily }
                    TapHandler { gesturePolicy: TapHandler.ReleaseWithinBounds; onTapped: root.view.toggleMute(index) }
                }
            }
        }
        Rectangle {
            visible: root.d.canAdd === true
            width: parent.width / 2
            height: root.rowH
            color: Theme.panel
            Text { anchors.centerIn: parent; text: "add loop"; color: Theme.textOff; font.pixelSize: 15; font.family: Theme.fontFamily }
            TapHandler { gesturePolicy: TapHandler.ReleaseWithinBounds; onTapped: root.view.addLoop() }
        }

        // Sliders
        Grid {
            columns: 2
            spacing: 1
            width: parent.width
            Slider { label: "input level"; symbol: "rec_thresh"; meter: root.d.inPeak || 0; marker: root.d.inGain || 0 }
            Slider { label: "feedback"; symbol: "feedback" }
            Slider { label: "wet"; symbol: "wet" }
            Slider { label: "dry (monitor)"; symbol: "dry" }
        }
    }

    // A horizontal slider: the controller value as a bar (or, for the input, the meter as a bar
    // and the threshold as a line); drag sideways sets it
    component Slider: Rectangle {
        id: sld
        property string label
        property string symbol
        property real meter: -1
        property real marker: -1
        readonly property real value: (root.d.sliders || {})[symbol] || 0
        width: (parent.width - 1) / 2
        height: root.rowH
        color: Theme.panel
        Rectangle {
            width: parent.width * Math.min(1, sld.meter >= 0 ? sld.meter : sld.value)
            height: parent.height
            color: sld.meter >= 0 ? "#00aa00" : "#2266bb"
        }
        Rectangle {   // threshold
            visible: sld.meter >= 0
            x: parent.width * sld.value - 1
            width: 2; height: parent.height; color: "#ffff00"
        }
        Text {   // gain marker
            visible: sld.marker >= 0
            x: parent.width * sld.marker - width / 2
            text: "▼"; color: "#dd0000"; font.pixelSize: 12
        }
        Text { anchors.verticalCenter: parent.verticalCenter; x: 6; text: sld.label; color: Theme.textOff; font.pixelSize: 15 }
        MouseArea {
            anchors.fill: parent
            preventStealing: true
            property real startX
            property real startValue
            onPressed: (mouse) => { startX = mouse.x; startValue = sld.value }
            onPositionChanged: (mouse) => root.view.setSlider(sld.symbol, startValue + (mouse.x - startX) / width)
        }
    }
}
