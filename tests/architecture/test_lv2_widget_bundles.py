"""zynthian-ui's LV2 bundles (lv2/: the zyngui:widget ontology and the extension bundles that add the
built-in zynthian widgets to plugins, upstream a1527c99) must be installed and on LV2_PATH, or no
LV2 plugin gets its zynthian widget (spectrum, tuner, graphic EQ, NAM, AIDA-X, chord analyzer) in
either UI. ZynthianOS does it in zynthian-sys; here desktop/install.sh and zynthian_desktop_env.sh."""

import os
import re
import subprocess

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_SH = os.path.join(REPO, "desktop", "zynthian_desktop_env.sh")


def lv2_path(preset):
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", "/tmp"),
           "ZYNTHIAN_UI_DIR": REPO}
    if preset is not None:
        env["LV2_PATH"] = preset
    out = subprocess.run(["bash", "-c", f'. "{ENV_SH}" >/dev/null 2>&1; . "{ENV_SH}" >/dev/null 2>&1; echo "$LV2_PATH"'],
                         env=env, capture_output=True, text=True, check=True)
    return out.stdout.strip().split(":")


@pytest.mark.parametrize("preset", [None, "/usr/lib/lv2"], ids=["default", "set-by-session"])
def test_ui_lv2_bundles_on_lv2_path_once(preset):
    path = lv2_path(preset)
    assert path.count(f"{REPO}/lv2") == 1
    if preset:
        assert path[0] == preset


def test_install_copies_lv2_bundles():
    with open(os.path.join(REPO, "desktop", "install.sh")) as f:
        m = re.search(r"for d in (zyngui [^;]*); do", f.read())
    assert m and "lv2" in m.group(1).split()
