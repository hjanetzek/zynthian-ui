#!/bin/bash
#******************************************************************************
# ZYNTHIAN PROJECT: directory layout for desktop Linux (and Nura)
#
# Sourced by setup_desktop.sh and zynthian_desktop.sh. Every variable can be
# set beforehand to override it.
#
# Read-only parts (code, factory data) default to the git checkouts next to
# this zynthian-ui checkout, as cloned by hand:
#
#   <ZYNTHIAN_DIR>/zynthian-ui, zynthian-sys, zynthian-data, zynthian-help, zyncoder
#   <ZYNTHIAN_DIR>/jalv: zynthian's jalv (github.com/zynthian/jalv, branch asyncli), which
#   the LV2 engine needs; setup_desktop.sh builds it into ZYNTHIAN_SW_DIR
#
# A package sets ZYNTHIAN_DIR (e.g. /usr/share/zynthian) instead.
# Everything that zynthian writes goes to the XDG directories of the user.
#******************************************************************************

# zynthian runs as an application, it doesn't manage the system (see zynconf.desktop_mode)
export ZYNTHIAN_DESKTOP=1

_zd_ui_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export ZYNTHIAN_UI_DIR="${ZYNTHIAN_UI_DIR:-$_zd_ui_dir}"
export ZYNTHIAN_DIR="${ZYNTHIAN_DIR:-$(dirname "$ZYNTHIAN_UI_DIR")}"
export ZYNTHIAN_SYS_DIR="${ZYNTHIAN_SYS_DIR:-$ZYNTHIAN_DIR/zynthian-sys}"
export ZYNTHIAN_DATA_DIR="${ZYNTHIAN_DATA_DIR:-$ZYNTHIAN_DIR/zynthian-data}"
export ZYNTHIAN_HELP_DIR="${ZYNTHIAN_HELP_DIR:-$ZYNTHIAN_DIR/zynthian-help}"
export ZYNTHIAN_ZYNCODER_DIR="${ZYNTHIAN_ZYNCODER_DIR:-$ZYNTHIAN_DIR/zyncoder}"
export ZYNTHIAN_JALV_SRC_DIR="${ZYNTHIAN_JALV_SRC_DIR:-$ZYNTHIAN_DIR/jalv}"
export ZYNTHIAN_RECIPE_DIR="${ZYNTHIAN_RECIPE_DIR:-$ZYNTHIAN_SYS_DIR/scripts/recipes}"

_zd_config_home="${XDG_CONFIG_HOME:-$HOME/.config}"
_zd_data_home="${XDG_DATA_HOME:-$HOME/.local/share}"

export ZYNTHIAN_CONFIG_DIR="${ZYNTHIAN_CONFIG_DIR:-$_zd_config_home/zynthian}"
export ZYNTHIAN_MY_DATA_DIR="${ZYNTHIAN_MY_DATA_DIR:-$_zd_data_home/zynthian/my-data}"
export ZYNTHIAN_PLUGINS_DIR="${ZYNTHIAN_PLUGINS_DIR:-$_zd_data_home/zynthian/plugins}"
export ZYNTHIAN_LV2_DIR="${ZYNTHIAN_LV2_DIR:-$ZYNTHIAN_PLUGINS_DIR/lv2}"
export ZYNTHIAN_SW_DIR="${ZYNTHIAN_SW_DIR:-$_zd_data_home/zynthian/sw}"
export ZYNTHIAN_PLUGINS_SRC_DIR="${ZYNTHIAN_PLUGINS_SRC_DIR:-$ZYNTHIAN_SW_DIR/plugins}"
export ZYNTHIAN_VENV_DIR="${ZYNTHIAN_VENV_DIR:-$_zd_data_home/zynthian/venv}"
# zynthian's own programs (its jalv) before the system's: the jalv engine talks to the
# asyncli fork's command line, a distribution's jalv makes it hang. Built by
# setup_desktop.sh into ZYNTHIAN_SW_DIR, or packaged in ZYNTHIAN_LIB_DIR/bin (Nura)
for _zd_bin in "${ZYNTHIAN_LIB_DIR:-/usr/lib/zynthian}/bin" "$ZYNTHIAN_SW_DIR/bin"; do
	case ":$PATH:" in
		*":$_zd_bin:"*) ;;
		*) [ -d "$_zd_bin" ] && export PATH="$_zd_bin:$PATH" ;;
	esac
done
unset _zd_bin
# Removable media, as mounted by udisks
export ZYNTHIAN_EX_DATA_DIR="${ZYNTHIAN_EX_DATA_DIR:-/run/media/$USER}"

# System LV2 directories first (Arch/Alpine use /usr/lib/lv2, Debian adds the multiarch one)
_zd_lv2_system="/usr/lib/lv2:/usr/local/lib/lv2"
if [ -d "/usr/lib/$(uname -m)-linux-gnu/lv2" ]; then
	_zd_lv2_system="$_zd_lv2_system:/usr/lib/$(uname -m)-linux-gnu/lv2"
fi
export LV2_PATH="${LV2_PATH:-$_zd_lv2_system:$ZYNTHIAN_LV2_DIR:$ZYNTHIAN_DATA_DIR/presets/lv2:$ZYNTHIAN_MY_DATA_DIR/presets/lv2}"

unset _zd_ui_dir _zd_config_home _zd_data_home _zd_lv2_system
