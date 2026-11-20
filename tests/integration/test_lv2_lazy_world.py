"""The lilv world of zynthian_lv2 is built on first use, not at import: importing reads only the engine list.
Built once, also when several threads (a snapshot's parallel engine starts) ask at the same time.

Needs the real lilv binding (the TTL parsing test also rdflib): skipped where tests/bootstrap.py had to stub it.
"""

import json
import os
import subprocess
import sys
import threading
import time
import types
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

REPO = Path(__file__).resolve().parents[2]

MANIFEST = """\
@prefix lv2:  <http://lv2plug.in/ns/lv2core#> .
@prefix doap: <http://usefulinc.com/ns/doap#> .
<urn:zyntest:lazy> a lv2:Plugin, lv2:InstrumentPlugin ; lv2:binary <plugin.so> ; doap:name "Lazy" .
"""


ENGINE_CONFIG = {"ZY": {"ID": "0123456789", "NAME": "ZynAddSubFX", "TITLE": "ZynAddSubFX", "TYPE": "MIDI Synth",
                        "CAT": "Synth", "ENABLED": True, "INDEX": 0, "URL": "", "UI": "", "DESCR": "",
                        "QUALITY": 0, "COMPLEX": 0, "EDIT": 0}}


def needs_lilv():
    from tests.bootstrap import STUBBED_MODULES
    if "lilv" in STUBBED_MODULES:
        pytest.skip("needs the lilv binding (stubbed here)")


@pytest.fixture
def lv2(tmp_path, monkeypatch):
    """zynthian_lv2 with no world loaded yet, on a private LV2_PATH; lilv.World counts its instances"""
    needs_lilv()
    from zyngine import zynthian_lv2 as z
    system = tmp_path / "system"
    bundle = system / "lazy.lv2"
    bundle.mkdir(parents=True)
    (bundle / "manifest.ttl").write_text(MANIFEST)
    monkeypatch.setenv("LV2_PATH", str(system))
    monkeypatch.setattr(z, "LV2_STAMP_FILE", str(tmp_path / "lv2.stamp"))
    monkeypatch.setattr(z, "_world", None)
    builds = []
    world_cls = z.lilv.World

    class CountingWorld(world_cls):  # a subclass: the bindings check isinstance(world, World)
        def __init__(self, *args, **kwargs):
            builds.append(threading.current_thread().name)
            time.sleep(0.05)  # widen the window two threads can both see "not built yet"
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(z.lilv, "World", CountingWorld)
    yield types.SimpleNamespace(z=z, builds=builds, tmp=tmp_path)
    monkeypatch.undo()
    z.init_lilv()


def test_import_builds_no_world_and_imports_no_rdflib():
    needs_lilv()
    # An engine config exists (without one, the import generates it: that needs the LV2 data)
    code = (f"import sys; sys.path.insert(0, {str(REPO)!r})\n"
            "import tests.bootstrap, os, json\n"
            # the bootstrap imports rdflib to see whether it's installed
            "[sys.modules.pop(m) for m in list(sys.modules) if m.split('.')[0] == 'rdflib']\n"
            f"open(os.environ['ZYNTHIAN_CONFIG_DIR'] + '/engine_config.json', 'w').write({json.dumps(ENGINE_CONFIG)!r})\n"
            "from zyngine import zynthian_lv2 as z\n"
            "assert 'ZY' in z.engines_by_type['MIDI Synth']\n"
            "assert not z.is_world_loaded(), 'world built at import'\n"
            "assert 'rdflib' not in sys.modules, 'rdflib imported'\n")
    env = dict(os.environ, PYTHONWARNINGS="ignore")
    proc = subprocess.run([sys.executable, "-c", code], cwd=REPO, env=env, capture_output=True, text=True,
                          timeout=120)
    assert proc.returncode == 0, proc.stderr[-1500:]


def test_first_use_builds_once(lv2):
    z = lv2.z
    assert not z.is_world_loaded()
    world = z.get_world()
    assert z.get_world() is world
    assert z.world is world  # module attribute, for code outside zynthian_lv2
    assert lv2.builds == [threading.current_thread().name]
    assert str(world.get_all_plugins()[world.new_uri("urn:zyntest:lazy")].get_name()) == "Lazy"


def test_two_threads_build_once(lv2):
    z = lv2.z
    barrier = threading.Barrier(2)
    got = []

    def use():
        barrier.wait()
        got.append(z.get_world())

    threads = [threading.Thread(target=use) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    assert len(lv2.builds) == 1
    assert len(got) == 2 and got[0] is got[1]


def test_port_query_builds_the_world(lv2):
    z = lv2.z
    z.plugin_ports_cache.clear()
    assert z.get_plugin_ports("urn:zyntest:lazy") == []
    assert z.is_world_loaded() and len(lv2.builds) == 1


def test_change_check_and_engine_list_dont_build_it(lv2):
    z = lv2.z
    assert z.check_lv2_changes() is False
    z.load_engines()
    z.get_engines()
    z.get_engines_by_type()
    assert not z.is_world_loaded() and lv2.builds == []


def test_changes_after_first_use_reload(lv2):
    z = lv2.z
    z.get_world()
    generation = z.lv2_generation
    assert z.check_lv2_changes() is False
    (lv2.tmp / "lv2.stamp").touch()
    assert z.check_lv2_changes() is True
    assert z.lv2_generation == generation + 1 and len(lv2.builds) == 2


def test_preload_in_background(lv2):
    z = lv2.z
    thread = z.preload_world()
    thread.join(10)
    world = z.get_world()
    assert z.get_world() is world and lv2.builds == ["lv2_world"]
    assert z.preload_world() is None


def test_preload_waits_while_busy(lv2):
    z = lv2.z
    busy = [True]
    thread = z.preload_world(busy=lambda: busy[0], idle_time=0.1)
    time.sleep(0.3)
    assert lv2.builds == []  # a snapshot load is running: no preload
    busy[0] = False
    thread.join(10)
    assert lv2.builds == ["lv2_world"]


def test_a_use_during_the_preload_waits_for_it(lv2):
    z = lv2.z
    thread = z.preload_world()
    while not lv2.builds:
        time.sleep(0.001)
    world = z.get_world()  # waits for the preload instead of building again
    thread.join(10)
    assert z.get_world() is world and lv2.builds == ["lv2_world"]


def test_change_check_doesnt_wait_for_a_load(lv2):
    z = lv2.z
    z.get_world()
    (lv2.tmp / "lv2.stamp").touch()
    got = []
    with z._world_lock:  # another thread loading
        t = threading.Thread(target=lambda: got.append(z.check_lv2_changes()))
        t.start()
        t.join(5)
        assert got == [False] and not t.is_alive()
    assert z.check_lv2_changes() is True


def test_ttl_info_imports_rdflib_when_needed(lv2):
    # not importorskip: where rdflib isn't installed (upstream's CI), tests/bootstrap.py put a stub in its place
    from tests.bootstrap import STUBBED_MODULES
    if "rdflib" in STUBBED_MODULES:
        pytest.skip("needs rdflib (stubbed here)")
    info = lv2.z.get_info_from_ttl(str(lv2.tmp / "system" / "lazy.lv2"))
    assert info["urn:zyntest:lazy"]["name"] == "Lazy"
    assert lv2.builds == []
