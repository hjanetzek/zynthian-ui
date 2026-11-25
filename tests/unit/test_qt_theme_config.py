"""zynqt/theme.py: where Admin > Theme saves the user's choice, and "Default" removing it.

Since the launcher sources zynthian's config in each start's subshell, "Default" only removes the
user's line: the next start has the session's value again. A line the old "Default" left for one
start (ONCE_MARK) is removed by drop_once_lines() (at the UI's start, and by save_theme()).
"""

import os

import pytest

pytestmark = pytest.mark.unit

ENVARS = """#!/bin/bash
export ZYNTHIAN_UI_COLOR_BG="#000000"
"""


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    from zynconf import zynthian_config
    from zynqt import theme
    monkeypatch.setattr(zynthian_config, "config_dir", str(tmp_path))
    monkeypatch.setattr(zynthian_config, "config_fpath", str(tmp_path / "zynthian_envars.sh"))
    monkeypatch.setattr(theme, "SESSION_DEFAULTS", str(tmp_path / "no-session-defaults"))
    monkeypatch.setenv(theme.VAR, os.environ.get(theme.VAR, ""))   # save_config sets it: restored
    (tmp_path / "zynthian_envars.sh").write_text(ENVARS)
    return tmp_path


def lines(path):
    return path.read_text().splitlines()


def test_a_theme_is_saved_in_zynthian_envars(cfg):
    from zynqt import theme
    theme.save_theme("classic")
    assert 'export ZYNTHIAN_QT_THEME="classic"' in lines(cfg / "zynthian_envars.sh")
    assert theme.user_theme() == "classic"


def test_a_theme_goes_to_the_custom_config_when_that_sets_it(cfg):
    from zynqt import theme
    custom = cfg / "zynthian_custom_config.sh"
    custom.write_text('export ZYNTHIAN_QT_THEME="v4"\n')
    theme.save_theme("enterprise")
    assert 'export ZYNTHIAN_QT_THEME="enterprise"' in lines(custom)
    assert not any("ZYNTHIAN_QT_THEME" in line for line in lines(cfg / "zynthian_envars.sh"))
    assert theme.user_theme() == "enterprise"


def test_default_only_removes_the_users_lines(cfg):
    from zynqt import theme
    envars = cfg / "zynthian_envars.sh"
    custom = cfg / "zynthian_custom_config.sh"
    theme.save_theme("classic")
    custom.write_text('# mine\nexport ZYNTHIAN_QT_THEME="v4"\n')
    theme.save_theme("")
    # no line for one start any more: nothing about the theme is left
    assert not any("ZYNTHIAN_QT_THEME" in line for line in lines(envars))
    assert lines(custom) == ["# mine"]
    assert 'export ZYNTHIAN_UI_COLOR_BG="#000000"' in lines(envars)
    assert theme.user_theme() == ""


def test_a_line_the_old_default_left_is_removed(cfg):
    from zynqt import theme
    envars = cfg / "zynthian_envars.sh"
    envars.write_text(ENVARS + f'export ZYNTHIAN_QT_THEME="v4"  {theme.ONCE_MARK}\n')
    assert theme.user_theme() == ""     # not the user's choice
    theme.drop_once_lines()
    assert envars.read_text() == ENVARS
    envars.write_text(ENVARS + f"unset ZYNTHIAN_QT_THEME  {theme.ONCE_MARK}\n")
    theme.save_theme("galactica")
    assert lines(envars)[-1] == 'export ZYNTHIAN_QT_THEME="galactica"'
    assert theme.ONCE_MARK not in envars.read_text()
