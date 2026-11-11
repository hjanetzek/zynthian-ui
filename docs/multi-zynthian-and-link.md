# Several zynthians and Ableton Link

Status: 2026-11-11, branch `main` (tomita base). Research and design only: nothing here is
implemented. Builds on [architecture.md](architecture.md) (processes, MIDI router, zyngine API,
snapshots, threads); file:line references are to `zynthian-ui` unless another repository is
named (`zyncoder`, `zynthian-sys`, `zynthian-webconf`, all under `~/bastel/github`). Statements
marked *(unverified)* come from documentation or reasoning, not from running code.

Part 1 is about one zynthian (the master, with the UI) driving others (slaves, engines only);
part 2 about Ableton Link. They meet at the clock: Link is also the simplest way to keep several
zynthians in time.

---

## Part 1: one master UI, slaves running only engines

### 1.1 What exists today

Nothing multi-device: no master/slave, remote or "cluster" code, no env vars for it, no mDNS
browsing (`git grep` on `main` and `origin/tomita`). What does exist and can be built on:

| Piece | Where | Relevance |
|---|---|---|
| Network MIDI services: QmidiNet (multicast UDP), jackrtpmidid (RTP-MIDI / AppleMIDI), jacknetumpd (MIDI 2.0 Network UMP), touchosc2midi | systemd units `zynthian-sys/etc/systemd/{qmidinet,jackrtpmidid,jacknetumpd,touchosc2midi}.service`; started/stopped by `zyngine/zynthian_state_manager.py:2639-2882` (`start_netump`, `start_rtpmidi`, `start_qmidinet`, `start_touchosc2midi`); env vars `ZYNTHIAN_MIDI_NETWORK_ENABLED`, `…_NETUMP_ENABLED`, `…_RTPMIDI_ENABLED`, `…_TOUCHOSC_ENABLED` (`zyngui/zynthian_gui_config.py:400-406`) | MIDI between zynthians works today: autoconnect treats their JACK ports as hardware MIDI devices (`zynautoconnect/zynthian_autoconnect.py:718-728`, aliases `NET:rtp_*`, `NET:ump_*`, `NET:qmidi_*` at :1574-1587), so a network port can feed a zmip, be a chain's MIDI output, the clock source or a clock output |
| CUIA OSC server, UDP 1370 | `zynconf/zynthian_config.py:156`; Tk `zyngui/zynthian_gui.py:325-418`; Qt `zynqt/ui.py:1289-1310`; [osc-interface.md](osc-interface.md) | Remote *UI actions* (screens, switches, ZS3 load, transport). Not an engine API: no replies in Qt, no state queries |
| Mixer OSC (`/MIXER/…`, `/DAWOSC/…`) | Tk only, broken ([osc-interface.md](osc-interface.md), "/MIXER/…") | Was meant for remote mixers with meter feedback; would need rewriting |
| mDNS announcements | `zynthian-sys/etc/avahi/services/zynthian-osc.service` (`_osc._udp` 1370), `zynthian-rtpmidi.service` (`_apple-midi._udp` 5004), `zynthian-webconf.service` (`_http._tcp` 80), `zynthian-modui.service`, `zynthian-ssh.service` | Discovery of slaves is half there (static files, announced even when the service is off) |
| Webconf | `zynthian-webconf/lib/zynthian_config_handler.py:28-205` | Talks to the running UI only by OSC CUIAs to localhost:1370 (`NOP`, `POWER_OFF`, `REBOOT`, `RELOAD_*`); snapshots are handled as files (`lib/snapshot_config_handler.py:152-257`), never loaded into the running state |
| `zynthian_headless.py` | 47 lines | State manager without UI, then `while True: sleep(1)`. **Not runnable**: `import autoconnect` (:5) and `autoconnect.autoconnect()` (:40), a module that doesn't exist (`zynautoconnect.autoconnect()` at `zynautoconnect/zynthian_autoconnect.py:1716`); `init_midi()`/autoconnect are also already done by `zynthian_state_manager.start()` (:202-246). No CUIA consumer, no OSC server. Same on `origin/tomita` except a path |
| Network audio | none | jacktrip only appears in the installed program lists; no netjack, zita-njbridge or PipeWire network module is configured |

