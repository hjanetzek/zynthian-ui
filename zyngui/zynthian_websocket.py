# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# Websocket API of the UI: CUIAs, keys and MIDI in, feedback streams out
#
# Copyright (C) 2015-2026 Fernando Moyano <jofemodo@zynthian.org>
#
# ******************************************************************************
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ******************************************************************************

"""The UI's websocket server (port zynconf.ServerPort["websocket"], 8370), without the toolkit.

Clients send JSON messages: {"cuia": NAME, "args": [...]} (into the UI's CUIA queue, as OSC),
{"key": "down"|"up", "code": KeyboardEvent.code}, {"midi": "note_on"|"note_off"|"cc"|...} (on the
active chain's MIDI channel), and text commands: "/subscribe STREAM ..." and "/unsubscribe
STREAM|* ...". The feedback streams: "wsled_state", "screen_state", "dpm_global", "dpm_state" and
"chain_state" (see their sections below for the message formats).

zynthian_websocket_feedback is a mixin of the UI class (zyngui.zynthian_gui, zynqt.ui.ZynUI). It
needs from the UI: exit_flag, state_manager, chain_manager, cuia_queue, and these methods (the
toolkit's part, see "Toolkit interface" below):

  websocket_run_idle(fn, *args)       run fn in the UI (GUI) thread, as soon as it is idle
  websocket_run_later(ms, fn, *args)  run fn in the UI thread after ms milliseconds
  websocket_key_event(action, code)   a key from a client (default: ignored)
  websocket_cuia(cuia, args, src)     a CUIA from a client (default: into cuia_queue)
  websocket_wsleds()                  the LED object with last_wsled_state / wsled_state_changed,
                                      or None (default: self.wsleds)
  screen_state_current()              (screen name, view) of the screen shown
  get_screen_title(view)              its title (breadcrumb)
  screen_state_watch(on)              start / stop reporting title changes (cb_screen_state_title)

Views report their state as zyngui.zynthian_gui_base does: state_key, get_state(what),
get_state_parent(), is_state_shown(), and the SS_GUI_VIEW_STATE / _LIST / _SELECT zynsignals; a
change of screen is SS_GUI_SHOW_SCREEN. A UI can also call cb_screen_state_full() on any change:
the state is then compared with the one sent and only the differences go out.
"""

import json
import logging
import sys
import threading
from queue import SimpleQueue
from time import sleep

from zyncoder.zyncore import lib_zyncore
import zynconf
from zyngine.zynthian_signal_manager import zynsigman

try:
    from websocket_server import WebsocketServer
except ImportError:  # Not installed: the UI runs without websocket server
    WebsocketServer = None


if WebsocketServer is not None:

    class zynthian_websocket_server(WebsocketServer):
        """Websocket server that doesn't print a traceback for connections failing the handshake.

        Port probes (e.g. webconf checking if the UI websocket is up) and scanners connect and close without
        sending a request, and websocket_server fails with an AssertionError or a socket error.
        """

        def handle_error(self, request, client_address):
            err = sys.exc_info()[1]
            if isinstance(err, (AssertionError, OSError)):
                logging.debug(f"Websocket connection from {client_address} failed => {type(err).__name__}: {err}")
            else:
                logging.error(f"Websocket connection from {client_address} failed => {type(err).__name__}: {err}", exc_info=True)

else:
    zynthian_websocket_server = None


