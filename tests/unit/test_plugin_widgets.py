"""Plugin widgets (zyngui.zynthian_widget_data.plugin_widget): the Qt UI picks its view of an LV2
plugin's zynthian widget by the widget file's name, zynthian_widget_<name>.py.

Upstream renamed the Guitarix graphic EQ widget to lowercase (732e32b7,
zynthian_widget_gxgraphiceq.py); the shared module kept "GxGraphicEQ", so the Qt UI showed the
controllers instead of the EQ."""

import glob
import os
from types import SimpleNamespace

import pytest

wd = pytest.importorskip("zyngui.zynthian_widget_data")

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def processor(fpath):
    return SimpleNamespace(engine=SimpleNamespace(custom_gui_fpath=fpath))


def test_gxgraphiceq_widget_is_recognised():
    fpath = f"{REPO}/lv2/gxgraphiceq-zyngui.lv2/zynthian_widget_gxgraphiceq.py"
    assert wd.plugin_widget(processor(fpath)) == "gxgraphiceq"


@pytest.mark.parametrize("fpath", sorted(glob.glob(f"{REPO}/lv2/*-zyngui.lv2/zynthian_widget_*.py")),
                         ids=os.path.basename)
def test_every_bundled_lv2_widget_has_a_qt_view(fpath):
    assert wd.plugin_widget(processor(fpath)) is not None


def test_no_widget():
    assert wd.plugin_widget(processor(None)) is None
    assert wd.plugin_widget(processor("/x/zynthian_widget_unknown.py")) is None


def test_engine_widget_names_any_widget_module():
    assert wd.engine_widget(processor("/u/lv2-widgets/x-zyngui.lv2/zynthian_widget_mylooper.py")) == "mylooper"
    assert wd.plugin_widget(processor("/u/lv2-widgets/x-zyngui.lv2/zynthian_widget_mylooper.py")) is None
    assert wd.engine_widget(processor("/x/other.py")) is None
    assert wd.engine_widget(None) is None
