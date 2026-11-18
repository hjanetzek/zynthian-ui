// What the top bar shows, for every theme's TopBar (shared: a theme's TopBar only places and
// styles it). As Tk's zynthian_gui_base: on the mixer and launcher the snapshot and ZS3 title
// with the tempo (beat | bpb/4 and the bpm); on chain control and the special processors' control
// screens Tk's select path (the processor's preset path); on the pattern editor its title, or
// its edit mode's title shown inverted (set_edit_mode); else the screen's title.
import QtQuick

QtObject {
    id: state

    property string title: ""       // the screen's title (Main.qml: the list's or the screen's)

    readonly property var status: zyn.status
    readonly property bool onMixer: zyn.currentScreen === "mixer" || zyn.currentScreen === "launcher"
    readonly property bool onPatternEditor: zyn.currentScreen === "pattern_editor"
    readonly property bool onControl: ["chain_control", "audio_player", "tempo", "alsa_mixer"].indexOf(zyn.currentScreen) >= 0
    // The pattern editor's edit modes: their title inverted
    readonly property bool inverted: onPatternEditor && zyn.patternEditor.modeTitle !== ""

    readonly property string text: onMixer && status.snapshotTitle ? status.snapshotTitle
        : onControl ? zyn.chainControl.selectPath
        : onPatternEditor ? (inverted ? zyn.patternEditor.modeTitle : zyn.patternEditor.tkTitle)
        : title

    // The tempo, on the mixer and launcher
    readonly property bool tempoShown: onMixer
    readonly property string tempoText: status.beat + "|" + status.bpb + "/4 " + (status.tempo || 0).toFixed(1) + "bpm"
}
