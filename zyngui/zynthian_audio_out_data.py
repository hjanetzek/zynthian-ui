# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# Audio output routing list of the active chain: UI-independent part of
# zynthian_gui_audio_out, used by the Tk and Qt UIs.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ******************************************************************************

import logging

import zynautoconnect


def audio_out_list(chain_manager, playback_ports):
    """Rows [value, value, title, (info, icon)] of the active chain's audio outputs: main
    mixbus, other chains, side-chain inputs, physical outputs (playback_ports:
    zynautoconnect.get_hw_audio_dst_ports())"""
    list_data = []
    if chain_manager.active_chain.chain_id:
        # Normal chain so add mixer / chain targets
        port_names = [("Main mixbus", 0, ["Send audio from this chain to the main mixbus", "audio_output.png"])]
        list_data.append((None, None, "> CHAINS"))
        len_check = len(list_data)
        for chain_id, chain in chain_manager.chains.items():
            if chain_id != 0 and chain != chain_manager.active_chain and chain.audio_thru or chain.is_synth() and chain.synth_slots[0][0].type == "Special":
                if chain_manager.will_audio_howl(chain_manager.active_chain.chain_id, chain_id):
                    prefix = "∞ "
                else:
                    prefix = ""
                port_names.append((f"{prefix}{chain.get_name()}", chain_id, [f"Send audio from this chain to the input of chain {chain.get_name()}.", "audio_output.png"]))
            # Add side-chain targets
            for processor in chain.get_processors():
                try:
                    for port_name in zynautoconnect.get_sidechain_portnames(processor.jackname):
                        port_names.append((f"↣ side {port_name}", port_name, [f"Send audio from this chain to the sidechain input of processor {port_name}.", "audio_output.png"]))
                except Exception as e:
                    logging.info(e)
                    pass
        for title, processor, info in port_names:
            if processor in chain_manager.active_chain.audio_out:
                list_data.append((processor, processor, "\u2612 " + title, info))
            else:
                list_data.append((processor, processor, "\u2610 " + title, info))
        if len(list_data) == len_check:
            list_data.pop() # Remove section title for empty section

    if chain_manager.active_chain.is_audio():
        port_names = []
        # Direct physical outputs
        list_data.append((None, None, "> AUDIO OUTPUT"))
        len_check = len(list_data)
        port_count = len(playback_ports)
        for i in range(0, port_count, 2):
            if playback_ports[i].aliases:
                suffix = f" ({playback_ports[i].aliases[0]})"
            else:
                suffix = ""
            port_names.append((f"Output {i + 1}{suffix}", f"^{playback_ports[i].name}$", [f"Send audio from this chain directly to physical audio output {i + 1}{suffix} as mono.", "audio_output.png"]))
            if i < port_count:
                if playback_ports[i + 1].aliases:
                    suffix = f" ({playback_ports[i + 1].aliases[0]})"
                else:
                    suffix = ""
                port_names.append((f"Output {i + 2}{suffix}", f"^{playback_ports[i + 1].name}$", [f"Send audio from this chain directly to physical audio output {i + 2}{suffix} as mono.", "audio_output.png"]))
                port_names.append((f"Outputs {i + 1}+{i + 2} (stereo)", f"^{playback_ports[i].name}$|^{playback_ports[i + 1].name}$", [f"Send audio from this chain directly to physical audio outputs {i + 1} & {i + 2} as stereo.", "audio_output.png"]))
        for title, processor, info in port_names:
            if processor in chain_manager.active_chain.audio_out:
                list_data.append((processor, processor, "\u2612 " + title, info))
            else:
                list_data.append((processor, processor, "\u2610 " + title, info))
        if len(list_data) == len_check:
            list_data.pop() # Remove section title for empty section

    return list_data
