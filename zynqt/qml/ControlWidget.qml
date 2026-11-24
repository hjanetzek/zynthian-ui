// The controller page's widget (zynthian_gui_control's widgets): waveform of audio file
// processors, envelope, filter, drawbars, plugin widgets ... Each view created when first shown, or
// after the first frame (Deferred), then kept; with lazy (the grid layouts' overlay) only when
// first shown
import QtQuick

Item {
    id: root
    property var cc: zyn.chainControl
    property bool lazy: false
    visible: cc.widgetType !== ""

    Deferred {
        anchors.fill: parent
        property bool seen: false
        onNeededChanged: if (needed) seen = true
        Component.onCompleted: if (needed) seen = true
        allowed: !root.lazy || seen
        visible: root.cc.widgetType === "audio_file"
        needed: root.cc.widgetType === "audio_file"
        sourceComponent: Component { WaveformView { view: root.cc.waveform } }
    }
    Deferred {
        anchors.fill: parent
        property bool seen: false
        onNeededChanged: if (needed) seen = true
        Component.onCompleted: if (needed) seen = true
        allowed: !root.lazy || seen
        visible: root.cc.widgetType === "envelope"
        needed: root.cc.widgetType === "envelope"
        sourceComponent: Component { EnvelopeView { view: root.cc.envelope } }
    }
    Deferred {
        anchors.fill: parent
        property bool seen: false
        onNeededChanged: if (needed) seen = true
        Component.onCompleted: if (needed) seen = true
        allowed: !root.lazy || seen
        visible: root.cc.widgetType === "filter"
        needed: root.cc.widgetType === "filter"
        sourceComponent: Component { FilterView { view: root.cc.filterView } }
    }
    Deferred {
        anchors.fill: parent
        property bool seen: false
        onNeededChanged: if (needed) seen = true
        Component.onCompleted: if (needed) seen = true
        allowed: !root.lazy || seen
        visible: root.cc.widgetType === "drawbar"
        needed: root.cc.widgetType === "drawbar"
        sourceComponent: Component { DrawbarView { view: root.cc.drawbarView } }
    }
    Deferred {
        anchors.fill: parent
        property bool seen: false
        onNeededChanged: if (needed) seen = true
        Component.onCompleted: if (needed) seen = true
        allowed: !root.lazy || seen
        visible: root.cc.widgetType === "plugin"
        needed: root.cc.widgetType === "plugin"
        sourceComponent: Component { PluginWidgetView { view: root.cc.pluginView } }
    }
    Deferred {
        anchors.fill: parent
        property bool seen: false
        onNeededChanged: if (needed) seen = true
        Component.onCompleted: if (needed) seen = true
        allowed: !root.lazy || seen
        visible: root.cc.widgetType === "euclid"
        needed: root.cc.widgetType === "euclid"
        sourceComponent: Component { EuclidSeqView { view: root.cc.euclidView } }
    }
    Deferred {
        anchors.fill: parent
        property bool seen: false
        onNeededChanged: if (needed) seen = true
        Component.onCompleted: if (needed) seen = true
        allowed: !root.lazy || seen
        visible: root.cc.widgetType === "organelle"
        needed: root.cc.widgetType === "organelle"
        sourceComponent: Component { OrganelleView { view: root.cc.organelleView } }
    }
    // A zynthian widget the Qt UI can't show (a user / external widget: Tk code)
    Rectangle {
        anchors.fill: parent
        visible: root.cc.widgetType === "unsupported"
        color: Theme.widgetBackground
        Text {
            anchors.fill: parent
            anchors.margins: 8
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.Wrap
            elide: Text.ElideRight
            text: "This plugin has a zynthian widget the Qt UI can't show:\n" + root.cc.unsupportedWidget
            color: Theme.textOff
            font.pixelSize: Math.max(10, Math.min(16, parent.height / 8))
        }
    }
    Deferred {
        anchors.fill: parent
        property bool seen: false
        onNeededChanged: if (needed) seen = true
        Component.onCompleted: if (needed) seen = true
        allowed: !root.lazy || seen
        visible: root.cc.widgetType === "sooperlooper"
        needed: root.cc.widgetType === "sooperlooper"
        sourceComponent: Component { SooperLooperView { view: root.cc.sooperLooperView } }
    }
}