So: MIDI between zynthians is solved; audio, control and state are not.

### 1.2 What the master needs from a slave

From [architecture.md](architecture.md) §3, everything a UI does goes through a handful of
objects: the state manager (snapshots, ZS3, MIDI learn, busy state), the chain manager (chains,
processors, engines, active chain), the processors (banks, presets, controller screens) and
`zynthian_controller` (values, MIDI learn), plus zynmixer (strips, meters), zynseq (transport,
tempo, launcher) and zynsigman signals and `is_dirty` flags for the way back. A master showing a
slave's chains needs all of these remotely:

1. **Model**: the slave's chains, processors, controllers (with their options: ranges, labels,
   ticks, groups/screens), banks and presets.
2. **Commands**: add/remove chain or processor, set bank/preset, set controller value, MIDI learn,
   mixer values, transport.
3. **Change notifications**: controller values changed by MIDI or the engine, preset changes,
   chain changes, busy state, MIDI activity.
4. **Meters**: per strip, 20–30 Hz.
5. **Audio**: the slave's output (at least its main mix, ideally per chain) to the master's mixer.
6. **MIDI**: the master's controllers to the slave's chains (and back for feedback).
7. **Clock**: tempo, beat phase, start/stop.
8. **State**: snapshots and ZS3 that include the slave.

### 1.3 Options for audio and MIDI transport

| Option | What it is | Pros | Cons | Effort |
|---|---|---|---|---|
| **NetJACK2** (jackd `-d net` on the slave, `jack_load netmanager` on the master) | One JACK graph period-synchronous across machines; the slave runs from the master's clock, audio and MIDI ports appear on the master as a client | Sample-synchronous, no drift, MIDI and audio in one link, discovery by multicast, works with jackd (zynthian-sys) | The slave has **no local audio**: its sound card is not the driver (it can be added with `alsa_out`/`zita-a2j`, resampled). Wired Ethernet only; a lost link stops the slave's graph. Latency ≥ 1–2 periods | Small to set up (jackd options, a service); medium to integrate (port naming in autoconnect, failure handling) |
| **PipeWire netjack2 modules** (`libpipewire-module-netjack2-driver` / `-manager`) | The same protocol in PipeWire, compatible with jackd's NetJACK2 | Fits Nura (pipewire-jack): no jackd needed; the driver side is scheduled with the manager's period plus `netjack2.latency` periods (default 2); optional Opus/int encoding *(from the PipeWire man pages, unverified on a device)* | Same as NetJACK2; module availability depends on the PipeWire build (Alpine's `pipewire` package: to check) | Small (a PipeWire config fragment) |
| **zita-njbridge** (`zita-j2n` / `zita-n2j`) | Point-to-point audio over UDP with resampling | Each side keeps its own sound card and clock, robust, low CPU | Audio only (no MIDI); latency set by its buffer (a few ms to tens of ms); no discovery | Small (packaging, a service per stream) |
| **JackTrip** | Audio over UDP, built for the internet | Robust, Wi-Fi and WAN capable, hub mode for many peers | Audio only; more latency than netjack on a LAN; heavier | Small |
| **AES67 / RTP audio** (PipeWire `module-rtp-sink`/`-source`, PTP) | Standard networked audio | Interoperates with other gear; PTP clocking | Needs PTP (linuxptp) for sync; set-up complexity; audio only | Medium |
| **Network MIDI only** (RTP-MIDI, Network UMP, QmidiNet) | Already in zynthian | Exists; RTP-MIDI interoperates with macOS/iOS; UMP is MIDI 2.0 | MIDI only; jitter on Wi-Fi; no audio back | None (done) |

Notes:
- For a master that *mixes* slaves, the slave's audio must reach the master's zynmixer. NetJACK2
  makes the slave's ports local JACK ports on the master; the others create local ports too
  (`zita-n2j`, `jacktrip`), so all of them fit autoconnect's "audio input" model (chain
  `audio_in`, [architecture.md](architecture.md) §2.4).
