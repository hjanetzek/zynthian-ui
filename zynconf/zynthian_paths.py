# -*- coding: utf-8 -*-
# ******************************************************************************
# ZYNTHIAN PROJECT: Zynthian directory layout
#
# One place for all the directories zynthian uses.
#
# Every directory can be set with its environment variable. Unset ones are
# derived from ZYNTHIAN_DIR (default "/zynthian", the ZynthianOS layout), except
# ZYNTHIAN_UI_DIR, which defaults to the directory this code runs from.
# The results are written back into os.environ, so code that reads the
# variables directly and child processes (scripts, engines) see the same values.
#
# This module must stay light: only the standard library, no zynthian imports.
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

import os


def _env(name, default):
    value = os.environ.get(name)
    if not value:
        value = default
        os.environ[name] = value
    return value


zynthian_dir = _env("ZYNTHIAN_DIR", "/zynthian")
ui_dir = _env("ZYNTHIAN_UI_DIR", os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
sys_dir = _env("ZYNTHIAN_SYS_DIR", f"{zynthian_dir}/zynthian-sys")
config_dir = _env("ZYNTHIAN_CONFIG_DIR", f"{zynthian_dir}/config")
data_dir = _env("ZYNTHIAN_DATA_DIR", f"{zynthian_dir}/zynthian-data")
my_data_dir = _env("ZYNTHIAN_MY_DATA_DIR", f"{zynthian_dir}/zynthian-my-data")
ex_data_dir = _env("ZYNTHIAN_EX_DATA_DIR", "/media/root")
sw_dir = _env("ZYNTHIAN_SW_DIR", f"{zynthian_dir}/zynthian-sw")
plugins_dir = _env("ZYNTHIAN_PLUGINS_DIR", f"{zynthian_dir}/zynthian-plugins")
help_dir = _env("ZYNTHIAN_HELP_DIR", f"{zynthian_dir}/zynthian-help")
venv_dir = _env("ZYNTHIAN_VENV_DIR", f"{zynthian_dir}/venv")
recipe_dir = _env("ZYNTHIAN_RECIPE_DIR", f"{sys_dir}/scripts/recipes")

# Writable LV2 directory where zynthian installs plugins and presets
lv2_dir = _env("ZYNTHIAN_LV2_DIR", f"{plugins_dir}/lv2")

# Installed native libraries (e.g. /usr/lib/zynthian in a package). Unset: each
# library is loaded from its build directory in the source tree.
lib_dir = os.environ.get("ZYNTHIAN_LIB_DIR", "")


def native_lib(fname, build_dir):
    """Path of native library fname: from ZYNTHIAN_LIB_DIR if it's there, else from build_dir"""
    if lib_dir:
        fpath = os.path.join(lib_dir, fname)
        if os.path.isfile(fpath):
            return fpath
    return os.path.join(build_dir, fname)
