"""Adding chains and processors: the stages of zynthian_gui.modify_chain, without its screens.

The status dict collects what the screens ask for (type, engine, MIDI channel, ...) as in the Tk
UI; next_step() returns what is still missing ("engine", "midi_chan") or creates the chain or
processor once everything is known, and returns the processor to show (None for none).
"""

import logging

import zynautoconnect

ZMOP_MOD_INDEX = 16   # Dedicated zmop for MOD-UI (zynthian_gui)


class ChainEdit:

    def __init__(self, state_manager):
        self.state_manager = state_manager
        self.chain_manager = state_manager.chain_manager
        self.status = {}

    def start(self, status):
        self.status = dict(status)

    def next_step(self):
        """Returns ("engine", None) or ("midi_chan", None) if the screens must ask for more,
        ("done", (chain_id, processor)) when done, ("failed", message) on failure"""
        s = self.status
        if "engine" not in s:
            return ("engine", None) if "type" in s else ("failed", "No chain type")
        if "chain_id" in s:
            return self._modify_chain()
        if "midi_chan" not in s:
            return ("midi_chan", None)
        return self._add_chain()

    def _add_chain(self):
        s = self.status
        cm = self.chain_manager
        self.state_manager.start_busy("modify_chain", "Creating new chain")
        try:
            zmop_index = ZMOP_MOD_INDEX if s["engine"] == "MD" else None
            chain_id = cm.add_chain(None, s["midi_chan"], s.get("midi_thru", False),
                                    s.get("audio_thru", False), zmop_index,
                                    chain_pos=s.get("pos"), fast_refresh=True)
            if chain_id is None:
                return ("failed", "Failed to create chain")
            chain = cm.get_chain(chain_id)
            processor = cm.add_processor(chain_id, s["engine"])
            if chain.synth_slots or s.get("audio_thru", False):
                if s.get("mixbus", False):
                    am_proc = cm.add_processor(chain_id, "MR")
                    cm.set_chain_title(chain_id, am_proc.name)
                else:
                    cm.add_processor(chain_id, "MI")
            cm.rebuild_optimisation_cache()
            zynautoconnect.request_audio_connect(True)
            zynautoconnect.request_midi_connect(True)
            if processor and processor.type == "MIDI Synth":
                chain.init_MPE()
            cm.set_active_chain_by_id(chain_id)
            return ("done", (chain_id, processor))
        except Exception as e:
            logging.exception(f"creating chain {s}: {e}")
            return ("failed", f"Failed to create chain: {e}")
        finally:
            self.state_manager.end_busy("modify_chain")

    def _modify_chain(self):
        s = self.status
        cm = self.chain_manager
        chain_id = s["chain_id"]
        chain = cm.get_chain(chain_id)
        if chain is None:
            return ("failed", f"No chain {chain_id}")
        old_processor = s.get("processor")
        self.state_manager.start_busy("modify_chain",
                                      "Replacing processor" if old_processor else "Adding processor")
        try:
            if old_processor:
                processor = cm.add_processor(chain_id, s["engine"], chain.get_slot(old_processor))
                if processor:
                    cm.remove_processor(chain_id, old_processor)
                    chain.rebuild_graph()
            else:
                processor = cm.add_processor(chain_id, s["engine"], s.get("slot"))
            if not processor:
                return ("failed", "Failed to create processor")
            zynautoconnect.autoconnect()
            if processor.type == "MIDI Synth":
                chain.init_MPE()
            return ("done", (chain_id, processor))
        finally:
            self.state_manager.end_busy("modify_chain")