- A slave that plays into its *own* outputs (a rack of synths each with an interface, the
  master only controls) needs no audio transport at all, only control, MIDI and clock.

### 1.4 Options for remote control of the engines

| Option | Pros | Cons | Effort |
|---|---|---|---|
| **A. OSC CUIAs** (exists) | No new code on the slave; already announced over mDNS | UI actions, not an API: CUIAs act on the slave's *current screen and active chain*; no model, no replies (Qt), no notifications. Driving a slave means driving its invisible UI | None, but useless for a real master |
| **B. MIDI only** (CC/PC to the slave's chains over RTP-MIDI/UMP) | Exists; MIDI learn on the slave maps CCs to anything | No model on the master (it can't show the slave's presets or controller names); 7-bit values; no feedback unless the slave sends CC back (controller feedback zmop is unconnected: `zynautoconnect/zynthian_autoconnect.py:1054-1058`) | None to small |
| **C. Remote zyngine API** (an RPC server in a headless zynthian, a proxy on the master) | Full model and commands: the master's UI code calls the same API (chain manager, processors, zctrls) through proxies; notifications from zynsigman and `is_dirty` | New code on both sides; the API is large and not designed for remoting (objects passed by reference, e.g. `zctrl` objects in `add_midi_learn`, `zyngine/zynthian_chain_manager.py:1670`; engines reach into `zyngui`, e.g. `zyngine/ctrldev/zynthian_ctrldev_base_ui.py:45-81`) | Large |
| **D. Narrow "engine host" protocol** (designed for this: chains, processors, controllers, presets, mixer, meters, transport, as JSON/OSC messages with IDs) | Small, versionable, testable; the master keeps one local model per slave; matches what the Qt UI's models already consume (`zynqt/models/*.py`) | A second model of the same data; must follow zyngine changes | Medium to large |
| **E. Webconf API** | Already a web server with websockets (`zynthian-webconf/lib/zynthian_websocket_handler.py:35-104`) | Runs in another process than the state manager: it would itself need (C) or (D) to reach zyngine; adds latency | Large, no benefit over C/D |

The **headless zynthian** is needed in any option beyond A/B: a process with the state manager,
chain manager, autoconnect and zynseq but no UI. `zynthian_headless.py` is the stub for it; it
needs fixing (above), a CUIA consumer (or none: a slave has no screens), and a server for (C)/(D).
Code in zyngine that calls the UI (`zynthian_gui_config.zyngui…`, e.g.
`zyngine/zynthian_tts.py:241`, many ctrldev drivers) must tolerate `zyngui` being `None` — the
Qt port has the same need (see [qt-port-plan.md](qt-port-plan.md), "The engine side imports
`zyngui`").

### 1.5 State sync: snapshots, ZS3, controller values, MIDI learn

What a snapshot holds ([architecture.md](architecture.md) §3.5): chains with slots and processor
IDs, engine extended config, ZS3s (each: per chain routing/MIDI learn/note range, per processor
bank/preset/controller values, MIDI capture state, globals such as clock source), zynseq state.
For several zynthians:

- **Per-device snapshots, master orchestrates** (recommended): each slave keeps its own snapshot
  and ZS3 store; the master's snapshot records, per slave, the slave's identity and the snapshot
  file name (or embeds the slave's state JSON, `get_state()` at
  `zyngine/zynthian_state_manager.py:987-1016`, so one file restores everything). A master ZS3
  load sends "load ZS3 *id*" to each slave; ZS3 ids are strings ("ch/pc" or "zs3-N",
  `load_zs3` at :1434), so the master can use one id space and slaves store under the same ids.
  ZS3 loading is fast (no engine restarts) and works by program change too: a PC on the master's
  ZS3 channel forwarded over network MIDI already loads ZS3s on slaves that have
  `midi_prog_change_zs3` set (`zynmidi_read`, :885-905). That is a zero-code ZS3 sync today.
- **One global state split across devices** (the master owns every chain, slaves are dumb
  hosts): cleaner model, but processor IDs, chain IDs and MIDI channels must be unique across
  devices, and snapshot merging code (:1180-1237) shows how much remapping that needs. More
  effort, more failure modes (a slave missing at load).
- **Controller values**: in (C)/(D), the slave notifies the master on change (zctrls set
  `is_dirty`, `zyngine/zynthian_controller.py:97`, 490-501; there is no per-change signal, the
  UIs poll the dirty flag of the controllers they show, `zynqt/screens/control.py:123`). For
  remoting, a slave-side poll of all zctrls (or a hook in `set_value`) that batches changes at
  ~20 Hz is needed. *(Design proposal.)*
- **MIDI learn**: stays on the device that owns the controller: MIDI from the master's
  controllers arrives on the slave as a network MIDI device (a zmip), and the slave's learn
  tables (absolute by zmip, chain-bound by active chain, `zyngine/zynthian_chain_manager.py:
  1670-1724`) work unchanged. Caveat: chain-bound learning follows the *slave's* active chain,
  so the master has to set the slave's active chain when the user selects a remote chain.

### 1.6 Clock sync

| Method | Today | Notes |
|---|---|---|
| MIDI clock over network MIDI | Works: the master's `zynseq:clock` to a `NET:*` output (`zynautoconnect/zynthian_autoconnect.py:999-1003`), the slave's clock source a `NET:*` input (:1008-1011); the slave locks with zynseq's PLL (`zynlibs/zynseq/zynseq.cpp:184-317`) | Jitter on Wi-Fi; 24 PPQN; the slave's tempo follows with the PLL's settling time; start/stop: zynseq ignores START/STOP on its normal input (:494-507) and only realigns on START on `clock_in` (:458-466) |
| NetJACK2 | Implied: slaves run on the master's period clock; JACK transport (zynseq is the timebase master, :964) is shared *(unverified for netjack's transport sync)* | Sample-accurate, wired only |
| **Ableton Link** | Not implemented (part 2) | Wi-Fi tolerant, peer-to-peer, tempo + phase + start/stop; also syncs with phones, Live, Bitwig, … |

### 1.7 How the master shows everything

- **Aggregated chain model**: the master's chain list = local chains + per slave a group of
  remote chains (a "device" column or a colour per device). The Qt models (`zynqt/models/
  mixer.py` `MixerModel`, the chain manager screens) take rows from a provider: a
  `RemoteChainProvider` per slave fills the same roles from the slave's model.
- **Mixer with remote strips**: two variants. (a) The slave mixes locally, the master shows the
  slave's strips as remote strips (values and meters over the network, audio stays on the
  slave or comes as one stereo return). (b) The slave's per-chain audio is sent to the master
  (netjack ports) and mixed in the master's zynmixer as ordinary audio-input chains: meters are
  local, but every chain costs network channels and latency.