class zynthian_websocket_feedback:
    """Websocket server and feedback streams of the UI (mixin, see the module's docstring)"""

    def websocket_setup(self):
        """Initialize the websocket state (call it in the UI's __init__)"""
        self.websocket_port = zynconf.ServerPort['websocket']
        self.websocket_server = None
        self.websocket_engine_thread = None
        self.websocket_server_thread = None
        self.websocket_sender_thread = None
        self.websocket_clients = {}
        # Feedback streams clients can subscribe to: {name: function returning the current value (None if no value yet)}
        self.websocket_feedback_streams = {
            "wsled_state": lambda: self.websocket_wsleds().last_wsled_state if self.websocket_wsleds() else None,
            "screen_state": lambda: None,  # The full state is sent by the main thread after subscribing
            "dpm_global": lambda: None,  # Sent by the DPM sampling task after subscribing
            "dpm_state": lambda: None,
            "chain_state": lambda: self.get_chain_state()
        }
        # Feedback queued for the websocket sender thread: (stream, JSON message)
        self.websocket_queue = SimpleQueue()
        # Serialize the writes to the websocket connections, done from several threads
        self.websocket_send_lock = threading.Lock()
        # "screen_state" feedback: signals are registered only while someone is subscribed
        self.screen_state_active = False
        self.screen_state_full = 0  # Send the full state on next update: 1 => if it changed, 2 => always
        self.screen_state_parts = {}  # Views (or view parts) with changes to send => "list" or "select"
        self.screen_state_title = False  # Title changed
        self.screen_state_pending = False  # Update scheduled
        self.screen_state_sent = {}  # Last state sent, to send only what changes
        # DPM feedback ("dpm_global", "dpm_state"): sampled only while someone is subscribed
        self.dpm_feedback_active = False
        self.dpm_global_sent = None  # Last main bus levels sent
        self.dpm_state_sent = {}  # Last levels sent for each chain => {chain_id: [a, b, a_hold, b_hold]}
        # Chain feedback ("chain_state"): signals are registered only while someone is subscribed
        self.chain_state_active = False
        self.chain_state_pending = False  # Update queued for the sender thread
        self.chain_state_json = ""  # Last chain state sent
        # Feedback streams subscribed by each client: {client id: set of stream names}
        self.websocket_subscriptions = {}

    # --------------------------------------------------------------------------
    # Toolkit interface: implemented by the UI
    # --------------------------------------------------------------------------

    def websocket_run_idle(self, fn, *args):
        """Run fn(*args) in the UI thread, as soon as it is idle. Called from any thread."""
        raise NotImplementedError

    def websocket_run_later(self, ms, fn, *args):
        """Run fn(*args) in the UI thread after ms milliseconds. Called from the UI thread."""
        raise NotImplementedError

    def websocket_key_event(self, action, code):
        """A keyboard event from a client: action "down" / "up", code as HTML KeyboardEvent.code"""

    def websocket_cuia(self, cuia, args, src):
        """A CUIA from a client (websocket thread): into the UI's CUIA queue, as OSC"""
        self.cuia_queue.put_nowait((cuia, args, src))

    def websocket_wsleds(self):
        """The LEDs whose state the "wsled_state" stream sends (last_wsled_state, wsled_state_changed)"""
        return self.wsleds

    def screen_state_current(self):
        """(name, view) of the screen shown. Called from the UI thread.

        name: the "screen" sent (the Tk screen names); view: its view state (state_key, get_state(what)), or None
        """
        raise NotImplementedError

    @staticmethod
    def get_screen_title(screen_obj):
        """Title (breadcrumb) of the screen shown (view: from screen_state_current)"""
        return ""

    def screen_state_watch(self, on):
        """Start (on True) / stop reporting changes the views don't signal: titles => cb_screen_state_title()"""

    def websocket_stop(self):
        """End the sender thread and close the server"""
        self.websocket_queue.put(None)
        if self.websocket_server:
            try:
                self.websocket_server.shutdown_gracefully()
            except Exception as e:
                logging.debug(f"Can't stop the websocket server => {e}")

    # --------------------------------------------------------------------------
    # Clients and subscriptions
    # --------------------------------------------------------------------------

    def websocket_send(self, client, data):
        """Send a JSON message to a websocket client. Returns False if it can't be sent."""
        try:
            payload = json.dumps(data)
            with self.websocket_send_lock:
                self.websocket_server.send_message(client, payload)
            return True
        except Exception:
            return False  # Ignore broken or dropped socket links

    def websocket_command(self, client, message):
        """Handle a text command from a websocket client: /subscribe <stream> ... or /unsubscribe <stream|*> ..."""
        words = message.split()
        cmd, streams = words[0], words[1:]
        subs = self.websocket_subscriptions.setdefault(client['id'], set())
        if cmd not in ("/subscribe", "/unsubscribe") or not streams:
            self.websocket_send(client, {"error": f"Bad command '{message}'. Use '/subscribe <stream>' or '/unsubscribe <stream|*>'"})
            return
        if cmd == "/subscribe":
            unknown = [n for n in streams if n not in self.websocket_feedback_streams]
            new_dpm = []
            for name in streams:
                if name in self.websocket_feedback_streams and name not in subs:
                    subs.add(name)
                    if name == "screen_state":
                        self.websocket_run_idle(self.screen_state_sync, True)
                    elif name in ("dpm_global", "dpm_state"):
                        new_dpm.append(name)
                    elif name == "chain_state":
                        self.chain_state_sync()
                    # Send the current value, so the client doesn't have to wait for a change
                    value = self.websocket_feedback_streams[name]()
                    if value:
                        self.websocket_send(client, {name: value})
            if new_dpm:
                self.websocket_run_idle(self.dpm_feedback_sync, new_dpm)
        else:
            unknown = [n for n in streams if n != "*" and n not in self.websocket_feedback_streams]
            if "*" in streams:
                subs.clear()
            else:
                subs.difference_update(streams)
            self.websocket_run_idle(self.screen_state_sync)
            self.websocket_run_idle(self.dpm_feedback_sync)
            self.chain_state_sync()
        if unknown:
            self.websocket_send(client, {"error": f"Unknown feedback stream(s): {' '.join(unknown)}. Available: {' '.join(self.websocket_feedback_streams)}"})
        self.websocket_send(client, {"subscriptions": sorted(subs)})

    def websocket_has_subscribers(self, stream):
        return any(stream in subs for subs in list(self.websocket_subscriptions.values()))

    def websocket_broadcast(self, stream, value):
        """Send the value of a feedback stream to the clients subscribed to it"""
        if self.websocket_has_subscribers(stream):
            self.websocket_broadcast_payload(stream, json.dumps({stream: value}))

    def websocket_broadcast_payload(self, stream, payload):
        """Send a JSON message to the clients subscribed to a feedback stream"""
        for client_id, subs in list(self.websocket_subscriptions.items()):
            client = self.websocket_clients.get(client_id)
            if client and stream in subs:
                try:
                    with self.websocket_send_lock:
                        self.websocket_server.send_message(client, payload)
                except Exception:
                    pass  # Ignore broken or dropped socket links

    # --------------------------------------------------------------------------
    # "screen_state" websocket feedback
    #
    # The full state is sent after subscribing and when the screen or the layout of a view changes:
    #   {"screen": "control", "title": "...", "zyngui_chain_control": {"chain_blocks": {...}, "zyngui_selector": {...}}}
    # Otherwise, only the changed parts are sent, to be merged with the previous state:
    #   {"zyngui_chain_control": {"zyngui_selector": {"selected": 4}}}
    # The views send zynsigman signals when their state changes. Callbacks are registered only while someone is
    # subscribed, so there is no cost otherwise.
    # --------------------------------------------------------------------------

    def screen_state_sync(self, full=False):
        """Main thread: start/stop the screen state feedback, depending on the subscriptions"""
        active = self.websocket_has_subscribers("screen_state")
        if active and not self.screen_state_active:
            self.screen_state_active = True
            zynsigman.register(zynsigman.S_GUI, zynsigman.SS_GUI_SHOW_SCREEN, self.cb_screen_state_full)
            zynsigman.register(zynsigman.S_GUI, zynsigman.SS_GUI_VIEW_STATE, self.cb_screen_state_view)
            zynsigman.register(zynsigman.S_GUI, zynsigman.SS_GUI_VIEW_LIST, self.cb_screen_state_list)
            zynsigman.register(zynsigman.S_GUI, zynsigman.SS_GUI_VIEW_SELECT, self.cb_screen_state_select)
            self.screen_state_watch(True)
        elif not active and self.screen_state_active:
            self.screen_state_active = False
            zynsigman.unregister(zynsigman.S_GUI, zynsigman.SS_GUI_SHOW_SCREEN, self.cb_screen_state_full)
            zynsigman.unregister(zynsigman.S_GUI, zynsigman.SS_GUI_VIEW_STATE, self.cb_screen_state_view)
            zynsigman.unregister(zynsigman.S_GUI, zynsigman.SS_GUI_VIEW_LIST, self.cb_screen_state_list)
            zynsigman.unregister(zynsigman.S_GUI, zynsigman.SS_GUI_VIEW_SELECT, self.cb_screen_state_select)
            self.screen_state_watch(False)
            self.screen_state_parts = {}
            self.screen_state_sent = {}
        if active and full:
            # New subscriber => always send the full state
            self.screen_state_full = 2
            self.screen_state_schedule()

    def cb_screen_state_full(self, **kwargs):
        self.screen_state_full = max(self.screen_state_full, 1)
        self.screen_state_schedule()

    def cb_screen_state_view(self, view):
        if self.get_state_path(view) is not None:
            self.cb_screen_state_full()

    def cb_screen_state_list(self, view):
        self.screen_state_parts[view] = "list"
        self.screen_state_schedule()

    def cb_screen_state_select(self, view):
        if view not in self.screen_state_parts:
            self.screen_state_parts[view] = "select"
            self.screen_state_schedule()

    def cb_screen_state_title(self, *args):
        self.screen_state_title = True
        self.screen_state_schedule()

    def screen_state_schedule(self):
        # Defer the update, so a burst of changes is sent as one message
        if not self.screen_state_pending:
            self.screen_state_pending = True
            self.websocket_run_later(20, self.screen_state_update)

    def get_state_path(self, view):
        """Return the list of keys locating the state of a view (or view part), or None if it's not shown"""
        path = []
        root = None
        while view:
            if not view.state_key or not view.is_state_shown():
                return None
            path.insert(0, view.state_key)
            root = view
            view = view.get_state_parent()
        if root is not self.screen_state_current()[1]:
            return None
        return path

    @staticmethod
    def get_state_diff(old, new):
        """Return the values of new that differ from old (nested), or None if some key of old is missing in new"""
        if old.keys() - new.keys():
            return None
        diff = {}
        for key, value in new.items():
            old_value = old.get(key)
            if isinstance(value, dict) and isinstance(old_value, dict):
                d = zynthian_websocket_feedback.get_state_diff(old_value, value)
                if d is None:
                    return None
                if d:
                    diff[key] = d
            elif old_value != value:
                diff[key] = value
        return diff

    def screen_state_update(self):
        """Main thread: queue the screen state changes for the subscribers"""
        self.screen_state_pending = False
        parts, self.screen_state_parts = self.screen_state_parts, {}
        title, self.screen_state_title = self.screen_state_title, False
        full, self.screen_state_full = self.screen_state_full, 0
        if not self.screen_state_active:
            return
        try:
            screen, screen_obj = self.screen_state_current()
            # The screen may change before its signal arrives (views are filled while showing them)
            if screen != self.screen_state_sent.get("screen"):
                full = max(full, 1)
            if full:
                state = {"screen": screen}
                if screen_obj:
                    state["title"] = self.get_screen_title(screen_obj)
                    if screen_obj.state_key:
                        state[screen_obj.state_key] = screen_obj.get_state()
                sent, self.screen_state_sent = self.screen_state_sent, state
                if full == 1:
                    # Send only the differences, unless the screen changed or some key was removed
                    diff = self.get_state_diff(sent, state)
                    if diff is not None and "screen" not in diff:
                        state = diff
            else:
                # Send only the values that differ from the last sent ones
                state = {}
                if title and screen_obj:
                    title = self.get_screen_title(screen_obj)
                    if title != self.screen_state_sent.get("title"):
                        state["title"] = self.screen_state_sent["title"] = title
                for view, what in parts.items():
                    path = self.get_state_path(view)
                    if not path:
                        continue
                    node = None
                    sent = self.screen_state_sent
                    for key in path:
                        sent = sent.setdefault(key, {})
                    for key, value in view.get_state(what).items():
                        if sent.get(key) != value:
                            sent[key] = value
                            if node is None:
                                node = state
                                for k in path:
                                    node = node.setdefault(k, {})
                            node[key] = value
            if state:
                # Serialized here, as later updates modify the dictionaries
                self.websocket_queue.put(("screen_state", json.dumps({"screen_state": state})))
        except Exception as e:
            logging.error(f"Can't get screen state => {e}")

    # --------------------------------------------------------------------------
    # DPM websocket feedback
    #
    # "dpm_global": main bus levels => {"dpm_global": [a, b, a_hold, b_hold]}
    # "dpm_state": levels of every chain with audio => {"dpm_state": {chain_id: [a, b, a_hold, b_hold], ...}}
    # Levels go from 0.0 (silence, -72dBFS or less) to 1.0 (0dBFS), linear in dB, rounded to 2 decimals.
    # Peak meters change every audio period, so they are sampled (10Hz), but only while someone is subscribed,
    # and only the changes are sent: nothing is sent while levels don't change (e.g. silence).
    # "dpm_state" sends all the chains after subscribing, then only the changed ones (null for removed chains).
    # --------------------------------------------------------------------------

    dpm_feedback_period_ms = 100

    def dpm_feedback_sync(self, new_subscriptions=()):
        """Main thread: start/stop the DPM sampling, depending on the subscriptions

        new_subscriptions: DPM streams just subscribed, to send them the full levels on next sample
        """
        active = self.websocket_has_subscribers("dpm_global") or self.websocket_has_subscribers("dpm_state")
        if "dpm_global" in new_subscriptions:
            self.dpm_global_sent = None
        if "dpm_state" in new_subscriptions:
            self.dpm_state_sent = {}
        if self.websocket_has_subscribers("dpm_state"):
            self.state_manager.zynmixer_chan.enable_dpm(True)
            self.state_manager.zynmixer_bus.enable_dpm(True)
        if active and not self.dpm_feedback_active:
            self.dpm_feedback_active = True
            self.dpm_feedback_task()
        elif not active:
            self.dpm_feedback_active = False
            self.dpm_global_sent = None
            self.dpm_state_sent = {}

    @staticmethod
    def get_dpm_levels(dpm):
        return [round(1.0 - dpm.a, 2), round(1.0 - dpm.b, 2), round(1.0 - dpm.a_hold, 2), round(1.0 - dpm.b_hold, 2)]

    def dpm_feedback_task(self):
        """Main thread task: sample the DPMs and queue the changes for the subscribers"""
        if not self.dpm_feedback_active or self.exit_flag:
            return
        try:
            zynmixer_bus = self.state_manager.zynmixer_bus
            if self.websocket_has_subscribers("dpm_state"):
                self.state_manager.zynmixer_chan.update_dpm_states()
                zynmixer_bus.update_dpm_states()
                levels = {}
                for chain_id, chain in list(self.chain_manager.chains.items()):
                    proc = chain.zynmixer_proc
                    if proc is not None and proc.mixer_chan is not None:
                        levels[str(chain_id)] = self.get_dpm_levels(proc.zynmixer.dpm[proc.mixer_chan])
                changes = {k: v for k, v in levels.items() if self.dpm_state_sent.get(k) != v}
                for k in self.dpm_state_sent.keys() - levels.keys():
                    changes[k] = None  # Removed chain
                if changes:
                    self.dpm_state_sent = levels
                    self.websocket_queue.put(("dpm_state", json.dumps({"dpm_state": changes})))
            elif self.websocket_has_subscribers("dpm_global"):
                zynmixer_bus.update_dpm_states(1)
            if self.websocket_has_subscribers("dpm_global"):
                levels = self.get_dpm_levels(zynmixer_bus.dpm[0])
                if levels != self.dpm_global_sent:
                    self.dpm_global_sent = levels
                    self.websocket_queue.put(("dpm_global", json.dumps({"dpm_global": levels})))
        except Exception as e:
            logging.error(f"Can't get DPM feedback => {e}")
        self.websocket_run_later(self.dpm_feedback_period_ms, self.dpm_feedback_task)

    # --------------------------------------------------------------------------
    # Chain manager websocket feedback ("chain_state")
    #
    # The full chain list is sent after subscribing and on every change (it's small and changes are rare):
    #   {"chain_state": {"active": 1, "chains": [{"id": 0, "index": 0, "name": "Main", ...}, ...]}}
    # The chain manager signals are registered only while someone is subscribed. Loading a snapshot or a ZS3
    # sends a single signal at the end. Some user actions send several (e.g. adding a chain: active chain, add
    # chain, add processor), so the state is built by the websocket sender thread after a short delay, to
    # report them once. It's only sent if it changed.
    # --------------------------------------------------------------------------

    chain_state_signals = (
        (zynsigman.S_CHAIN_MAN, zynsigman.SS_SET_ACTIVE_CHAIN),
        (zynsigman.S_CHAIN_MAN, zynsigman.SS_MOVE_CHAIN),
        (zynsigman.S_CHAIN_MAN, zynsigman.SS_ADD_CHAIN),
        (zynsigman.S_CHAIN_MAN, zynsigman.SS_REMOVE_CHAIN),
        (zynsigman.S_CHAIN_MAN, zynsigman.SS_REMOVE_ALL_CHAINS),
        (zynsigman.S_CHAIN_MAN, zynsigman.SS_RENAME_CHAIN),
        (zynsigman.S_CHAIN_MAN, zynsigman.SS_ADD_PROCESSOR),
        (zynsigman.S_CHAIN_MAN, zynsigman.SS_REMOVE_PROCESSOR),
        (zynsigman.S_CHAIN_MAN, zynsigman.SS_SET_MIDI_CHAN),
        (zynsigman.S_STATE_MAN, zynsigman.SS_LOAD_SNAPSHOT),
        (zynsigman.S_STATE_MAN, zynsigman.SS_LOAD_ZS3),
    )

    def chain_state_sync(self):
        """Register/unregister the chain manager signals, depending on the subscriptions"""
        active = self.websocket_has_subscribers("chain_state")
        if active and not self.chain_state_active:
            self.chain_state_active = True
            for signal, subsignal in self.chain_state_signals:
                zynsigman.register(signal, subsignal, self.cb_chain_state)
        elif not active and self.chain_state_active:
            self.chain_state_active = False
            for signal, subsignal in self.chain_state_signals:
                zynsigman.unregister(signal, subsignal, self.cb_chain_state)
            self.chain_state_json = ""

    def cb_chain_state(self, **kwargs):
        # Queue one update for the sender thread, whatever the quantity of signals
        if not self.chain_state_pending:
            self.chain_state_pending = True
            self.websocket_queue.put(("chain_state", None))

    def send_chain_state(self):
        """Sender thread: send the chain state to the subscribers, if it changed"""
        sleep(0.05)  # Report the signals of a single action once
        self.chain_state_pending = False
        try:
            state_json = json.dumps({"chain_state": self.get_chain_state()})
        except Exception as e:
            logging.error(f"Can't get chain state => {e}")
            return
        if state_json != self.chain_state_json:
            self.chain_state_json = state_json
            self.websocket_broadcast_payload("chain_state", state_json)

    def get_chain_state(self):
        """Return the chain manager state as a JSON serializable dictionary"""
        chains = []
        for index, (chain_id, chain) in enumerate(list(self.chain_manager.chains.items())):
            midi_chan = chain.midi_chan
            if isinstance(midi_chan, int) and 0 <= midi_chan < 16:
                midi_chan += 1
            elif midi_chan == 0xffff:
                midi_chan = "all"
            else:
                midi_chan = None
            proc = chain.zynmixer_proc
            if proc is not None and proc.mixer_chan is not None:
                mixer = {"bus": proc.zynmixer is self.state_manager.zynmixer_bus, "strip": proc.mixer_chan}
            else:
                mixer = None
            chains.append({
                "id": chain_id,
                "index": index,  # Position in the mixer (display order), as used by the MIXER CUIA
                "name": chain.get_name(),
                "title": chain.title or "",
                "type": chain.get_type(),
                "midi_chan": midi_chan,  # 1-16, "all" or None
                "zmop_index": chain.zmop_index,
                "mixer": mixer,
                "audio_thru": bool(chain.audio_thru),
                "midi_thru": bool(chain.midi_thru)
            })
        active = self.chain_manager.active_chain
        return {"active": active.chain_id if active else None, "chains": chains}

    def websocket_init(self):
        """Start the websocket server and its threads"""
        if zynthian_websocket_server is None:
            logging.error("Can't start the websocket server: python module websocket_server (websocket-server) not installed")
            return
        ws_note_chans = {}  # (client id, note) => MIDI channel of the note_on sent by that client (piano, controller)

        def ws_midi_chan():
            """MIDI channel of the active chain (None if it has none). The channel sent by clients is ignored."""
            try:
                chan = int(self.chain_manager.get_active_chain().midi_chan)
            except Exception:
                return None
            return chan if 0 <= chan <= 15 else None

        # Define callback functions for server events
        def client_left(client, server):
            if client:  # None when a connection closes before the websocket handshake (port probes)
                self.websocket_clients.pop(client['id'], None)
                self.websocket_subscriptions.pop(client['id'], None)
                self.websocket_run_idle(self.screen_state_sync)
                self.websocket_run_idle(self.dpm_feedback_sync)
                self.chain_state_sync()
                # Release the notes this client left held
                for key in [k for k in ws_note_chans if k[0] == client['id']]:
                    self.state_manager.zynmidi.note_off(ws_note_chans.pop(key), key[1])
            logging.debug(f"Websocket disconnected! Total active connections: {len(self.websocket_clients)}")

        def new_client(client, server):
            self.websocket_clients[client['id']] = client
            self.websocket_subscriptions[client['id']] = set()
            logging.debug(f"Websocket connected! Total active connections: {len(self.websocket_clients)}")

        def message_received(client, server, message):
            try:
                if message.lstrip().startswith("/"):
                    self.websocket_command(client, message.strip())
                    return
                data = json.loads(message)
                #logging.info(f"Received from WebSocket client #{client['id']}: {data}")
                if "cuia" in data:
                    self.websocket_cuia(data['cuia'], data['args'], f"WS#{client['id']}")
                elif "key" in data:
                    self.websocket_key_event(data["key"], data.get("code", ""))
                elif "midi" in data:
                    # MIDI from the browser (virtual piano, local MIDI controllers). The MIDI channel sent by the
                    # client is ignored: everything goes to the active chain's channel. The channel used by each
                    # note_on is remembered so its note_off matches even if the active chain changes meanwhile.
                    kind = data["midi"]
                    zynmidi = self.state_manager.zynmidi
                    if kind == "note_on":
                        chan = ws_midi_chan()
                        if chan is not None:
                            note = int(data["note"]) & 0x7F
                            ws_note_chans[(client['id'], note)] = chan
                            lib_zyncore.ui_send_note_on(chan, note, int(data.get("vel", 100)) & 0x7F)
                    elif kind == "note_off":
                        note = int(data["note"]) & 0x7F
                        chan = ws_note_chans.pop((client['id'], note), None)
                        if chan is not None:
                            lib_zyncore.ui_send_note_on(chan, note, 0)
                    else:
                        chan = ws_midi_chan()
                        if chan is not None:
                            val = int(data.get("val", 0))
                            if kind == "cc":
                                lib_zyncore.ui_send_ccontrol_change(chan, int(data["ctrl"]) & 0x7F, val & 0x7F)
                            elif kind == "pitch_bend":      # 14 bit, 8192 = centre
                                lib_zyncore.ui_send_pitchbend_change(chan, val & 0x3FFF)
                            elif kind == "program":
                                zynmidi.set_midi_prg(chan, val & 0x7F)
                            elif kind == "chan_pressure":
                                lib_zyncore.ui_send_chan_press(chan, val & 0x7F)
            except json.JSONDecodeError:
                # Fallback handler if the browser sends plain unformatted text instead of JSON
                logging.warning(f"Non-JSON string received from WebSocket client {client['id']}: {message}")
            except Exception as e:
                logging.error(f"Error handling browser WebSocket request: {e}")


        # Websocket worker thread
        def worker_thread():
            # Loop watching wsled state changes, ...
            while not self.exit_flag:
                wsleds = self.websocket_wsleds()
                if wsleds and wsleds.wsled_state_changed:
                    wsleds.wsled_state_changed = False
                    self.websocket_broadcast("wsled_state", wsleds.last_wsled_state)
                # 50ms sleep keeps CPU overhead at near 0%
                sleep(0.05)

        # Websocket sender thread: sends the queued feedback. Blocks (no CPU) until there is something to send
        def sender_thread():
            while True:
                item = self.websocket_queue.get()
                if item is None:
                    break
                if item[0] == "chain_state":
                    self.send_chain_state()
                else:
                    self.websocket_broadcast_payload(*item)

        self.websocket_server = zynthian_websocket_server(host="0.0.0.0", port=self.websocket_port)
        self.websocket_server.set_fn_client_left(client_left)
        self.websocket_server.set_fn_new_client(new_client)
        self.websocket_server.set_fn_message_received(message_received)
        # Without run_forever, the network port remains totally closed!
        self.websocket_engine_thread = threading.Thread(target=self.websocket_server.run_forever, name="ZynWSEngine", daemon=True)
        self.websocket_engine_thread.start()
        # Worker thread
        self.websocket_server_thread = threading.Thread(target=worker_thread, name="ZynWSWorker", daemon=True)
        self.websocket_server_thread.start()
        # Sender thread
        self.websocket_sender_thread = threading.Thread(target=sender_thread, name="ZynWSSender", daemon=True)
        self.websocket_sender_thread.start()
        logging.info(f"ZYNTHIAN-UI WebSocket server running on port {self.websocket_port}")
