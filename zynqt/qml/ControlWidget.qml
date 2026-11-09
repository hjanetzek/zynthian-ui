// The controller page's widget (zynthian_gui_control's widgets): waveform of audio file
// processors, envelope, filter, plugin widgets ...
import QtQuick

Item {
    id: root
    property var cc: zyn.chainControl
    visible: cc.widgetType !== ""

    WaveformView {
        anchors.fill: parent
        visible: root.cc.widgetType === "audio_file"
        view: root.cc.waveform
    }
    EnvelopeView {
        anchors.fill: parent
        visible: root.cc.widgetType === "envelope"
        view: root.cc.envelope
    }
    FilterView {
        anchors.fill: parent
        visible: root.cc.widgetType === "filter"
        view: root.cc.filterView
    }
    PluginWidgetView {
        anchors.fill: parent
        visible: root.cc.widgetType === "plugin"
        view: root.cc.pluginView
    }
    EuclidSeqView {
        anchors.fill: parent
        visible: root.cc.widgetType === "euclid"
        view: root.cc.euclidView
    }
    OrganelleView {
        anchors.fill: parent
        visible: root.cc.widgetType === "organelle"
        view: root.cc.organelleView
    }
    SooperLooperView {
        anchors.fill: parent
        visible: root.cc.widgetType === "sooperlooper"
        view: root.cc.sooperLooperView
    }
}
