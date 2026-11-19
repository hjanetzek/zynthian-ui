// The controller page's widget (zynthian_gui_control's widgets): waveform of audio file
// processors, envelope, filter, drawbars, plugin widgets ... Each view created when first shown, or
// after the first frame (Deferred), then kept
import QtQuick

Item {
    id: root
    property var cc: zyn.chainControl
    visible: cc.widgetType !== ""

    Deferred {
        anchors.fill: parent
        visible: root.cc.widgetType === "audio_file"
        needed: root.cc.widgetType === "audio_file"
        sourceComponent: Component { WaveformView { view: root.cc.waveform } }
    }
    Deferred {
        anchors.fill: parent
        visible: root.cc.widgetType === "envelope"
        needed: root.cc.widgetType === "envelope"
        sourceComponent: Component { EnvelopeView { view: root.cc.envelope } }
    }
    Deferred {
        anchors.fill: parent
        visible: root.cc.widgetType === "filter"
        needed: root.cc.widgetType === "filter"
        sourceComponent: Component { FilterView { view: root.cc.filterView } }
    }
    Deferred {
        anchors.fill: parent
        visible: root.cc.widgetType === "drawbar"
        needed: root.cc.widgetType === "drawbar"
        sourceComponent: Component { DrawbarView { view: root.cc.drawbarView } }
    }
    Deferred {
        anchors.fill: parent
        visible: root.cc.widgetType === "plugin"
        needed: root.cc.widgetType === "plugin"
        sourceComponent: Component { PluginWidgetView { view: root.cc.pluginView } }
    }
    Deferred {
        anchors.fill: parent
        visible: root.cc.widgetType === "euclid"
        needed: root.cc.widgetType === "euclid"
        sourceComponent: Component { EuclidSeqView { view: root.cc.euclidView } }
    }
    Deferred {
        anchors.fill: parent
        visible: root.cc.widgetType === "organelle"
        needed: root.cc.widgetType === "organelle"
        sourceComponent: Component { OrganelleView { view: root.cc.organelleView } }
    }
    Deferred {
        anchors.fill: parent
        visible: root.cc.widgetType === "sooperlooper"
        needed: root.cc.widgetType === "sooperlooper"
        sourceComponent: Component { SooperLooperView { view: root.cc.sooperLooperView } }
    }
}