- **Metering over the network**: zynmixer's DPM values (`zynlibs/zynmixer`, read per frame by
  `zynqt/models/mixer.py:235-260`) sent as one UDP packet per slave per frame (≤ 30 Hz,
  ~4 floats per strip): small. Drop late packets, never queue.
- **Latency**: LAN control round trip ≈ 1 ms (wired) to 5–30 ms (Wi-Fi) *(typical figures,
  unverified)*: fine for parameter changes, not for audio over Wi-Fi.
- **Failure handling**: slaves come and go: mark remote chains "offline" (greyed, values kept),
  reconnect by mDNS identity, re-sync the model on reconnect (full state, then deltas). A
  snapshot load on the master with a slave missing loads the rest and reports the slave. With
  NetJACK2 a lost slave silences only its ports; a lost *master* stops a netjack slave's graph,
  so slaves that must keep playing should not depend on netjack.

### 1.8 Recommendation

**Slaves are headless zynthians with their own audio outputs; the master controls them over a
narrow engine-host protocol (option D) on OSC/UDP, MIDI over Network UMP or RTP-MIDI (exists),
clock by Ableton Link, and audio back to the master only when wanted (NetJACK2 or zita-njbridge,
wired).**

Why: it reuses everything that works per device (engines, router, MIDI learn, snapshots, ZS3)
and adds one well-defined boundary instead of remoting the whole Python API; slaves keep
playing when the master or the network goes away; Link removes the clock problem and also
brings phones and DAWs in; audio transport is optional and chosen by the set-up (wired rack vs
stage over Wi-Fi). Option C (remoting zyngine itself) looks cheaper but the API passes Python
objects and reaches into the UI; D can be implemented *on top of* zyngine in the slave as a thin
server and is what the Qt models need on the master side anyway.

