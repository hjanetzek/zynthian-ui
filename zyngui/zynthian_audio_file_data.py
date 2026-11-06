# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# Audio file widget: UI-independent part of zynthian_widget_audio_file (engine type, the view
# parameters an engine sets, loading a file, waveform peaks), used by the Tk and Qt UIs.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ******************************************************************************

import ctypes
import ctypes.util
import logging
from math import pow

import numpy as np

try:
    import soundfile
except ImportError:
    soundfile = None   # libsndfile through ctypes (load_wave)

ENG_NONE = 0
ENG_CLIPPY = 1
ENG_GLOBAL_AP = 2
ENG_CHAIN_AP = 3
ENG_SAMPLV1 = 4


def engine_type(processor):
    if processor is None:
        return ENG_NONE
    if processor.eng_code == "CL":
        return ENG_CLIPPY
    if processor.eng_code == "AP":
        return ENG_GLOBAL_AP if processor.id < 0 else ENG_CHAIN_AP
    if processor.eng_code == "JV/samplv1":
        return ENG_SAMPLV1
    return ENG_NONE


def file_zctrl(processor, widget_zctrl=None):
    """The controller with the file path: the control screen's widget controller, the selected
    clip's for clippy, else the processor's first path controller"""
    if widget_zctrl:
        return widget_zctrl
    try:
        return processor.controllers_dict[f"file {processor.engine.selected_phrase + 1}"]
    except Exception:
        for zctrl in processor.controllers_dict.values():
            if zctrl.is_path:
                return zctrl
    return None


def clippy_info(processor, zctrl, zynseq_obj):
    """(scene, phrase, midi_chan) of a clippy clip controller, else None"""
    if processor.eng_code != "CL":
        return None
    try:
        note = int(zctrl.symbol.split(" ")[1])
    except Exception as e:
        logging.error(f"Can't determine clippy sample index for '{zctrl.symbol}' => {e}")
        return None
    return (zynseq_obj.scene, note - 1, processor.midi_chan)


def transport(action, processor, eng_type, clip_info, state_manager):
    """The REC / STOP / PLAY keys on an audio file processor's widget (zynthian_widget_audio_file
    cuia_toggle_record / cuia_stop / cuia_play / cuia_toggle_play). action: "record", "stop",
    "play" or "toggle_play". True if handled, else the global transport applies."""
    libseq = state_manager.zynseq.libseq
    if clip_info:
        # Clippy: its clip's sequence; recording is the global audio recorder
        if action == "record":
            state_manager.audio_recorder.toggle_recording()
        elif action == "stop":
            libseq.setPlayState(clip_info[0], clip_info[1], clip_info[2], 0)
        elif action == "toggle_play":
            libseq.togglePlayState(clip_info[0], clip_info[1], clip_info[2])
        else:
            return False
        return True
    if eng_type == ENG_CHAIN_AP:
        ctrls = processor.controllers_dict
        if action == "stop":
            ctrls["transport"].set_value(0)
            ctrls["position"].set_value(0)
        elif action == "play":
            ctrls["transport"].set_value(127)
        elif action == "toggle_play":
            ctrls["transport"].toggle()
        else:
            return False
        return True
    return False


def clippy_values(processor, clip_info):
    """The clip's view values from its controllers: dict zoom, crop_start, crop_end, warp, beats,
    gain (as zynthian_widget_audio_file.get_clippy_values)"""
    zctrls = processor.controllers_dict
    note = clip_info[1] + 1
    values = {"zoom": zctrls[f"zoom {note}"].value, "crop_start": zctrls[f"crop_start {note}"].value,
              "crop_end": zctrls[f"crop_end {note}"].value, "warp": zctrls[f"warp {note}"].value,
              "beats": zctrls[f"beats {note}"].value, "gain": zctrls[f"gain {note}"].value}
    processor.engine.reset_monitors()
    return values


