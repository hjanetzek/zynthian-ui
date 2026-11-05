# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
#
# File selector: UI-independent part of zynthian_gui_file_selector (the directories to browse
# for file types: user files, collections, system files), used by the Tk and Qt UIs.
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

from zyngine.zynthian_engine import zynthian_engine

COLLECTIONS_DIR = zynthian_engine.data_dir + "/collections/"

# File extension: [directory names under files/, icon]
FEXT2DIRNAME = {
    "aidax": [["Neural Models"], "file_model.png"],
    "aidadspmodel": [["Neural Models"], "file_model.png"],
    "nam": [["Neural Models"], "file_model.png"],
    "nammodel": [["Neural Models"], "file_model.png"],
    "json": [["Neural Models"], "file_model.png"],
    "wav": [["IRs", "Samples", "Audio"], "file_audio.png"],
    "flac": [["IRs", "Samples", "Audio"], "file_audio.png"],
    "aiff": [["IRs", "Samples", "Audio"], "file_audio.png"],
    "ogg": [["Samples", "Audio"], "file_audio.png"],
    "mp3": [["Samples", "Audio"], "file_audio.png"],
    "mid": [["Midi"], "file_midi.png"],
    "scl": [["Tuning"], "file.png"],
    "zpat": [["Patterns"], "file_midi.png"],
}


def root_dirnames(fexts):
    """The directory names (under files/) of these file extensions"""
    dirnames = []
    for fext in fexts:
        dirnames += FEXT2DIRNAME.get(fext.lower(), [[]])[0]
    return set(dirnames)


def root_dirs(dirnames):
    """(title, path) of the directories to browse: the user's files, each collection's, the
    system's"""
    dirs = [(f"User {dirname}", zynthian_engine.my_data_dir + "/files/" + dirname) for dirname in dirnames]
    if os.path.isdir(COLLECTIONS_DIR):
        for de in sorted(os.scandir(COLLECTIONS_DIR), key=lambda de: de.name):
            if de.is_dir():
                dirs += [(f"{de.name} {dirname}", de.path + "/" + dirname) for dirname in dirnames]
    dirs += [(f"System {dirname}", zynthian_engine.data_dir + "/files/" + dirname) for dirname in dirnames]
    return dirs