### 1.9 Staged plan

| Stage | What | Effort *(estimate)* |
|---|---|---|
| 0 | Document a zero-code set-up: network MIDI between zynthians, MIDI clock or (after part 2) Link, ZS3 sync by forwarded program change, slaves configured in their own UI/webconf | 1–2 days |
| 1 | Headless slave: fix `zynthian_headless.py`, a systemd unit / launcher mode `ZYNTHIAN_UI=headless`, `zyngui` = `None` safety in zyngine, mDNS service `_zynthian._udp` with device name and protocol version | 1 week |
| 2 | Link in zynseq (part 2): tempo, phase and start/stop across devices | 2–3 weeks |
| 3 | Engine-host protocol v1 (read-only + values): list chains/processors/controllers/presets, set value, set preset, change notifications (batched), meters; a test client | 3–4 weeks |
| 4 | Master side in the Qt UI: device discovery, remote chains in chain list and mixer (variant a), control screen on remote processors, offline handling | 3–5 weeks |
| 5 | Commands: add/remove chains and processors remotely, MIDI learn on remote controllers, snapshot/ZS3 orchestration (per-device snapshots referenced by the master's) | 3–4 weeks |
| 6 | Optional audio return: NetJACK2/PipeWire netjack2 or zita-njbridge as a configurable "remote input" chain on the master; per-chain returns | 2–3 weeks |

### 1.10 Open questions

- Is the target a wired rack (NetJACK2 makes sense, one clock) or a stage over Wi-Fi (Link +
  control only)? It changes stage 6 completely.
- Should slaves keep a minimal local UI (e.g. a kit's display showing "slave of …") or run with
  no display at all?
- Is the PipeWire build on Nura built with the netjack2 and RTP modules?
- One state or per-device states (1.5)? The recommendation assumes per-device.
- Should the protocol be OSC (fits zynthian, liblo exists on both sides) or JSON over WebSocket
  (easier for browsers, e.g. a webconf-based remote)? Both can share one message schema.

---

## Part 2: Ableton Link, full support

### 2.1 What exists now

**No Link in zynthian's own code.** Searching zynseq, zyngine (tempo engine, state manager),
zyngui, zynqt, zyncoder, webconf and `origin/tomita` finds no `link`/`abl_link`/`hylia`/
`carabiner`/`jack_link` symbols; the "Ableton" hits are a pip package (`requirements.txt:13`,
`abletonparsing`), the Launchpad's "Ableton mode" (`zyngine/ctrldev/
zynthian_ctrldev_launchpad_pro_mk2.py:67-91`) and a comment (`zyngine/zynthian_controller.py:750`).

On the system side, zynthian-sys installs two Link-related libraries that nothing in the UI uses:
- **Hylia** (falkTX's host transport library for Link): `zynthian-sys/scripts/recipes/
  install_hylia.sh:3,15-20`, run by `setup_system_raspioslite_64bit_trixie.sh:569-571`,
  `…_bookworm.sh:561-563`, `setup_system_lxc_64bit_trixie.sh:596`.
- **Pure Data `abl_link~`**: `zynthian-sys/scripts/recipes/install_pd_extra_abl_link.sh:3,13-18`.
  So **Pd patches** can join a Link session today; nothing else can.

There is no `jack_link` service. `jack-midi-clock.service` (`zynthian-sys/etc/systemd/
jack-midi-clock.service:9`) exists but is unrelated to the UI.

### 2.2 How tempo, clock and transport work today

- **zynseq is the clock**: one JACK client, internal resolution `PPQN_INTERNAL` = 1920 ticks per
  beat (`zynlibs/zynseq/constants.h:55`). Each period `onJackProcess` (`zynlibs/zynseq/
  zynseq.cpp:372`) computes the frame offsets of the ticks in that period into `g_vTicks`
  (:432-483) from `dNextIntClockFrame` and `g_dFramesPerTick` (`updateClockTiming`, :169-171),
  then clocks the sequences tick by tick (`g_seqMan.clock(nTickTime, …, bSync, bBeat)`, :719),
  where `bSync` is the bar start and `bBeat` the beat start (:665-713).
- **Tempo**: `setTempo()` (:3239-3249; 10 ≤ bpm < 500; ignored while locked to external clock),
  Python `zynseq.set_tempo`/`nudge_tempo`/`tap_tempo` (`zynlibs/zynseq/zynseq.py:655-665`) via
  the tempo zctrl (:312, callback :672-673); `update_state` copies the C tempo back into the
  zctrl (:712-714) so the UI follows an external clock. Per-sequence tempo maps apply during
  playback (:719-721 of zynseq.cpp).
- **Clock source**: internal, or one MIDI input device: autoconnect connects
  `devices_in[ext_clock_zmip]` → `zynseq:clock_in` (`zynautoconnect/zynthian_autoconnect.py:
  1008-1011`; setters :593-612), saved per ZS3 as `global.clock_source` (`zyngine/
  zynthian_state_manager.py:1780`, restored :1585-1591). UI: Tk `zyngui/
  zynthian_gui_midi_config.py:198,300-302`, Qt `zynqt/screens/routing.py:174-176`. The
  external clock is followed by a 2nd-order DLL/PLL (`onExtClock`, zynseq.cpp:184-317), which
  steers `g_dFramesPerTick` so the internal ticks hit the predicted next pulse: a **frequency and
  phase lock without skipping ticks** — exactly the mechanism a Link follower needs.
- **Clock out**: MIDI clock every `PPQN_INTERNAL/PPQN_MIDI` ticks (:751-756) and START/STOP
  (:679-691) on `zynseq:clock`, routed to the selected outputs (autoconnect :999-1003). The MIDI
  router drops 0xF8 (`zyncoder/zynmidirouter.c:1414`), so clock only travels on these direct
  JACK connections.
- **JACK transport**: zynseq is the **timebase master** (`jack_set_timebase_callback`,
  zynseq.cpp:964; `onJackTimebase` :329-339 fills BBT and BPM; `updateJackPosition` :341-353
  repositions on tempo changes) and starts/stops the transport with its own state machine
  (:678, :686-687). It never follows another timebase master. Plugins hosted by jalv get tempo
  and position from JACK transport *(jalv's JACK backend forwards `time:Position`; not checked
  in this tree)*.
- **Transport state machine**: `transportStart/Stop/Toggle(uint8_t id)` with a client bitmask
  (zynseq.cpp:3214-3235). **Bug**: the Python wrapper passes `bytes(client, "utf-8")` with no
  argtypes (`zynlibs/zynseq/zynseq.py:637-653`), so C receives the low byte of a pointer as the
  id: `1 << id` for an arbitrary byte, and `transport_stop("ALL")`
  (`zyngine/zynthian_state_manager.py:279`) never reaches the "all" id 255. Logged in
  ui-parity/issues.txt.
- **Quantised launch**: sequences start on the bar (`bSync`) in `SequenceManager::clock`; the
  launcher's quantisation is relative to zynseq's own bar counter (`g_nBeat`, `g_nBar`).

### 2.3 What "full support" means

| Feature | Link API | zynthian side |
|---|---|---|
| Tempo sync | `SessionState::tempo()`, `setTempo()` | zynseq follows the session tempo; local tempo changes (UI, tap, MIDI-learned tempo zctrl, sequence tempo maps) are proposed to the session |
| Beat/phase alignment | `beatAtTime(t, quantum)`, `phaseAtTime`, quantum = beats per bar | zynseq's beat and bar boundaries (`g_nBeat`, `bSync`) land on the session's beat/phase grid with quantum = `g_nBeatsPerBar`; time signature changes change the quantum |
| Start/stop sync | `enableStartStopSync(true)`, `isPlaying()`, `setIsPlaying(…, time)` | zynseq's transport (STARTING/STOPPING) follows the session's play state and proposes its own starts/stops |
| Quantised launch | `requestBeatAtStartPlayingTime(0, quantum)` | starting the transport (launcher pad, TOGGLE_PLAY) begins at the next bar of the session; with Link the bar *is* the session phase |
| Peers display | `numPeers()`, peer callbacks | status bar: Link icon with peer count; tempo screen shows "Link" as source |
| Master or follower | Link has no master: all peers are equal; the last tempo change wins | "Link on/off" instead of a clock source choice; when on, an incoming MIDI clock is ignored, or the user picks one of {internal, MIDI device, Link} |
| MIDI clock / JACK transport | — | zynseq keeps emitting MIDI clock (outputs) and stays JACK timebase master, so external MIDI gear and LV2 plugins follow Link indirectly |
| Link Audio (Link 4+/5 beta) | `LinkAudio.hpp`, audio channels aligned to the timeline | out of scope for now; interesting for part 1 (audio between zynthians on the Link timeline) *(the SDK feature exists; suitability not evaluated)* |

### 2.4 How to integrate

**Option 1: Link SDK inside zynseq (recommended).** Link is a header-only C++ library
(`ableton::Link`, `include/ableton/Link.hpp`, asio included); zynseq is C++ already. Design:

- Create `ableton::Link link(g_dTempo)` at `init()` (zynseq.cpp ~:918-968), `enable()` by a new
  API `enableLink(bool)`, `enableStartStopSync(true)`. Link runs its own network thread; the
  JACK thread only uses `captureAudioSessionState()` / `commitAudioSessionState()`, which are
  realtime-safe (Link's documented audio-thread API, *per the SDK README; unverified here*).
- **Time base**: Link works in host time (`std::chrono::microseconds` of its platform clock);
  JACK in frames. Map the period start with `ableton::link::HostTimeFilter` (sample time →
  host time, as the SDK's JACK example `examples/linkaudio/AudioPlatform_Jack.ipp` does) plus the
  output latency (`jack_port_get_latency_range` of the playback ports).
- **Follower**: each period, read `beatAtTime(hostTime(periodEnd), quantum)` and steer
  `g_dFramesPerTick` so zynseq's tick position reaches that beat at the period end — the same
  structure as the external-clock PLL (`onExtClock`, :184-317, and the retiming at :447-449):
  treat Link like a perfect clock source whose "pulses" are computed, no filtering needed. On
  the first lock or a large phase error (> half a beat), jump (`nNextBeatTime`, `g_nBeat`) as
  the MIDI START handling does (:450-455).
- **Proposer**: `setTempo()` (:3239) also commits the new tempo to the session; tap tempo and
  tempo maps go through it. Transport start: if start/stop sync is on, `setIsPlayingAndRequestBeatAtTime(true, now, 0, quantum)`,
  and zynseq enters STARTING when the session's play state flips; stop: `setIsPlaying(false)`
  and STOPPING (zynseq stops on beat 1, :684-692: keep that).
- **Priority**: if `clock_in` is connected (external MIDI clock) Link is disabled or the user is
  warned; the UI offers one clock source: Internal / MIDI device / Link.
- **State**: `link_enabled` and `link_start_stop_sync` in zynseq's state (`getState`, :1635)
  or as ZS3 globals next to `clock_source` (`zyngine/zynthian_state_manager.py:1780`).
- **Python API**: `zynseq.py`: `enable_link(bool)`, `is_link_enabled()`, `get_link_peers()`;
  the tempo zctrl keeps working (it reads `getTempo`, which then returns the session tempo).

**Option 2: a separate bridge process** (jack_link-style, or Hylia/Carabiner):
a JACK client that is Link peer and JACK timebase master (or MIDI clock generator). zynseq
would have to *follow* the JACK transport/BBT or the bridge's MIDI clock (via `clock_in`, the
PLL). Pros: no change to zynseq, Link code isolated. Cons: zynseq is the timebase master today
and doesn't follow JACK transport at all; following MIDI clock from the bridge loses the phase
precision (24 PPQN, PLL settling) and start/stop semantics; two clocks to configure. Only
attractive as a stop-gap: e.g. a bridge that emits MIDI clock + START into `zynseq:clock_in`
works with today's code. (Hylia is already installed by zynthian-sys and is the obvious base for
such a bridge.)

**Licence**: the Link SDK is dual-licensed, GPLv2-or-later and proprietary
(`github.com/Ableton/link`, README). "Or later" lets it be used under GPLv3, so combining it with
zynseq (GPLv3, `zynlibs/zynseq/LICENSE.txt`) and the rest of zynthian (GPLv3, `LICENSE.txt`) is
fine; the combined work is GPLv3. Ableton's Link guidelines ask for UI conventions (the word
"Link", tempo and peer display) *(check the current guidelines before a release)*. SDK versions:
4.1.1 is the latest stable tag, 5.0b1 a beta (tags on GitHub, 2026-11-11).

**Build**: vendor Link as a git submodule or a Nura package (`link-dev`, headers only) and add
the include path to `zynlibs/zynseq/CMakeLists.txt`; asio is bundled with Link. Mind the
nura-builds rules (build in CI, check makedepends).

### 2.5 UI side

- **Tempo screen** (Tk `zyngui/zynthian_widget_tempo.py:79-83`; Qt the tempo processor's
  control screen, `zynqt/ui.py:49-51,128,412-415`, tap at `zynqt/models/widgets.py:222-227`):
  a "Link" toggle and "Start/stop sync" toggle as zctrls of the tempo engine
  (`zyngine/zynthian_engine_tempo.py:113-130` builds the controller list; it already switches
  between `bpm` and `ppqn` by clock source), so both UIs get them without screen code; peer count
  as a read-only zctrl or a label.
- **Clock source** selection (Tk `zyngui/zynthian_gui_midi_config.py`, Qt
  `zynqt/screens/routing.py:174-176`): add "Ableton Link" next to Internal and the MIDI devices.
- **Status bar**: a Link icon (on / with peers) next to the MIDI clock indicator
  (`status_midi_clock`, `zyngine/zynthian_state_manager.py:142`; Tk `zyngui/zynthian_gui_base.py:
  345,486`; Qt `zynqt/ui.py:320`).
- **CUIAs**: `LINK_TOGGLE` (for key bindings, OSC, MIDI note mappings).
- **Webconf**: optional default (`ZYNTHIAN_LINK_ENABLED`) on the MIDI options page.

### 2.6 Plan

| Step | What | Effort *(estimate)* |
|---|---|---|
| 1 | Package the Link SDK headers for Nura (and a build recipe for zynthian-sys); add to zynseq's CMake behind an option | 1–2 days |
| 2 | zynseq: Link object, enable/disable API, tempo follow and propose, host-time mapping (HostTimeFilter), phase lock in the tick generator; unit test with two zynseq instances or LinkHut on the desktop | 1–1.5 weeks |
| 3 | Start/stop sync and quantised start (bar = quantum), STARTING/STOPPING driven by the session; time-signature changes update the quantum | 3–5 days |
| 4 | Python wrapper, tempo engine zctrls, state (ZS3 global or zynseq state), clock-source exclusivity with MIDI clock | 2–3 days |
| 5 | UI: Qt and Tk tempo screen toggles (via zctrls), status icon, clock source entry, CUIA | 2–3 days |
| 6 | Tests on devices: Duet + phone (Link apps) + Live/Bitwig; jitter and phase error measurement (record clicks of both, compare onsets); Wi-Fi vs wired | 3–5 days |

Total about 3–4 weeks. A stop-gap (bridge emitting MIDI clock into `zynseq:clock_in`) is
2–3 days but gives only tempo and approximate phase.

### 2.7 Open questions

- Should Link be one of the clock sources (exclusive) or a layer on top of "internal" (internal
  + Link on)? Live and most apps treat it as on/off on top of the internal clock; MIDI clock in
  then conflicts.
- Link's realtime API on PipeWire's JACK: `captureAudioSessionState` must be called from the
  process callback; pipewire-jack's data thread is fine for that *(to verify)*.
- Upstream interest: zynthian upstream discussed Link support in the forum in the past
  *(not checked)*; worth asking before writing it, as zynseq is shared code.