def engine_view(eng_type, processor, monitors, zynseq_obj, samplerate, frames, zoom, crop_start, crop_end,
                clip_info, zctrl):
    """View parameters the engine sets (zynthian_widget_audio_file.refresh_gui), as a dict of
    zoom, offset (frames), crop_start, crop_end (frames), loop_markers, loop_start, loop_end,
    warp, beats, gain, vzoom, cursor_pos (0..1 of the cropped part), update_cue; None: unchanged.
    zoom, crop_start, crop_end: the current values (clippy's cursor follows them)."""
    v = dict.fromkeys(("zoom", "offset", "crop_start", "crop_end", "loop_markers", "loop_start", "loop_end",
                       "warp", "beats", "gain", "vzoom", "cursor_pos"))
    v["update_cue"] = False
    monitors = monitors or {}
    match eng_type:
        case 1:   # ENG_CLIPPY
            v["loop_markers"] = False
            for key in ("zoom", "offset", "crop_start", "crop_end", "warp", "beats"):
                if key in monitors:
                    v[key] = monitors[key]
            if "gain" in monitors:
                v["gain"] = monitors["gain"]
                v["vzoom"] = pow(1.26, v["gain"])       # vzoom from gain in dB
            if frames and clip_info:
                clip_state = zynseq_obj.libseq.getPlayState(clip_info[0], clip_info[1], clip_info[2])
                if clip_state == 1:
                    v["cursor_pos"] = zynseq_obj.progress[zctrl.processor.midi_chan] / 100.0
                    try:
                        cursor_frame = crop_start + int(v["cursor_pos"] * (crop_end - crop_start))
                        v["offset"] = cursor_frame - frames // (zoom * 2)
                    except Exception:
                        pass
                else:
                    v["cursor_pos"] = 0.0
        case 2 | 3:   # ENG_GLOBAL_AP, ENG_CHAIN_AP
            if samplerate:
                zctrls = processor.controllers_dict
                v["loop_markers"] = False
                v["zoom"] = zctrls['zoom'].value
                v["offset"] = int(samplerate * zctrls['offset'].value)
                start = zctrls['crop start'].value
                end = zctrls['crop end'].value
                v["beats"] = 0
                v["gain"] = zctrls['gain'].value    # linear gain
                v["vzoom"] = v["gain"] * zctrls['v-zoom'].value
                dur = end - start
                v["cursor_pos"] = (zctrls['position'].value - start) / dur if dur > 0 else 0
                v["crop_start"] = int(samplerate * start)
                v["crop_end"] = int(samplerate * end)
                if monitors.get("update_cue"):
                    v["update_cue"] = True
                    monitors["update_cue"] = False
        case 4:   # ENG_SAMPLV1
            zctrls = processor.controllers_dict
            v["zoom"] = 1
            v["offset"] = 0
            v["beats"] = 0
            if zctrls['GEN1_OFFSET'].value:
                v["crop_start"] = int(frames * zctrls['GEN1_OFFSET_1'].value)
                v["crop_end"] = int(frames * zctrls['GEN1_OFFSET_2'].value)
            else:
                v["crop_start"] = 0
                v["crop_end"] = frames
            v["loop_markers"] = zctrls['GEN1_LOOP'].value
            if v["loop_markers"]:
                v["loop_start"] = int(frames * zctrls['GEN1_LOOP_1'].value)
                v["loop_end"] = int(frames * zctrls['GEN1_LOOP_2'].value)
            v["vzoom"] = 2.0 * zctrls['OUT1_VOLUME'].value
        case _:
            v["zoom"] = 1
            v["offset"] = 0
            v["beats"] = 0
    return v


# Loading

class _SfInfo(ctypes.Structure):
    _fields_ = [("frames", ctypes.c_int64), ("samplerate", ctypes.c_int), ("channels", ctypes.c_int),
                ("format", ctypes.c_int), ("sections", ctypes.c_int), ("seekable", ctypes.c_int)]


_libsndfile = None


def _load_with_libsndfile(fpath):
    """(data, samplerate) through libsndfile directly (no python-soundfile, as on the Duet)"""
    global _libsndfile
    if _libsndfile is None:
        _libsndfile = ctypes.CDLL(ctypes.util.find_library("sndfile") or "libsndfile.so.1")
        _libsndfile.sf_open.restype = ctypes.c_void_p
        _libsndfile.sf_open.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.POINTER(_SfInfo)]
        _libsndfile.sf_readf_float.restype = ctypes.c_int64
        _libsndfile.sf_readf_float.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64]
        _libsndfile.sf_close.argtypes = [ctypes.c_void_p]
    info = _SfInfo()
    handle = _libsndfile.sf_open(fpath.encode(), 0x10, ctypes.byref(info))   # SFM_READ
    if not handle:
        raise IOError(f"libsndfile can't open {fpath}")
    try:
        data = np.zeros((info.frames, info.channels), dtype=np.float32)
        read = _libsndfile.sf_readf_float(handle, data.ctypes.data, info.frames)
        return data[:max(0, read)], info.samplerate
    finally:
        _libsndfile.sf_close(handle)


def load_wave(fpath):
    """(data: frames x channels array, channels, frames, samplerate) of an audio file"""
    if soundfile:
        with soundfile.SoundFile(fpath) as sf:
            channels = sf.channels
            samplerate = sf.samplerate
            frames = sf.seek(0, soundfile.SEEK_END)
            sf.seek(0)
            data = sf.read(frames, always_2d=True)
    else:
        data, samplerate = _load_with_libsndfile(fpath)
        frames, channels = data.shape
    return data, channels, frames, samplerate


def peaks(data, start, length, width, samples_per_peak=16):
    """Waveform of frames start..start+length at width points: (mins, maxs), each channels x
    width, from samples_per_peak samples per point (as the Tk widget)"""
    frames, channels = data.shape
    width = max(1, int(width))
    length = min(frames, int(length))
    fpp = max(1, length // width)
    start = max(0, min(int(start), frames - length))
    start = (start // fpp) * fpp   # aligned to the point size: no flicker when scrolling
    block = min(fpp, 1024)
    step = max(1, block // samples_per_peak)
    idx = start + np.arange(width)[:, None] * fpp + np.arange(0, block, step)[None, :]
    idx = np.minimum(idx, frames - 1)
    samples = data[idx]                      # width x n x channels
    mins = np.minimum(samples.min(axis=1), 0.0).T
    maxs = np.maximum(samples.max(axis=1), 0.0).T
    return mins, maxs
