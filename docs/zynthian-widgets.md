# Zynthian UI widgets: reference and Qt support

A *widget* is the graphic view zynthian shows on a processor's chain control page, next to the
four controllers: an envelope, a filter curve, a spectrum, a tuner, a waveform, a looper, …
This is the complete list for zynthian-ui `main` (6fa46dc44: upstream `origin/tomita` plus the
port), with what selects each widget, how to open it, what the Tk UI (upstream) and our Qt UI
show, and whether the plugin or engine is packaged on Nura.

Checked 2026-11-19 in the QEMU compare VMs: the Qt VM (SSH 2252, theme `v4`, 480x320, this
repository's `zynthian-ui` package) and the Tk VM (SSH 2253, nura-builds' `zynthian-ui-tomita`
0_git20261107, which is older than upstream's LV2 widget bundles and the drawbar widget: where
upstream's current Tk code differs, the sections say so). Plugin lists come from a lilv scan in
the Qt VM (`tools/lv2_widget_designations.py`, 527 bundles).

## How a widget is chosen

Upstream: `zynthian_gui_control.set_controller_screen()` and `show_widget()`; the selection
logic is shared with the Qt UI in `zyngui/zynthian_widget_data.py` (`screen_type()`,
`plugin_widget()`).

1. **Page widget, from the page's controllers** (`screen_type(zctrls)`): the four controllers
   of the shown page are checked in page order; the **first** one that has any of these
   attributes decides:
   - `zctrl.envelope` → **envelope**,
   - `zctrl.filter` → **filter**,
   - `zctrl.drawbar` → **drawbar**,
   - a path controller whose file types include wav/aiff/flac/mp3/ogg → **audio file**.

   The attributes come from LV2 port designations (`zynthian_lv2.get_plugin_ports()`,
   `zyngine/zynthian_lv2.py:1338-1362` for ports, `:1513-1537` for property parameters, passed to
   the controller by `zynthian_engine_jalv`, `zynthian_controller.py:215-220`), or from an
   engine's controller definition (`{'envelope': 'attack'}` in FluidSynth, `{'filter':
   'cutoffFrequency'}` in ZynAddSubFX).
2. **Otherwise the engine's widget**: `processor.engine.custom_gui_fpath`, a module
   `zynthian_widget_<name>.py` (Tk calls `engine.refresh_custom_gui()` first, so LV2 widget
   bundles added at runtime are found). Set by:

   | Engine | Widget | Where |
   |---|---|---|
   | Audio player (AP, also the global player) | audio_file | `zynthian_engine_audioplayer.py:77` |
   | Clippy (CL, clip launcher) | audio_file | `zynthian_engine_clippy.py:82` |
   | setBfree (BF) | setbfree | `zynthian_engine_setbfree.py:252` |
   | SooperLooper (SL) | sooperlooper | `zynthian_engine_sooperlooper.py:371` |
   | Tempo (TP, the state manager's tempo processor) | tempo | `zynthian_engine_tempo.py:65` |
   | Internet radio (IR) | inet_radio | `zynthian_engine_inet_radio.py:560` |
   | Pure Data (PD), per preset | organelle / euclidseq | `zynthian_engine_puredata.py:231-249` |
   | jalv (LV2), per plugin | the plugin's `zyngui:widget` UI | `zynthian_engine_jalv.get_custom_gui_fpath()`, `zynthian_lv2.get_plugin_zyngui_widget()` (`zynthian_lv2.py:972-1050`) |

Rules that follow from this:

- Only **processor pages** get a widget: the chain controller pages ("Controllers 1", …) never
  do (`set_controller_screen`: "NOT for chain controllers pages!").
- An engine widget shows on **every page** of that processor that has no page widget (the
  setBfree drawbars, the tuner, … on all their pages).
- Tk shows it in control mode; widgets that ask for it (`hide_on_select_mode()`) hide in select
  mode. Envelope, filter, drawbar and audio file take half the height (`rows //= 2`: the lower
  half of the page list stays); the others replace the page list.
- `MULTI_INSTANCE = True` in a module (Organelle) makes one widget instance per processor.

### LV2 widget bundles (`zyngui:widget`)

Since upstream a1527c99 (2026-11-16, forum topic 13882) an LV2 plugin's widget is declared as an
LV2 UI of class `zyngui:widget` (vocabulary: `lv2/zyngui.lv2/zyngui.ttl`), with `ui:binary`
naming the Python module and `zyngui:apiVersion 1` (`zyngui:help` optional: an HTML help page).
An *extension bundle* adds only the `ui:ui` triple to an existing plugin (it must not declare the
plugin); one bundle can serve several plugins. The built-in bundles in `lv2/`:

