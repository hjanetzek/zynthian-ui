# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# MIDI files of the MIDI recorder/player (external storage, captures, user and system files):
# UI-independent part of zynthian_gui_midi_recorder, used by the Tk and Qt UIs.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ******************************************************************************

import os
import logging
from os.path import isfile, join

from zynconf import zynthian_paths
from zyngui import zynthian_gui_config
from zynlibs.zynsmf import zynsmf
from zynlibs.zynsmf.zynsmf import libsmf  # Direct access to shared library

system_dir_sdc = zynthian_paths.data_dir + "/files/Midi"
capture_dir_sdc = zynthian_paths.my_data_dir + "/capture"
user_dir_sdc = zynthian_paths.my_data_dir + "/files/Midi"


def get_filelist(src_dir):
    res = []
    smf = libsmf.addSmf()

    for f in os.listdir(src_dir):
        fpath = join(src_dir, f)
        fname = f[:-4]
        fext = f[-4:].lower()
        if isfile(fpath) and fext in ('.mid'):
            # Get mtime
            mtime = os.path.getmtime(fpath)

            # Get duration
            try:
                zynsmf.load(smf, fpath)
                length = libsmf.getDuration(smf)
            except Exception as e:
                length = 0
                logging.warning(e)

            # Generate title
            title = fname.replace(";", ">", 1).replace(";", "/")

            res.append({
                'fpath': fpath,
                'fname': fname,
                'fext': fext[1:],
                'length': length,
                'fduration': f"{int(length / 60)}:{int(length % 60):02}",
                'mtime': mtime,
                'title': title
            })

    libsmf.removeSmf(smf)
    return res


def midi_file_rows(ex_data_dir, i=1):
    """Rows [fpath, index, title, (info, icon)] of the MIDI files by source, newest first, with a
    section title row per source; i: index of the first file row"""
    rows = []

    def fill_from_source(source_dir, header_title):
        nonlocal i
        flist = get_filelist(source_dir)
        if len(flist) > 0:
            rows.append([None, 0, header_title])
            for finfo in sorted(flist, key=lambda d: d['mtime'], reverse=True):
                title = f"{finfo['title']} ({finfo['fduration']})"
                rows.append([finfo['fpath'], i, title, ["Select to play.\nBold to show options.", None]])
                i += 1

    # External storage
    for exd in zynthian_gui_config.get_external_storage_dirs(ex_data_dir):
        fill_from_source(exd, f"USB> {os.path.basename(exd)} MIDI Tracks")
    # Internal storage
    fill_from_source(capture_dir_sdc, "SD> Captured MIDI Tracks")
    fill_from_source(user_dir_sdc, "SD> User MIDI Tracks")
    fill_from_source(system_dir_sdc, "SD> System MIDI Tracks")
    return rows