| Bundle | Plugin URIs | Module |
|---|---|---|
| `meters-zyngui.lv2` | `http://gareus.org/oss/lv2/meters#spectr30mono`, `#spectr30stereo` | `zynthian_widget_spectr30.py` |
| `tuna-zyngui.lv2` | `http://gareus.org/oss/lv2/tuna#one`, `#mod` | `zynthian_widget_tunaone.py` |
| `gxgraphiceq-zyngui.lv2` | `http://guitarix.sourceforge.net/plugins/gx_graphiceq_#_graphiceq_`, `…/gx_barkgraphiceq_#_barkgraphiceq_` | `zynthian_widget_gxgraphiceq.py` |
| `nam-zyngui.lv2` | `http://github.com/mikeoliphant/neural-amp-modeler-lv2` | `zynthian_widget_nam.py` |
| `aidax-zyngui.lv2` | `http://aidadsp.cc/plugins/aidadsp-bundle/rt-neural-loader` | `zynthian_widget_aidax.py` |
| `chord-analyzer-zyngui.lv2` | `https://dusk-audio.github.io/plugins/chord-analyzer`, `…/chord-analyzer-midi`, `…/chord-analyzer-headless` | `zynthian_widget_chord_analyzer.py` |
| `samplv1-zyngui.lv2` | `http://samplv1.sourceforge.net/lv2` | the shared `zyngui/zynthian_widget_audio_file.py` (see [Audio file](#audio-file-waveform)) |

Before a1527c99 the same mapping was a dict in `zynthian_engine_jalv.plugins_custom_gui`
(the Tk VM's package still has it, with the module `zynthian_widget_GxGraphicEQ.py`), and user
widgets went into `zyngui/widgets_user` (see [User and external widgets](#user-and-external-widgets)).

### Qt UI

`zynqt/screens/control.py` `_set_widget()` applies the same order: `screen_type()` (but a
drawbar page gets no view), then `plugin_widget()`, which maps the engine's widget **module
name** to a QML view if the name is in `zynthian_widget_data.PLUGIN_WIDGETS` (spectr30, tunaone,
gxgraphiceq, nam, aidax, chord_analyzer, tempo, inet_radio, euclidseq, organelle, sooperlooper);
then the audio file view for audio player, Clippy and samplv1 processors. The Qt UI never runs the
Tk modules. `ControlWidget.qml` picks the view by `widgetType`:

| widgetType | QML | Model |
|---|---|---|
| `envelope` | `EnvelopeView.qml` | `zynqt/models/widgets.py` `EnvelopeView` |
| `filter` | `FilterView.qml` | `FilterView` |
| `audio_file` | `WaveformView.qml` | `zynqt/models/audio_file.py` (shared `zyngui/zynthian_audio_file_data.py`) |
| `plugin` | `PluginWidgetView.qml` (kinds bars, tuner, text, aidax, tempo, radio) | `PluginView` |
| `euclid` | `EuclidSeqView.qml` | `EuclidSeqView` (shared `zyngui/zynthian_euclidseq_data.py`) |
| `organelle` | `OrganelleView.qml` | `zynqt/models/organelle.py` (shared `zyngui/zynthian_organelle_data.py`) |
| `sooperlooper` | `SooperLooperView.qml` | `SooperLooperView` (shared `zyngui/zynthian_sooperlooper_data.py`) |

Envelope, filter and audio file take the lower half of the middle column (`widgetHalf` in
`ChainControlScreen.qml`, theme v4 the same); the others replace the page list.

## Overview

| Widget | Trigger | How to open | Tk (upstream) | Qt | Nura package |
|---|---|---|---|---|---|
| [Envelope](#envelope) | port designation `param:delay/attack/hold/decay/sustain/fade/release`; FluidSynth's env. attack/release | MDA JX10 > "Amp Envelope"; Fabla > "Pad 1 - ADSR"; FluidSynth > "envelope/filter" | yes | yes | yes (mda-lv2/mod-mda-lv2, fabla-lv2, amsynth-lv2, MiMi-d, fluidsynth) |
| [Filter](#filter) | `param:cutoffFrequency`, `param:resonance`; ZynAddSubFX's filter cutoff/resonance | MDA JX10 > "Params 2"; amsynth > "Filter 1"; ZynAddSubFX > "main" | yes | yes | yes (same, zynaddsubfx) |
| [Drawbar](#drawbar-and-setbfree) | `param:drawbar` (zynthian-data's patched Calf Organ TTL) | Calf Organ > a drawbar page (ZynthianOS) | yes (since 2026-11-09) | **no** | Calf Organ yes, the patched TTL no |
| [setBfree](#drawbar-and-setbfree) | engine setBfree | setBfree chain, any page | yes (since 2026-11-09) | **no** | setbfree |
| [Audio file](#audio-file-waveform) | audio player, Clippy, samplv1; any page with an audio file path controller | Audio player (chain or the global one); Clippy pad; samplv1 | yes (needs moderngl) | yes | built in; samplv1-lv2 (Tk: no moderngl on Nura) |
| [Spectrum](#spectrum-spectr30) | x42 `meters#spectr30mono/stereo` | Audio effect "1/3 Octave Spectrum Display" | yes | yes | x42-plugins |
| [Tuner](#tuner-tunaone) | x42 `tuna#one`, `tuna#mod` | Audio effect "x42 Instrument Tuner" | yes | yes | x42-plugins (`tuna#one`) |
| [Graphic EQ](#graphic-eq-gxgraphiceq) | `gx_graphiceq`, `gx_barkgraphiceq` | Audio effect "GxGraphicEQ" | yes | yes | guitarix-lv2 |
| [NAM](#nam) | Neural Amp Modeler | Audio effect "Neural Amp Modeler" | yes | yes | neural-amp-modeler-lv2 |
| [AIDA-X](#aida-x) | AIDA-X `rt-neural-loader` | Audio effect "AIDA-X" | yes | yes | aida-x-lv2 |
| [Chord analyzer](#chord-analyzer) | Dusk Audio chord-analyzer, -midi, -headless | MIDI tool "Chord Analyzer Headless" | yes | yes | dusk-audio-juce-lv2 |
| [Tempo](#tempo) | the tempo processor | main menu > Tempo, CUIA `TEMPO` | yes | yes (own layout, decided deviation) | built in |
| [Internet radio](#internet-radio) | engine InternetRadio | Audio generator "Internet Radio" | yes | yes | needs `vlc` (not a dependency) |
| [Euclidean sequencer](#euclidean-sequencer) | Pd preset with `use_euclidseq_widget` | Special > PureData > midi-generative/EuclidSeq6 | yes | yes (small screens: see gaps) | puredata, zynthian-puredata |
| [Organelle](#organelle) | Pd preset path with "organelle", or `use_organelle_widget` | PureData > audio-fx/Cannabits (and 9 more) | yes | yes (knob/switch mapping differs) | puredata, zynthian-puredata |
| [SooperLooper](#sooperlooper) | engine SooperLooper | Audio effect "SooperLooper" | yes | yes (no ALT arrows) | sooperlooper |
| [User widgets](#user-and-external-widgets) | a `zyngui:widget` UI anywhere on LV2_PATH | the plugin's pages | yes (a1527c99) | **no** | folder `~/.local/share/zynthian/plugins/lv2-widgets` |

## Envelope

- **File:** `zyngui/zynthian_widget_envelope.py`; geometry and drag logic shared in
  `zynthian_widget_data.py` (`envelope_*`). Upstream: jofemodo, vangelis, October 2024 (forum
  topic 10269, "New ADSR envelope widget"); delay/hold/fade and curved segments later (riban
  9eef63a8, efb40f48).
- **Shows:** the envelope as a filled polygon: the phases present, each over an equal share of
  the width, in the order delay, attack, hold, decay, sustain, fade, release; attack, decay and
  release drawn as exponential curves; sustain as a level, fade as a slope after it (negative
  fade if its range goes below 0), release from the right edge.
- **Touch:** press near a phase's end selects it (the dragged phase is highlighted), drag:
  time phases (delay, attack, hold, decay) longer to the right, release longer to the left,
  sustain and fade up/down. The knobs work on the page's four controllers as usual.
- **Trigger (page widget):** a controller on the page with an envelope designation:
  `lv2:designation param:delay | param:attack | param:hold | param:decay | param:sustain |
  param:fade | param:release` (`http://lv2plug.in/ns/ext/parameters#…`), or `'envelope':
  '<phase>'` in an engine's controller options. **Which controllers it draws:** all controllers
  with an envelope designation in the **port group** (`pg:group`) of the page's first
  controller (`processor.get_group_zctrls(group_symbol)`), including those on the group's other
  pages. So one designated controller on a page is enough to show the widget, and a group split
  over two pages (MiMi-d's "Loudness Env 1"/"2") shows the whole envelope on both. Missing
  phases are simply left out (FluidSynth draws attack and release only). Envelope wins over
  filter if its controller comes first on the page.
- **How to open:** see [How to see the envelope](#how-to-see-the-envelope) below.
- **Tk:** yes. **Qt:** yes (`EnvelopeView.qml`, same geometry and drag code). Parity: Qt draws
  in fixed blue (`ThemeBase.widgetLine/widgetFill`), Tk in `color_on` with a darker fill (red
  in the default theme); Tk's `show()` divides by the number of envelope controllers (a
  ZeroDivisionError if the page's group has none; Qt guards it).
- **Nura:** see the plugin list.

## Filter

- **File:** `zyngui/zynthian_widget_filter.py` (ronsum, 04a76be9, December 2025); curve and
  drag shared in `zynthian_widget_data.py` (`filter_*`).
- **Shows:** a low-pass response with a resonance peak, 20 Hz–20 kHz on a log scale, −32…+16 dB,
  on a grid.
- **Touch:** an X-Y pad: drag horizontally for cutoff, vertically for resonance (up = more),
  relative to the values at the press.
- **Trigger (page widget):** `lv2:designation param:cutoffFrequency` and/or
  `param:resonance` on a controller of the page (or `'filter': 'cutoffFrequency' |
  'resonance'` in an engine's controllers: ZynAddSubFX). The widget uses the cutoff and
  resonance controllers of the page's port group; either one suffices (no cutoff: drawn at mid
  position; no resonance: no peak). FluidSynth's "filter cutoff"/"filter resonance" have no
  filter attribute: its "envelope/filter" page shows the envelope.
- **How to open:** MDA JX10 > page "Params 2" (its VCF Freq/Reso are ungrouped, so they share
  the default group); amsynth > "Filter 1"; ZynAddSubFX > "main"; MiMi-d > "Filter"; MDA
  RezFilter (audio effect) > its filter page.
- **Tk:** yes. **Qt:** yes (`FilterView.qml`). Parity: colours as for the envelope (Tk red
  fill, Qt blue).

## Drawbar and setBfree

- **Files:** `zyngui/zynthian_widget_drawbar.py` (generic, LV2) and
  `zyngui/zynthian_widget_setbfree.py` (a subclass naming setBfree's `DB 16` … `DB 1`
  controllers). Upstream: niels, zynthian-ui PR 612 (commits ee07890c "Add drawbars to lv2
  engines" and 33d49b9b, merged into vangelis and tomita 2026-11-09, forum topic 13835).
- **Shows:** nine Hammond drawbars (brown 16′ 5⅓′, white, black, with the footage) pulled out by
  the controllers' values; the drawbar ticks of setBfree (0–8 mapped to 127…7) are used as
  interpolation knots, linear controllers (Calf Organ 0.0–8.0) map directly.
- **Touch:** drag a drawbar up/down.
- **Trigger:** setBfree: the engine (every page of a setBfree chain). LV2: a page with a
  controller designated `lv2:designation param:drawbar` (not a standard LV2 parameter: zynthian's
  own); the widget then shows all drawbar controllers of the processor. The only TTL with it is
  zynthian-data's `lv2-custom/calf.lv2/Organ.ttl` (zynthian-data PR 31).
- **How to open:** setBfree chain (Add chain > Instrument > setBfree), page "drawbars 1".
- **Tk:** upstream yes; the Tk VM's 20261107 package predates it (no widget there).
- **Qt:** **no view**: `_set_widget()` drops `drawbar`, and `setbfree` is not in
  `PLUGIN_WIDGETS`, so Qt shows the controllers (knobs "DB 16" …) and nothing else.
- **Nura:** setbfree and calf-lv2 are packaged; the patched Organ TTL is not applied (see
  [Nura packaging](#nura-the-lv2-custom-ttls-are-not-applied)), and Nura's zynthian-data is older than
  that TTL. So on Nura only setBfree can show drawbars, and only in the Tk UI.

## Audio file (waveform)

- **File:** `zyngui/zynthian_widget_audio_file.py` (jofemodo, 8b0151bf, November 2025; OpenGL
  through moderngl/pyopengltk since); shared logic in `zyngui/zynthian_audio_file_data.py`.
- **Shows:** the file's waveform (per channel), crop and loop markers, beat and cue markers,
  the play cursor, an info line (file name, time); zoom, offset and amplitude zoom come from the
  processor's controllers (pages "edit", "cue markers", …).
- **Touch/keys:** mouse wheel zooms; transport CUIAs on this page play/stop/record the file or
  clip (`cuia_toggle_play`, `cuia_stop`, `cuia_toggle_record`), with the LEDs.
- **Trigger:** engines audio player (chain processor and the global player) and Clippy; samplv1
  through its `zyngui:widget` bundle (engine widget on all its pages); and any page with a path
  controller for audio files (`screen_type`, e.g. samplv1's "Params 1" with `P101_SAMPLE_FILE`).
- **How to open:** Add chain > Audio Generator > Audio Player, load a file (Nura's
  zynthian-data has `files/Audio/Oya.mp3`) > page "main"; Clippy: a clip pad in the launcher;
  samplv1 > "Params 1".
- **Tk:** yes, but on Nura the module doesn't load: upstream needs `moderngl` (the 20261107
  package also `soundfile`), neither is packaged for Alpine ("Can't load custom widget module
  'zynthian_widget_audio_file' => No module named 'moderngl'"): no waveform in the Tk UI on
  Nura. The desktop venv has them with `ZYNTHIAN_TK_WIDGETS=1`.
- **Qt:** yes (`WaveformView.qml`, QML Shape, libsndfile through ctypes when python-soundfile is
  missing). Gaps: the view keeps the previous processor's file name when the new one has no
  file (samplv1 without a sample, an empty Clippy show "Oya.mp3"); Qt's `chain_control` sends a
  Clippy chain to the launcher (since 4c408ea3), so its "Clip" page is reached from a pad.
- **samplv1:** main's bundle names the module as `file:///zynthian/zynthian-ui/zyngui/…`, which
  doesn't exist outside ZynthianOS: no engine widget for samplv1 in the port (the Qt UI shows the
  waveform anyway, from the engine type). Fixed on branch `lv2-user-widgets` (35c278d6, module
  path relative to the bundle; see docs/upstream-candidates.md there).

## Spectrum (spectr30)

- **File:** `lv2/meters-zyngui.lv2/zynthian_widget_spectr30.py` (jofemodo, 2c0a49d4, January
  2022: the first widget, with the base class).
- **Shows:** 30 third-octave bands (25 Hz–20 kHz) as bars with peak-hold ticks, scaled by the
  plugin's "UI gain". No touch.
- **Trigger:** `http://gareus.org/oss/lv2/meters#spectr30mono`, `#spectr30stereo`.
- **How to open:** in an audio chain (or after a synth) add Audio Effect > Analyzer > "1/3
  Octave Spectrum Display Stereo", any page; play something.
- **Tk:** yes. **Qt:** yes (`PluginWidgetView` "bars"). Parity: Tk green bars, red ticks; Qt
  blue bars, green ticks.

## Tuner (tunaone)

- **File:** `lv2/tuna-zyngui.lv2/zynthian_widget_tunaone.py` (jofemodo, 2c0a49d4, 2022).
- **Shows:** the detected note (C3, A4, …) and a cents bar on a −50…+50 scale, coloured green
  (in tune) to red; "??" / hidden without signal (RMS below −50 dB). No touch.
- **Trigger:** `http://gareus.org/oss/lv2/tuna#one`, `#mod`.
- **How to open:** Audio Effect > Analyzer > "x42 Instrument Tuner".
- **Tk:** yes. **Qt:** yes ("tuner"). Nura: x42-plugins provides `tuna#one` (and `#two`, which
  has no widget), not `#mod`.

## Graphic EQ (gxgraphiceq)

- **File:** `lv2/gxgraphiceq-zyngui.lv2/zynthian_widget_gxgraphiceq.py` (jofemodo, 8c68f402,
  March 2026; renamed from `zynthian_widget_GxGraphicEQ.py` in a1527c99, which broke the Qt view
  until `PLUGIN_WIDGETS` followed).
- **Shows:** the bands (11 for GxGraphicEQ, 24 Bark bands for GxBarkGraphicEQ) as level bars
  from the plugin's outputs, with a tick at each band's gain (−30…+22 dB) and the 0 dB line.
- **Touch:** press/drag in a band's column sets its gain to the touched height.
- **Trigger:** `…/gx_graphiceq_#_graphiceq_`, `…/gx_barkgraphiceq_#_barkgraphiceq_`.
- **How to open:** Audio Effect > Filter & EQ > "GxGraphicEQ" (GxBarkGraphicEQ is disabled by
  default in the engine list).
- **Tk:** yes. **Qt:** yes (bars, editable). The level bars stayed empty in both VMs with a
  synth playing through it (only the gain ticks show).

## NAM

- **File:** `lv2/nam-zyngui.lv2/zynthian_widget_nam.py` (jofemodo, 04922e86, January 2025).
- **Shows:** "Model:" and the loaded model's file name. No touch.
- **Trigger:** `http://github.com/mikeoliphant/neural-amp-modeler-lv2`.
- **How to open:** Audio Effect > Simulator > "Neural Amp Modeler"; choose a model on the
  "Neural Model" controller.
- **Tk:** yes. **Qt:** yes ("text": a smaller label, no underline).

## AIDA-X

- **File:** `lv2/aidax-zyngui.lv2/zynthian_widget_aidax.py` (riban, e01d4b9d, June 2024; model
  and cabinet info 04922e86).
- **Shows:** input and output level meters (falling 10 % per refresh) and the model and cabinet
  file names. No touch.
- **Trigger:** `http://aidadsp.cc/plugins/aidadsp-bundle/rt-neural-loader`.
- **How to open:** Audio Effect > Simulator > "AIDA-X".
- **Tk:** yes. **Qt:** yes ("aidax"). Parity: Tk's meters have green/yellow/grey zones, Qt plain
  bars.

## Chord analyzer

- **File:** `lv2/chord-analyzer-zyngui.lv2/zynthian_widget_chord_analyzer.py` (jofemodo,
  62e86a6b, September 2026).
- **Shows:** the detected chord ("C 6 (Root)") and bass note, from the plugin's outputs (it
  supports the monitor names of all three variants). No touch.
- **Trigger:** `https://dusk-audio.github.io/plugins/chord-analyzer`, `…-midi`, `…-headless`
  (not the "-2" variants).
- **How to open:** in a MIDI/synth chain add MIDI Tool > "Chord Analyzer Headless" (enabled by
  default; the other two are disabled in the engine list), play a chord.
- **Tk:** yes. **Qt:** yes ("text"). Parity: Tk yellow chord text, Qt white.

## Tempo

- **File:** `zyngui/zynthian_widget_tempo.py` (riban, 6c8cd235, January 2026).
- **Shows:** the tempo in large type ("80.0 BPM"); the page controllers are BPM, metronome mode
  and volume, beats per bar. **Touch:** a tap on it taps the tempo.
- **Trigger:** the tempo engine (TP), i.e. the state manager's tempo processor; the screen
  `tempo` is the control screen showing it.
- **How to open:** main menu > Tempo, or CUIA `TEMPO` (both also tap the tempo once).
- **Tk:** yes. **Qt:** yes ("tempo", with a "tap for tap tempo" hint): the tempo screen is a
  decided deviation (stays as Qt in the `tk` theme).

## Internet radio

- **File:** `zyngui/zynthian_widget_inet_radio.py` (riban, 5e31cd02, February 2024).
- **Shows:** the station or stream title, info (file / show), bitrate, codec, channels, and the
  artwork if the stream has one. No touch.
- **Trigger:** engine InternetRadio (IR), which runs VLC.
- **How to open:** Add chain > Audio Generator > Internet Radio, pick a station (bank = genre).
- **Tk:** yes. **Qt:** yes ("radio").
- **Nura:** the engine needs `vlc`, which isn't a zynthian-ui dependency: without it the engine is
  marked unavailable ("Engine 'IR' is not available!"). `apk add vlc` (Alpine community, 87
  packages in the VM) and a restart of the UI make it work (checked, streaming in both VMs).

## Euclidean sequencer

- **File:** `zyngui/zynthian_widget_euclidseq.py` (ronsum, 944d9ea8, June 2025); state, OSC and
  patterns in `zyngui/zynthian_euclidseq_data.py` (shared with Qt).
- **Shows:** six channels as circles with their Euclidean pattern (steps, hits, the polygon of
  hits, the current step) and the channel's note; a control panel for the selected channel
  (mode, length, hits, offset, mute).
- **Touch:** tap a circle selects its channel, drag it up/down changes its note; the panel's −/+
  buttons (or a drag on the value) change mode/length/hits/offset; Mute.
- **Trigger:** a Pure Data preset whose `zynconfig.yml` has `use_euclidseq_widget: true`
  (zynthian-data: midi-generative/EuclidSeq6).
- **How to open:** Add chain > Special > PureData, bank "midi-generative", preset "EuclidSeq6",
  page "General".
- **Tk:** yes. **Qt:** yes (`EuclidSeqView.qml`). Gap: at 480x320 (theme v4) the panel takes the
  whole middle column and the circles get no room (Tk shows the circles and cuts the panel).

## Organelle

- **File:** `zyngui/zynthian_widget_organelle.py` (ronsum, 44def09e, March 2025;
  `MULTI_INSTANCE`), shared parts in `zyngui/zynthian_organelle_data.py`.
- **Shows:** the Organelle's 128x64 OLED (five text lines and graphics sent by the patch over
  OSC), its LED, an AUX button (and FS), a volume slider; the knobs are the patch's knob 1–4.
- **Touch/keys:** tap a text line to go to that menu entry (the patch's menu); AUX
  press/release. Tk also maps the hardware: a switch toggles a menu *select mode* in which knob 3
  scrolls the menu (`/enc_up`, `/enc_down`) and its switch selects (`/enc_sel`), another switch is
  AUX (auto-long disabled while held); arrow CUIAs too.
- **Trigger:** a Pure Data preset whose path contains "organelle" or whose config has
  `use_organelle_widget: true`. In Nura's zynthian-data: audio-fx Cannabits, CA_Filter,
  Freeze_by_Tempo, Guitar2ARP2, LFO_Delay, Side-Chain, Vocoder_RL; midi-generative
  Euclidean_Rhythms, MidiFileSynth, Quilt. The Organelle abstractions are in
  `zynthian-data/puredata/organelle` (pd started with `-path` for it outside /zynthian: our
  patch 3237ba5a, nura-builds `zynthian-ui-tomita` patch 0019).
- **How to open:** Add chain > Special > PureData, bank "audio-fx", preset "Cannabits", page
  "Knobs".
- **Tk:** yes. **Qt:** yes (`OrganelleView.qml`); instead of the knob/switch select mode it has
  on-screen ▲ / SEL / ▼ buttons: the hardware mapping (knob 3, switches, arrows) is not
  ported.

## SooperLooper

- **File:** `zyngui/zynthian_widget_sooperlooper.py` (riban, 4d316a44, July 2022); actions shared
  in `zyngui/zynthian_sooperlooper_data.py`.
- **Shows:** the transport buttons (record, overdub, multiply, replace, substitute, insert, undo,
  redo, trigger, oneshot, reverse, pause, mute), one row per loop with position/length and
  state, "add loop", sliders for input level, feedback, wet, dry.
- **Touch/keys:** buttons press the function on the selected loop; tap a loop row selects it,
  a 1.4 s press asks to remove it; tap the mute area mutes; drag (or wheel) the sliders. Transport
  CUIAs in ALT mode drive the looper (record/play/stop); ALT + arrows: previous/next loop,
  undo/redo; ALT + program change selects a loop.
- **Trigger:** engine SooperLooper (SL).
- **How to open:** Add chain > Audio Effect > SooperLooper (also an Audio Input chain), page
  "Loop record 1".
- **Tk:** yes. **Qt:** yes (`SooperLooperView.qml`: buttons, loops, sliders, add/remove, ALT
  transport). Gap: ALT + arrows and ALT + program change are not handled.
- **Nura:** sooperlooper is a zynthian-ui dependency (nura-builds `aports/engines/sooperlooper`).

## How to see the envelope

Three easy ways, all with packages that are on Nura and enabled by default:

1. **Parity Test snapshot / Fabla:** load `900-Test/001-Parity Test.zss` (or add Add chain >
   Instrument > Fabla), open the Fabla chain's chain control and select **"Pad 1 - ADSR"** (every
  "Pad N - ADSR" page): an ADSR envelope (flat until you raise attack/decay).
2. **MDA JX10:** Add chain > Instrument > MDA JX10, pages **"Amp Envelope"** and **"Filter
   Envelope"** (ADSR with its default values, so it looks like an envelope at once); page
   "Params 2" shows the filter.
3. **FluidSynth:** Add chain > Instrument > FluidSynth, pick a soundfont (FluidR3 GM), page
   **"envelope/filter"**: an attack/release envelope (two phases).

More: amsynth "Amp Env" / "Filter Env" (ADSR), MiMi-d "Loudness Env 1" (ADSR with the fade
phase "sustain time"), MDA DX10's envelope page (attack/decay/release).

On the encoder kits the page is reached by turning the select knob in the chain control's select
mode; by touch, tap the page in the list. The widget appears in control mode.

## Plugins and engines with envelope / filter / drawbar designations

From the lilv scan in the Qt VM (all of nura-builds' installed LV2 bundles), plus the engines:

| Plugin / engine | URI | Envelope (port group → page) | Filter | Enabled by default |
|---|---|---|---|---|
| Fabla | `http://www.openavproductions.com/fabla` | per pad: `GROUP_PADn_ADSR` (attack, decay, sustain, release) → "Pad n - ADSR" | – | yes |
| MDA JX10 (mod and drobilla URIs) | `http://moddevices.com/plugins/mda/JX10` | `amp_env` (ADSR) → "Amp Envelope"; `filt_env` (ADSR) → "Filter Envelope" | `vcf_freq`, `vcf_reso` (no group) → "Params 2" | yes (mod) |
| MDA DX10 | `http://moddevices.com/plugins/mda/DX10` | `env` (attack, decay, release) | – | yes |
| MDA Piano | `…/mda/Piano` | `env` (decay, release) | – | no |
| MDA RezFilter (audio effect) | `…/mda/RezFilter` | `env` (attack, release) | `filt` (freq, res) | yes |
| MDA MultiBand (audio effect) | `…/mda/MultiBand` | `env` (attack, release) | – | no |
| MDA SubSynth (audio effect) | `…/mda/SubSynth` | release only (no group) | – | no |
| amsynth | `http://code.google.com/p/amsynth/amsynth` | `group_amp_env`, `group_filter_env` (ADSR) → "Amp Env", "Filter Env" | `group_filter` → "Filter 1" | yes |
| MiMi-d | `https://butoba.net/homepage/mimid.html` | `g601_filter_env`, `g602_loudn_env` (ADSR + fade = sustain time) → "Filter Env 1/2", "Loudness Env 1/2" | `g501_filter` → "Filter" | yes |
| FluidSynth (engine) | – | "env. attack", "env. release" → "envelope/filter" | – (its filter controllers aren't designated) | yes |
| ZynAddSubFX (engine) | – | – | "filter cutoff", "filter resonance" → "main" | yes |
| (sfz engine) | – | attack/release prepared but commented out (`zynthian_engine_sfz.py:63`) | – | – |

No installed plugin has `param:drawbar`. Other `param:` designations seen on input control
ports (no widget): frequency 1, gain 2, pulseWidth 2, waveform 3, wetDryRatio 1.

### Nura: the lv2-custom TTLs are not applied

ZynthianOS copies zynthian-data's `lv2-custom/*.lv2/*.ttl` over the installed plugin bundles
(zynthian-sys `scripts/update_zynthian_data.sh:415-426`). These patched TTLs add the envelope
and filter designations (and port groups, ranges, …) to many more synths. Nura's zynthian-data
package installs them in `/usr/share/zynthian/zynthian-data/lv2-custom`, but nothing copies them,
so on Nura these plugins show **no** envelope/filter widget although they do on ZynthianOS:

Helm (amp/filter/mod envelopes, filter), Obxd and OB-Xf (envelopes, filter), Odin2 (amp envelope,
three filters), TAL-NoiseMaker (envelopes, filter), TAL-Dub-3 (filter), Ultramaster KR-106
(ADSR, filter), RipplerX (ADSR), Calf Monosynth (two ADSFR envelopes, filter), synthv1, padthv1
and samplv1 (DCF/LFO/DCA envelopes and filters), Dexed (filter), Nekobi (filter), raffo, vex,
JC303 and TAL-U-NO-LX (one designation each). Upstream's newer zynthian-data also patches Calf
Organ with `param:drawbar`. This is a nura-builds packaging item (logged for the nura-builds
session); `tools/lv2_widget_designations.py` lists what the installed TTLs declare.

## User and external widgets

- **Now (a1527c99, forum topic 13882, 2026-11-17):** a widget is a `zyngui:widget` UI in any
  bundle on LV2_PATH: in the plugin's own bundle or an extension bundle (manifest with the `ui:ui`
  triple and the module beside it). User/external widgets go to
  `$ZYNTHIAN_PLUGINS_DIR/lv2-widgets` (ZynthianOS `/zynthian/zynthian-plugins/lv2-widgets`); a
  user widget wins over a built-in one with the same API version. New, removed or changed
  bundles are found without restarting (`check_lv2_changes()`; touch
  `$ZYNTHIAN_CONFIG_DIR/lv2.stamp` after editing a file inside an existing bundle). jofemodo
  plans package categories for plugins and widgets in zynthian-packages.
- **Before (September 2026, forum topic 13650):** `zyngui/widgets_user/zynthian_widget_<plugin
  name lowercased, spaces as _>.py`; ZynthianOS migrates those files into bundles
  (`migrate_user_widgets.py`); the port has no such files and no migration.
- **On the desktop and Nura:** branch `lv2-user-widgets` (another agent) puts
  `~/.local/share/zynthian/plugins/lv2-widgets` (and the presets folder) on LV2_PATH in the
  launcher and fixes the samplv1 bundle path; see its docs/architecture.md section.
- **Qt:** user widgets are Python/Tk modules, which the Qt UI doesn't run: a plugin whose widget
  isn't one of the built-in names shows only its controllers. A user widget with a built-in
  module name (e.g. its own `zynthian_widget_tunaone.py`) gets the built-in QML view. Qt reads
  `custom_gui_fpath` when the processor is created (no `refresh_custom_gui()`).
- **Existing user widgets found (2026-11-19):** none published as packages yet.
  zynthian-packages has only Soundfonts, Samples and IRs (46 packages). On the forum:
  ascari.maximilian's looper LV2 plugin with its own touch widget (topic 13650, a SooperLooper
  replacement, not published); niels' drawbar widget, merged upstream (topic 13835). A GitHub
  code search found only copies of the built-in widgets (crestenstclair/crest-zynthian).

## Qt gaps (to do)

- [ ] Drawbar view: `drawbar` pages (LV2 `param:drawbar`) and setBfree's engine widget
      (`zynthian_widget_drawbar.py`, `zynthian_widget_setbfree.py`, upstream PR 612).
- [ ] User/external `zyngui:widget` widgets: at least say "this plugin has a widget the Qt UI
      can't show" (or a fallback to the controllers is fine), pick up widget changes at runtime.
- [ ] Widget colours in the `tk` theme as Tk's (`color_on` outline, darker fill; spectrum green
      bars and red peaks; chord text yellow; AIDA-X meter zones).
- [ ] Waveform view: clear the file name/data when the processor has no file (samplv1, Clippy).
- [ ] Euclidean sequencer at 480x320: room for the circles (or a toggle between circles and
      panel).
- [ ] Organelle: the hardware mapping (select mode on knob 3, its switch, AUX switch, arrows).
- [ ] SooperLooper: ALT + arrows (previous/next loop, undo/redo), ALT + program change.
- [ ] Clippy: Qt opens the launcher for a Clippy chain (upstream shows its control page).
- Nura packaging, not Qt: apply zynthian-data's lv2-custom TTLs; `vlc` for the internet radio;
  moderngl for the Tk waveform (Tk only).

<!-- Private note (not part of the document's content): screenshots of each widget, Qt (VM 2252,
theme v4) and Tk (VM 2253, zynthian-ui-tomita 0_git20261107) side by side, are in the private
zynthian-stuff repository: ui-parity/shots/widgets/<name>-qt.png, -tk.png, -side-by-side.png
(commit 260be2b). -->
